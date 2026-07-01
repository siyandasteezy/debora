"""
Reasoning Engine — orchestrates all analysis and selects the best therapeutic approach.
Runs emotion detection, distortion detection, and framework selection in parallel.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum

from src.reasoning.distortion_detector import DistortionAnalysis, detect_cognitive_distortions
from src.reasoning.emotion_detector import EmotionThemeAnalysis, analyse_emotions_and_themes
from src.reasoning.frameworks.act import ACTGuidance, apply_act
from src.reasoning.frameworks.cbt import CBTGuidance, apply_cbt
from src.reasoning.frameworks.dbt import DBTGuidance, apply_dbt
from src.reasoning.frameworks.motivational_interviewing import MIGuidance, apply_mi
from src.reasoning.frameworks.positive_psychology import PPGuidance, apply_positive_psychology
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TherapeuticFramework(str, Enum):
    CBT = "cbt"
    ACT = "act"
    DBT = "dbt"
    MI = "mi"
    POSITIVE_PSYCHOLOGY = "positive_psychology"
    SUPPORTIVE = "supportive"  # When distress is low — just listen


@dataclass
class ReasoningOutput:
    emotion_analysis: EmotionThemeAnalysis
    distortion_analysis: DistortionAnalysis
    primary_framework: TherapeuticFramework
    framework_guidance: CBTGuidance | ACTGuidance | DBTGuidance | MIGuidance | PPGuidance | None
    reasoning_rationale: str
    conversation_stage: str  # explore | deepen | reframe | action | support


def _preferred_framework(
    framework_scores: dict[str, list[float]],
) -> TherapeuticFramework | None:
    """Return the framework with highest average engagement after 3+ data points."""
    averages = {
        fw: sum(scores) / len(scores)
        for fw, scores in framework_scores.items()
        if len(scores) >= 3
    }
    if not averages:
        return None
    best_fw, best_avg = max(averages.items(), key=lambda x: x[1])
    if best_avg < 0.45:
        return None
    try:
        return TherapeuticFramework(best_fw)
    except ValueError:
        return None


def _select_framework(
    emotion_analysis: EmotionThemeAnalysis,
    distortion_analysis: DistortionAnalysis,
    framework_scores: dict[str, list[float]] | None = None,
) -> tuple[TherapeuticFramework, str]:
    """Rule-based framework selector. Returns (framework, rationale)."""
    distress = emotion_analysis.distress_level
    has_distortions = distortion_analysis.has_significant_distortions
    has_goals = bool(emotion_analysis.goals_mentioned)
    valence = emotion_analysis.overall_valence
    themes = set(emotion_analysis.themes)

    # DBT: high distress + emotional intensity → distress tolerance first (safety-critical, never overridden)
    if distress >= 0.75:
        return (
            TherapeuticFramework.DBT,
            "High emotional distress detected — DBT distress tolerance and validation skills are most helpful.",
        )

    # CBT: moderate distress with clear cognitive distortions
    if has_distortions and 0.3 <= distress <= 0.74:
        return (
            TherapeuticFramework.CBT,
            "Cognitive distortions are prominent — CBT thought examination is appropriate.",
        )

    # MI: ambivalence about change or goals present
    ambivalence_themes = {"ambivalence", "motivation", "change", "habit", "addiction", "procrastination"}
    if has_goals and ambivalence_themes.intersection(themes):
        return (
            TherapeuticFramework.MI,
            "Goal ambivalence detected — MI can help explore and strengthen motivation.",
        )

    # ACT: avoidance, rumination, or existential themes
    act_themes = {"avoidance", "rumination", "existential", "meaning", "values", "chronic illness"}
    if act_themes.intersection(themes) and distress >= 0.3:
        return (
            TherapeuticFramework.ACT,
            "Themes of avoidance or values conflict suggest ACT's acceptance and values work.",
        )

    # Positive Psychology: low distress, building on strengths
    if distress < 0.35 and valence >= -0.2:
        # If this user has engaged more with a different framework, use that instead
        preferred = _preferred_framework(framework_scores or {})
        if preferred and preferred not in (TherapeuticFramework.SUPPORTIVE,):
            return (
                preferred,
                f"User has shown higher engagement with {preferred.value} — applying learned preference.",
            )
        return (
            TherapeuticFramework.POSITIVE_PSYCHOLOGY,
            "Moderate distress with positive indicators — positive psychology can build on existing strengths.",
        )

    # Default supportive — but defer to learned preference if available
    preferred = _preferred_framework(framework_scores or {})
    if preferred:
        return (
            preferred,
            f"Applying {preferred.value} based on user's engagement history.",
        )

    return (
        TherapeuticFramework.SUPPORTIVE,
        "Providing empathic supportive listening without framework imposition.",
    )


def _select_conversation_stage(
    emotion_analysis: EmotionThemeAnalysis,
    message_count: int,
) -> str:
    if message_count <= 2:
        return "explore"
    if emotion_analysis.distress_level >= 0.6:
        return "support"
    if message_count <= 5:
        return "deepen"
    if emotion_analysis.goals_mentioned:
        return "action"
    return "reframe"


async def run_reasoning(
    user_message: str,
    conversation_history: str = "",
    message_count: int = 1,
    framework_scores: dict[str, list[float]] | None = None,
) -> ReasoningOutput:
    """Parallel analysis + framework selection."""
    emotion_task = asyncio.create_task(
        analyse_emotions_and_themes(user_message, conversation_history)
    )
    distortion_task = asyncio.create_task(
        detect_cognitive_distortions(user_message)
    )

    emotion_analysis, distortion_analysis = await asyncio.gather(
        emotion_task, distortion_task
    )

    framework, rationale = _select_framework(emotion_analysis, distortion_analysis, framework_scores)
    stage = _select_conversation_stage(emotion_analysis, message_count)

    framework_guidance = None
    if framework == TherapeuticFramework.SUPPORTIVE:
        pass
    elif framework == TherapeuticFramework.CBT:
        framework_guidance = await apply_cbt(user_message, emotion_analysis, distortion_analysis)
    elif framework == TherapeuticFramework.ACT:
        framework_guidance = await apply_act(user_message, emotion_analysis)
    elif framework == TherapeuticFramework.DBT:
        framework_guidance = await apply_dbt(user_message, emotion_analysis)
    elif framework == TherapeuticFramework.MI:
        framework_guidance = await apply_mi(user_message, emotion_analysis)
    elif framework == TherapeuticFramework.POSITIVE_PSYCHOLOGY:
        framework_guidance = await apply_positive_psychology(user_message, emotion_analysis)

    logger.debug(
        "reasoning_complete",
        framework=framework.value,
        stage=stage,
        distress=emotion_analysis.distress_level,
        has_distortions=distortion_analysis.has_significant_distortions,
    )

    return ReasoningOutput(
        emotion_analysis=emotion_analysis,
        distortion_analysis=distortion_analysis,
        primary_framework=framework,
        framework_guidance=framework_guidance,
        reasoning_rationale=rationale,
        conversation_stage=stage,
    )

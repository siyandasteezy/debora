"""Positive Psychology framework — template-based, no external API."""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from src.reasoning.emotion_detector import EmotionThemeAnalysis


@dataclass
class PPGuidance:
    perma_focus: str
    strength_spotting: list[str]
    gratitude_prompt: str | None
    meaning_reflection: str
    savouring_exercise: str | None
    growth_reframe: str
    flourishing_goal: str
    affirmation_of_progress: str


_PERMA_FOCUS = ["positive_emotions", "engagement", "relationships", "meaning", "accomplishment"]

_STRENGTH_SPOTTING: dict[str, list[str]] = {
    "reaching out": ["courage to seek support", "self-awareness", "openness"],
    "trying": ["perseverance", "determination", "commitment"],
    "managing to": ["resilience", "capability", "self-efficacy"],
    "despite": ["resilience", "strength under pressure", "grit"],
    "still here": ["survival strength", "persistence", "hope"],
}

_DEFAULT_STRENGTHS = ["self-reflection", "honesty with yourself", "willingness to engage"]

_MEANING_REFLECTIONS = [
    "Even in the hardest moments, what still feels meaningful or worth protecting to you?",
    "What does this difficulty tell you about what you care about?",
    "What would it mean to you to come through this?",
    "What small moment of meaning have you experienced recently, even a tiny one?",
]

_GROWTH_REFRAMES = [
    "Struggling with this doesn't mean you're failing — it often means you're in the middle of something that matters.",
    "The fact that this is hard is not evidence that you can't do it.",
    "Pain and growth often travel together. What this experience might be teaching you isn't visible yet.",
    "Challenges don't define us — they reveal us. And what I hear is someone who cares deeply.",
]

_FLOURISHING_GOALS = [
    "What's one small thing this week that would let you feel more like yourself?",
    "What's the tiniest version of something you enjoy that you could make room for today?",
    "What would it look like to take one small step toward something that matters to you?",
]

_PROGRESS_AFFIRMATIONS = [
    "Just talking about this — that matters. It's a form of taking care of yourself.",
    "You're here, you're reflecting, you're trying. That's not nothing.",
    "The fact that you can name what's hard means you're already doing something important.",
]


def _spot_strengths(emotion_analysis: EmotionThemeAnalysis) -> list[str]:
    strengths = list(emotion_analysis.strengths)
    for key, vals in _STRENGTH_SPOTTING.items():
        if key in " ".join(emotion_analysis.stressors + emotion_analysis.themes).lower():
            strengths += vals[:2]
    return list(set(strengths or _DEFAULT_STRENGTHS))[:4]


async def apply_positive_psychology(
    user_message: str,
    emotion_analysis: EmotionThemeAnalysis,
) -> PPGuidance:
    low_distress = emotion_analysis.distress_level < 0.4
    strengths = _spot_strengths(emotion_analysis)

    return PPGuidance(
        perma_focus=random.choice(_PERMA_FOCUS[:3] if not low_distress else _PERMA_FOCUS),
        strength_spotting=strengths,
        gratitude_prompt=(
            "What's one small thing — however minor — that you're grateful for today?"
            if low_distress else None
        ),
        meaning_reflection=random.choice(_MEANING_REFLECTIONS),
        savouring_exercise=(
            "Think of one moment recently that felt even slightly good. Let yourself stay with it for 30 seconds."
            if low_distress else None
        ),
        growth_reframe=random.choice(_GROWTH_REFRAMES),
        flourishing_goal=random.choice(_FLOURISHING_GOALS),
        affirmation_of_progress=random.choice(_PROGRESS_AFFIRMATIONS),
    )

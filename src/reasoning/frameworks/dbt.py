"""DBT framework — template-based, no external API."""
from __future__ import annotations

import random
from dataclasses import dataclass

from src.reasoning.emotion_detector import EmotionCategory, EmotionThemeAnalysis


@dataclass
class DBTGuidance:
    module: str
    skill_name: str
    skill_description: str
    immediate_exercise: str
    wise_mind_reflection: str
    validation_statement: str
    opposite_action_suggestion: str | None


_VALIDATIONS = [
    "What you're feeling makes complete sense given what you're going through.",
    "Anyone in your situation would find this incredibly hard.",
    "Your emotions are valid — they're telling you something important.",
    "It's understandable that you feel this way. Your experience is real.",
    "I hear how much pain you're in right now, and it makes sense.",
]

_SKILLS = [
    {
        "module": "distress_tolerance",
        "skill_name": "TIPP",
        "skill_description": "Temperature, Intense exercise, Paced breathing, Paired muscle relaxation — fast-acting tools for overwhelming emotion.",
        "immediate_exercise": "Try holding cold water on your wrists or face for 30 seconds — it activates your dive reflex and quickly lowers emotional intensity.",
        "wise_mind_reflection": "From your wise mind: what's one small thing that would help you feel slightly safer right now?",
        "opposite_action": "Instead of withdrawing, try one small act of connection — even a text to someone you trust.",
    },
    {
        "module": "mindfulness",
        "skill_name": "Observe and Describe",
        "skill_description": "Notice your experience without judgement — describe what you observe without adding evaluation.",
        "immediate_exercise": "Take 60 seconds to notice five things you can see, four you can touch, three you can hear. Just observe, don't evaluate.",
        "wise_mind_reflection": "What does your wise mind — the balance of emotion and reason — tell you about this situation?",
        "opposite_action": None,
    },
    {
        "module": "emotion_regulation",
        "skill_name": "Check the Facts",
        "skill_description": "Emotions are not always reliable guides to facts. Checking the facts helps you respond rather than react.",
        "immediate_exercise": "Ask yourself: what is the actual event? What story am I telling about it? What do the facts say without the story?",
        "wise_mind_reflection": "If your emotion were at 50% intensity instead of 100%, what would you decide to do?",
        "opposite_action": "If shame is driving isolation, try one small act of reaching out instead.",
    },
    {
        "module": "distress_tolerance",
        "skill_name": "ACCEPTS",
        "skill_description": "Activities, Contributing, Comparisons, Emotions (opposite), Pushing away, Thoughts, Sensations — distraction tools for riding out a wave.",
        "immediate_exercise": "Pick one: do an absorbing activity, help someone else, or engage a different sensory experience (music, scent, taste) to ride out the intensity.",
        "wise_mind_reflection": "This feeling is intense — and feelings, even the most painful ones, do pass. What has helped you wait one out before?",
        "opposite_action": None,
    },
]


def _select_skill(emotion_analysis: EmotionThemeAnalysis) -> dict:
    distress = emotion_analysis.distress_level
    top = emotion_analysis.top_emotion

    if distress >= 0.7:
        return _SKILLS[0]  # TIPP for high distress
    if top and top.category in (EmotionCategory.ANXIETY, EmotionCategory.OVERWHELM):
        return _SKILLS[1]  # Mindfulness for anxiety
    if top and top.category in (EmotionCategory.SHAME, EmotionCategory.GUILT):
        return _SKILLS[2]  # Check the facts for shame/guilt
    return random.choice(_SKILLS)


async def apply_dbt(
    user_message: str,
    emotion_analysis: EmotionThemeAnalysis,
) -> DBTGuidance:
    skill = _select_skill(emotion_analysis)
    return DBTGuidance(
        module=skill["module"],
        skill_name=skill["skill_name"],
        skill_description=skill["skill_description"],
        immediate_exercise=skill["immediate_exercise"],
        wise_mind_reflection=skill["wise_mind_reflection"],
        validation_statement=random.choice(_VALIDATIONS),
        opposite_action_suggestion=skill.get("opposite_action"),
    )

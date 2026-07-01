"""Motivational Interviewing framework — template-based, no external API."""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from src.reasoning.emotion_detector import EmotionThemeAnalysis


@dataclass
class MIGuidance:
    open_question: str
    reflection: str
    affirmation: str
    change_talk_detected: list[str]
    sustain_talk_detected: list[str]
    ambivalence_summary: str
    evoking_question: str
    readiness_to_change: float
    mi_spirit_notes: str


_OPEN_QUESTIONS = [
    "What would you most like things to look like six months from now?",
    "What's important to you about making a change here?",
    "What do you imagine life could be like if things were different?",
    "What's got you thinking about this now?",
    "What's been going well, even in the middle of all this?",
]

_REFLECTIONS = [
    "It sounds like part of you really wants things to be different, even if it feels hard to know how.",
    "You're caught between where you are and where you want to be — and that tension is real.",
    "It seems like this matters a lot to you, even if the path forward isn't clear yet.",
    "I hear that you want change and that you're not sure you're ready — both of those can be true at the same time.",
]

_AFFIRMATIONS = [
    "The fact that you're reflecting on this at all shows real courage.",
    "Reaching out and talking about something this difficult takes strength.",
    "You've clearly been thinking about this carefully — that matters.",
    "Just being willing to look at this honestly says something important about who you are.",
]

_EVOKING_QUESTIONS = [
    "What would be the best thing about making this change?",
    "On a scale of 1–10, how important is this change to you — and what would make it a point higher?",
    "What would you lose if things stayed exactly the same?",
    "What would you be able to do or feel if you made this change?",
]


def _detect_change_talk(text: str) -> list[str]:
    markers = ["want to", "wish I", "need to", "thinking about", "considering", "hoping to", "I could", "I would"]
    return [m for m in markers if m.lower() in text.lower()][:3]


def _detect_sustain_talk(text: str) -> list[str]:
    markers = ["but", "however", "can't", "too hard", "not ready", "don't know how", "what's the point"]
    return [m for m in markers if m.lower() in text.lower()][:3]


async def apply_mi(
    user_message: str,
    emotion_analysis: EmotionThemeAnalysis,
) -> MIGuidance:
    change_talk = _detect_change_talk(user_message)
    sustain_talk = _detect_sustain_talk(user_message)
    has_goals = bool(emotion_analysis.goals_mentioned)

    readiness = 0.4
    if change_talk and not sustain_talk:
        readiness = 0.7
    elif sustain_talk and not change_talk:
        readiness = 0.2
    elif change_talk and sustain_talk:
        readiness = 0.45

    ambivalence = (
        "You seem to genuinely want things to be different and also have real doubts about whether change is possible. Both sides make sense."
        if change_talk and sustain_talk
        else "There are signs of motivation here that are worth exploring further."
    )

    return MIGuidance(
        open_question=random.choice(_OPEN_QUESTIONS),
        reflection=random.choice(_REFLECTIONS),
        affirmation=random.choice(_AFFIRMATIONS),
        change_talk_detected=change_talk,
        sustain_talk_detected=sustain_talk,
        ambivalence_summary=ambivalence,
        evoking_question=random.choice(_EVOKING_QUESTIONS),
        readiness_to_change=readiness,
        mi_spirit_notes="Express empathy, amplify change talk, roll with resistance.",
    )

"""CBT framework — template-based, no external API."""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from src.reasoning.distortion_detector import CognitiveDistortion, DistortionAnalysis
from src.reasoning.emotion_detector import EmotionCategory, EmotionThemeAnalysis

@dataclass
class CBTGuidance:
    thought_challenge: str
    behavioural_experiment: str | None
    socratic_questions: list[str]
    distortion_addressed: str | None
    evidence_for: list[str]
    evidence_against: list[str]
    balanced_thought: str
    homework_suggestion: str | None


_SOCRATIC_QUESTIONS = {
    CognitiveDistortion.ALL_OR_NOTHING: [
        "Is there a middle ground here that you might be missing?",
        "What would a 50% version of this look like?",
        "What evidence is there that it's not completely one way or the other?",
    ],
    CognitiveDistortion.CATASTROPHISING: [
        "What's the most likely outcome, not the worst?",
        "If the worst did happen, what resources would you have to cope?",
        "Has something this bad happened before? How did you manage?",
    ],
    CognitiveDistortion.OVERGENERALISATION: [
        "Can you think of even one time when this wasn't the case?",
        "Is 'always' or 'never' really accurate here?",
        "What would be a more precise way to describe what happened?",
    ],
    CognitiveDistortion.MIND_READING: [
        "What evidence do you have for what they're thinking?",
        "Could there be another explanation for their behaviour?",
        "Have you been able to ask them directly?",
    ],
    CognitiveDistortion.SHOULD_STATEMENTS: [
        "Where did this rule come from?",
        "What would happen if you replaced 'should' with 'could'?",
        "Would you hold a friend to this same standard?",
    ],
    CognitiveDistortion.LABELLING: [
        "Is one moment or quality the whole story of who you are?",
        "Would you label a friend this way based on one thing?",
        "What are some other words that describe you?",
    ],
    CognitiveDistortion.PERSONALISATION: [
        "What other factors could have contributed to this?",
        "Are you taking on responsibility that belongs to others too?",
        "What percentage of this was actually in your control?",
    ],
    CognitiveDistortion.FORTUNE_TELLING: [
        "What evidence do you have that this outcome is inevitable?",
        "What are two or three other ways this could unfold?",
        "How accurate have similar predictions been in the past?",
    ],
}

_DEFAULT_SOCRATIC = [
    "What would you tell a close friend in this situation?",
    "What evidence supports this thought, and what challenges it?",
    "How might you see this differently in a month's time?",
    "What's the most realistic outcome here?",
]

_BALANCED_THOUGHTS: dict[CognitiveDistortion, list[str]] = {
    CognitiveDistortion.ALL_OR_NOTHING: [
        "Most situations have shades of grey — this doesn't have to be all success or all failure.",
        "I can acknowledge what went wrong without dismissing what went right.",
    ],
    CognitiveDistortion.CATASTROPHISING: [
        "This feels huge right now, and I can still find a way through it.",
        "I've faced hard things before and found a way forward.",
    ],
    CognitiveDistortion.OVERGENERALISATION: [
        "This happened once — it doesn't define every time.",
        "One difficult experience doesn't predict all future ones.",
    ],
    CognitiveDistortion.SHOULD_STATEMENTS: [
        "I'm doing the best I can with what I have right now.",
        "I can aim for better without demanding perfection from myself.",
    ],
    CognitiveDistortion.LABELLING: [
        "I made a mistake — that doesn't make me a failure as a person.",
        "I am more than any single quality or moment.",
    ],
}

_DEFAULT_BALANCED = [
    "This is difficult, and I have more resources and strengths than I may be giving myself credit for.",
    "I can hold this feeling while also recognising there's more to the picture.",
]


async def apply_cbt(
    user_message: str,
    emotion_analysis: EmotionThemeAnalysis,
    distortion_analysis: DistortionAnalysis,
) -> CBTGuidance:
    top = distortion_analysis.top_distortion
    distortion_type = top.distortion if top else None

    questions = _SOCRATIC_QUESTIONS.get(distortion_type, _DEFAULT_SOCRATIC) if distortion_type else _DEFAULT_SOCRATIC
    balanced_pool = _BALANCED_THOUGHTS.get(distortion_type, _DEFAULT_BALANCED) if distortion_type else _DEFAULT_BALANCED

    challenge = (
        f"It sounds like there might be a '{distortion_type.value.replace('_', ' ')}' pattern here. "
        f"{top.reframe_suggestion}"
    ) if top else "What thought is at the centre of this feeling for you?"

    return CBTGuidance(
        thought_challenge=challenge,
        behavioural_experiment="Notice over the next day or two whether the evidence matches this thought.",
        socratic_questions=questions[:3],
        distortion_addressed=distortion_type.value if distortion_type else None,
        evidence_for=["The situation you've described"],
        evidence_against=["Other times this wasn't true", "What others who care about you might say"],
        balanced_thought=random.choice(balanced_pool),
        homework_suggestion="Try writing down the thought, the evidence for and against it, and a more balanced version.",
    )

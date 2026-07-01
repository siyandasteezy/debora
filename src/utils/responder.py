"""
Rule-based response composer. Builds empathetic, structured responses
from reasoning and framework analysis — no external API required.
"""
from __future__ import annotations

import random

from src.reasoning.engine import ReasoningOutput, TherapeuticFramework
from src.reasoning.emotion_detector import EmotionCategory, DetectedEmotion
from src.reasoning.frameworks.cbt import CBTGuidance
from src.reasoning.frameworks.dbt import DBTGuidance
from src.reasoning.frameworks.act import ACTGuidance
from src.reasoning.frameworks.motivational_interviewing import MIGuidance
from src.reasoning.frameworks.positive_psychology import PPGuidance
from src.recommendations.engine import Recommendation


_EMPATHETIC_OPENINGS: dict[EmotionCategory, list[str]] = {
    EmotionCategory.SADNESS: [
        "I can hear how much pain you're carrying right now.",
        "It sounds like you're going through something really heavy.",
        "What you're describing sounds incredibly hard.",
    ],
    EmotionCategory.ANXIETY: [
        "It sounds like your mind has been working overtime with worry.",
        "I can hear how much tension and uncertainty you're holding.",
        "Living with that level of anxiety is genuinely exhausting.",
    ],
    EmotionCategory.ANGER: [
        "It sounds like you've reached a real breaking point with this.",
        "That frustration and anger makes a lot of sense given what you're describing.",
        "I hear how much this situation has worn you down.",
    ],
    EmotionCategory.HOPELESSNESS: [
        "When hope feels this far away, everything takes so much more effort.",
        "What you're describing — that sense that nothing will change — is one of the heaviest feelings there is.",
        "I hear how stuck and depleted you feel right now.",
    ],
    EmotionCategory.OVERWHELM: [
        "It sounds like there's just too much, and not enough of you to hold it all.",
        "That feeling of being completely overwhelmed is real and valid.",
        "When everything piles up like this, it can feel impossible to find solid ground.",
    ],
    EmotionCategory.LONELINESS: [
        "That sense of being alone with all of this is one of the hardest things.",
        "Feeling unseen and disconnected is a real kind of pain.",
        "Loneliness like this can be incredibly heavy to carry.",
    ],
    EmotionCategory.GRIEF: [
        "Grief moves at its own pace, and what you're feeling is completely understandable.",
        "Loss touches everything, doesn't it. I'm sorry you're going through this.",
        "There's no right way to grieve, and what you're feeling is real.",
    ],
    EmotionCategory.SHAME: [
        "Shame is one of the most isolating feelings — it whispers that we're alone in what we feel.",
        "I want you to know that feeling this way doesn't make it true.",
        "Carrying shame is exhausting. You don't have to hold that alone.",
    ],
    EmotionCategory.GUILT: [
        "It sounds like you've been holding yourself responsible for a lot.",
        "Guilt can be a really heavy burden to carry.",
        "I hear how much you're judging yourself right now.",
    ],
    EmotionCategory.FRUSTRATION: [
        "That frustration is completely understandable — hitting walls is draining.",
        "I can hear how stuck and frustrated you feel with this.",
        "Feeling like nothing is working is genuinely exhausting.",
    ],
    EmotionCategory.JOY: [
        "It's really good to hear some brightness in what you're sharing.",
        "That sounds like a meaningful moment.",
    ],
    EmotionCategory.RELIEF: [
        "I'm glad to hear some of that pressure has lifted.",
        "Relief after a hard stretch is a real thing to celebrate.",
    ],
    EmotionCategory.NEUTRAL: [
        "Thank you for sharing this with me.",
        "I'm glad you felt you could talk about this.",
        "I appreciate you opening up about this.",
    ],
}

_DEFAULT_OPENINGS = [
    "Thank you for sharing this with me.",
    "I'm glad you reached out.",
    "I hear you.",
]

_FOLLOW_UP_QUESTIONS = [
    "How are you feeling right now, in this moment?",
    "What feels most pressing for you right now?",
    "Is there a particular part of this you'd like to explore more?",
    "What would feel most helpful to focus on?",
    "What do you need most right now — to be heard, or to think through what to do?",
]

_SUPPORTIVE_CLOSING = [
    "I'm here, and I'm listening. Please keep sharing.",
    "You don't have to figure all of this out at once. I'm here with you.",
    "Take whatever time you need. I'm not going anywhere.",
    "Whatever you're feeling, you can bring it here.",
]


def _opening(emotion: DetectedEmotion | None) -> str:
    if emotion is None:
        return random.choice(_DEFAULT_OPENINGS)
    pool = _EMPATHETIC_OPENINGS.get(emotion.category, _DEFAULT_OPENINGS)
    return random.choice(pool)


def _framework_insight(reasoning: ReasoningOutput) -> str:
    g = reasoning.framework_guidance
    fw = reasoning.primary_framework

    if fw == TherapeuticFramework.SUPPORTIVE or g is None:
        return ""

    if isinstance(g, CBTGuidance):
        q = g.socratic_questions[0] if g.socratic_questions else ""
        return f"{g.thought_challenge} {q}".strip()

    if isinstance(g, DBTGuidance):
        return f"{g.validation_statement} {g.immediate_exercise}"

    if isinstance(g, ACTGuidance):
        lines = [g.acceptance_prompt, g.defusion_exercise]
        if g.metaphor:
            lines.append(g.metaphor)
        return " ".join(lines)

    if isinstance(g, MIGuidance):
        return f"{g.reflection} {g.open_question}"

    if isinstance(g, PPGuidance):
        parts = [g.affirmation_of_progress, g.growth_reframe]
        return " ".join(parts)

    return ""


def _recommendation_snippet(rec: Recommendation) -> str:
    if not rec.strategies:
        return ""
    s = rec.strategies[0]
    short_instructions = s.instructions[:180] + "…" if len(s.instructions) > 180 else s.instructions
    return f"One thing that research supports for situations like this: **{s.name}** — {short_instructions}"


def _stage_prefix(stage: str) -> str:
    prefixes = {
        "explore": "",
        "deepen": "As we go a bit deeper — ",
        "reframe": "Stepping back for a moment — ",
        "action": "Thinking about where you want to go from here — ",
        "support": "",
    }
    return prefixes.get(stage, "")


def build_response(
    reasoning: ReasoningOutput,
    recommendation: Recommendation,
    stage: str,
    message_count: int,
) -> str:
    parts: list[str] = []

    # 1. Empathetic opening
    emotion = reasoning.emotion_analysis.top_emotion
    parts.append(_opening(emotion))

    # 2. Acknowledge themes/stressors if present
    themes = reasoning.emotion_analysis.themes[:2]
    stressors = reasoning.emotion_analysis.stressors[:1]
    if stressors:
        parts.append(f"It sounds like {stressors[0]} is weighing on you.")

    # 3. Stage prefix + framework insight (not on first message)
    if message_count > 1:
        prefix = _stage_prefix(stage)
        insight = _framework_insight(reasoning)
        if insight:
            combined = f"{prefix}{insight}".strip()
            parts.append(combined)

    # 4. Practical recommendation (from message 2 onwards)
    if message_count >= 2 and recommendation.strategies:
        snippet = _recommendation_snippet(recommendation)
        if snippet:
            parts.append(snippet)

    # 5. Psychoeducation from RAG (if available)
    if recommendation.psychoeducation:
        edu = recommendation.psychoeducation[:250].strip()
        if edu:
            parts.append(f"*Research note:* {edu}")

    # 6. Follow-up question or supportive close
    if reasoning.primary_framework == TherapeuticFramework.SUPPORTIVE or message_count == 1:
        parts.append(random.choice(_FOLLOW_UP_QUESTIONS))
    else:
        parts.append(random.choice(_SUPPORTIVE_CLOSING))

    return "\n\n".join(p for p in parts if p.strip())

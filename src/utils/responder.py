"""
Rule-based response composer. Builds empathetic, structured responses
from reasoning and framework analysis — no external API required.

Opening-up techniques used:
  - First message: normalising statement + low-stakes entry question
  - Short responses: reflect back then invite more (partial disclosure)
  - All messages: mirror key phrases before asking anything
  - Questions avoid "how do you feel?" in favour of anchored, concrete prompts
"""
from __future__ import annotations

import random
import re

from src.reasoning.engine import ReasoningOutput, TherapeuticFramework
from src.reasoning.emotion_detector import EmotionCategory, DetectedEmotion
from src.reasoning.frameworks.cbt import CBTGuidance
from src.reasoning.frameworks.dbt import DBTGuidance
from src.reasoning.frameworks.act import ACTGuidance
from src.reasoning.frameworks.motivational_interviewing import MIGuidance
from src.reasoning.frameworks.positive_psychology import PPGuidance
from src.recommendations.engine import Recommendation


# ── Empathetic openings keyed by top emotion ──────────────────────────────────

_EMPATHETIC_OPENINGS: dict[EmotionCategory, list[str]] = {
    EmotionCategory.SADNESS: [
        "I can hear how much pain you're carrying right now.",
        "It sounds like you're going through something really heavy.",
        "What you're describing sounds incredibly hard.",
        "That kind of sadness can make everything feel heavier than it should.",
    ],
    EmotionCategory.ANXIETY: [
        "It sounds like your mind has been working overtime.",
        "I can hear how much tension and uncertainty you're holding.",
        "Living with that level of anxiety is genuinely exhausting.",
        "That constant alertness wears on a person.",
    ],
    EmotionCategory.ANGER: [
        "It sounds like you've reached a real breaking point with this.",
        "That frustration makes a lot of sense given what you're describing.",
        "I hear how much this situation has worn you down.",
        "Anger like this usually means something important has been ignored for too long.",
    ],
    EmotionCategory.HOPELESSNESS: [
        "When hope feels this far away, everything takes so much more effort.",
        "What you're describing — that sense that nothing will change — is one of the heaviest feelings there is.",
        "I hear how stuck and depleted you feel right now.",
        "That kind of heaviness is real, and I'm glad you're talking about it.",
    ],
    EmotionCategory.OVERWHELM: [
        "It sounds like there's just too much, and not enough of you to hold it all.",
        "That feeling of being completely overwhelmed is real and valid.",
        "When everything piles up like this, it can feel impossible to find solid ground.",
        "Too much at once, with no clear way through — that's exhausting.",
    ],
    EmotionCategory.LONELINESS: [
        "That sense of being alone with all of this is one of the hardest things.",
        "Feeling unseen and disconnected is a real kind of pain.",
        "Loneliness like this can be incredibly heavy to carry.",
        "Going through hard things without someone to share it with makes everything harder.",
    ],
    EmotionCategory.GRIEF: [
        "Grief moves at its own pace, and what you're feeling is completely understandable.",
        "Loss touches everything, doesn't it. I'm sorry you're going through this.",
        "There's no right way to grieve, and what you're feeling is real.",
        "Grief doesn't follow a schedule — and it's allowed to be messy.",
    ],
    EmotionCategory.SHAME: [
        "Shame is one of the most isolating feelings — it whispers that we're alone in what we feel.",
        "I want you to know that feeling this way doesn't make it true.",
        "Carrying shame is exhausting. You don't have to hold that alone.",
        "Shame thrives in silence. The fact that you're speaking about it matters.",
    ],
    EmotionCategory.GUILT: [
        "It sounds like you've been holding yourself responsible for a lot.",
        "Guilt can be a really heavy burden to carry.",
        "I hear how much you're judging yourself right now.",
        "Holding yourself to account is one thing — punishing yourself is another.",
    ],
    EmotionCategory.FRUSTRATION: [
        "That frustration is completely understandable — hitting walls is draining.",
        "I can hear how stuck and frustrated you feel with this.",
        "Feeling like nothing is working is genuinely exhausting.",
        "When effort isn't producing results, frustration is the natural response.",
    ],
    EmotionCategory.JOY: [
        "It's really good to hear some brightness in what you're sharing.",
        "That sounds like a meaningful moment.",
        "I'm glad something is bringing you some light right now.",
    ],
    EmotionCategory.RELIEF: [
        "I'm glad to hear some of that pressure has lifted.",
        "Relief after a hard stretch is a real thing to acknowledge.",
        "That sounds like a weight off.",
    ],
    EmotionCategory.NEUTRAL: [
        "Thank you for sharing this with me.",
        "I'm glad you felt you could talk about this.",
        "I appreciate you opening up about this.",
        "I'm here and I'm listening.",
    ],
}

_DEFAULT_OPENINGS = [
    "Thank you for sharing this with me.",
    "I'm glad you reached out.",
    "I hear you.",
    "I'm here.",
]

# ── First-message welcomes ─────────────────────────────────────────────────────

_FIRST_MESSAGE_WELCOME = [
    (
        "Thank you for being here.\n\n"
        "A lot of people find it hard to know where to start — and that's completely okay. "
        "You don't need to have the words figured out.\n\n"
        "What's been sitting with you most lately? It doesn't have to be the whole story — "
        "just whatever feels closest to the surface right now."
    ),
    (
        "I'm really glad you reached out.\n\n"
        "There's no right way to begin this, and no pressure to explain everything at once. "
        "Whatever brought you here today is worth talking about.\n\n"
        "Where would you like to start?"
    ),
    (
        "Welcome. I'm here, and I'm not going anywhere.\n\n"
        "Sometimes it's hard to put what we're carrying into words. "
        "You don't have to have it all figured out — we can work through it together.\n\n"
        "What's been on your mind?"
    ),
]

# ── Opening-up prompts (when user is giving short, closed responses) ──────────

_OPEN_UP_REFLECTIONS = [
    "It sounds like there might be more beneath what you just said — and that's okay.",
    "Sometimes the hardest things to talk about are the ones that matter most.",
    "A lot can hide inside a short answer.",
    "You don't have to have it all figured out before you speak.",
    "Whatever you're holding, you can bring it here at whatever pace feels right.",
]

_PARTIAL_DISCLOSURE_INVITES = [
    (
        "You don't need to share more than feels right right now. "
        "But if there's a bit more to it — I'm here, and there's no rush."
    ),
    (
        "You can take this one small piece at a time. "
        "Even just naming what it feels like in your body — tight, heavy, hollow — "
        "can be a place to start."
    ),
    (
        "Sometimes it helps to start somewhere concrete. "
        "What has today actually looked like for you — sleep, eating, that kind of thing?"
    ),
    (
        "There's no pressure to get to the 'main thing' straightaway. "
        "What's one small detail about what's going on that you haven't said yet?"
    ),
]

_GENTLE_REOPEN_QUESTIONS = [
    "What does a typical day feel like for you right now?",
    "When did things start feeling this way — was there a moment, or did it creep up gradually?",
    "What does it feel like in your body when this comes up?",
    "Is there anyone in your life who knows you're feeling this way?",
    "What have you already tried, even if it didn't fully work?",
    "What would 'a little bit better' actually look like for you?",
]

# ── Normal follow-up questions (for when user is engaging well) ────────────────

_FOLLOW_UP_QUESTIONS = [
    "What feels most pressing for you right now?",
    "Is there a particular part of this you'd like to explore more?",
    "What would feel most helpful to focus on — working through what happened, or thinking about what's next?",
    "What do you need most right now — to be heard, or to think through what to do?",
    "When this feeling comes up, where do you notice it most — in your thoughts, your body, your relationships?",
    "What do you think has been making this harder recently?",
]

_SUPPORTIVE_CLOSING = [
    "I'm here, and I'm listening. Please keep sharing.",
    "You don't have to figure all of this out at once. I'm here with you.",
    "Take whatever time you need. I'm not going anywhere.",
    "Whatever you're feeling, you can bring it here.",
    "You're not carrying this alone right now.",
]


# ── Reflection helpers ─────────────────────────────────────────────────────────

def _reflect_message(user_message: str) -> str:
    """Pull a short phrase from the user's message and mirror it back."""
    sentences = re.split(r'[.!?]+', user_message.strip())
    sentences = [s.strip() for s in sentences if len(s.strip()) > 8]
    if not sentences:
        return ""
    # Take the first substantive sentence and convert to a reflection
    raw = sentences[0].lower()
    # Strip leading "i " for smoother reflection
    raw = re.sub(r'^i\s+(feel|am|have|was|don\'t|cant|can\'t|just)\s+', '', raw)
    raw = raw[:120]  # cap length
    if raw:
        return f"When you say \"{raw}\" — I want to make sure I understand what that's like for you."
    return ""


# ── Framework insight extractor ────────────────────────────────────────────────

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


def _opening(emotion: DetectedEmotion | None) -> str:
    if emotion is None:
        return random.choice(_DEFAULT_OPENINGS)
    pool = _EMPATHETIC_OPENINGS.get(emotion.category, _DEFAULT_OPENINGS)
    return random.choice(pool)


# ── Main response builder ─────────────────────────────────────────────────────

def build_response(
    reasoning: ReasoningOutput,
    recommendation: Recommendation,
    stage: str,
    message_count: int,
    user_message: str = "",
    short_response_streak: int = 0,
) -> str:
    parts: list[str] = []

    # ── First message: warm welcome + normalising + entry question ─────────────
    if message_count <= 1:
        return random.choice(_FIRST_MESSAGE_WELCOME)

    # ── Empathetic opening ─────────────────────────────────────────────────────
    emotion = reasoning.emotion_analysis.top_emotion
    parts.append(_opening(emotion))

    # ── Acknowledge stressor ───────────────────────────────────────────────────
    stressors = reasoning.emotion_analysis.stressors[:1]
    if stressors:
        parts.append(f"It sounds like {stressors[0]} is weighing on you.")

    # ── Reflective listening: mirror back a phrase before going further ────────
    if user_message and message_count <= 4:
        reflection = _reflect_message(user_message)
        if reflection:
            parts.append(reflection)

    # ── If user is giving short/closed replies: open-up mode ──────────────────
    if short_response_streak >= 2:
        parts.append(random.choice(_OPEN_UP_REFLECTIONS))
        parts.append(random.choice(_PARTIAL_DISCLOSURE_INVITES))
        parts.append(random.choice(_GENTLE_REOPEN_QUESTIONS))
        return "\n\n".join(p for p in parts if p.strip())

    # ── Stage prefix + framework insight (from message 2 onwards) ─────────────
    if message_count > 1:
        prefix = _stage_prefix(stage)
        insight = _framework_insight(reasoning)
        if insight:
            combined = f"{prefix}{insight}".strip()
            parts.append(combined)

    # ── Practical recommendation (from message 3 onwards, once user is sharing) ─
    if message_count >= 3 and short_response_streak == 0 and recommendation.strategies:
        snippet = _recommendation_snippet(recommendation)
        if snippet:
            parts.append(snippet)

    # ── Psychoeducation from RAG ───────────────────────────────────────────────
    if recommendation.psychoeducation and short_response_streak == 0:
        edu = recommendation.psychoeducation[:250].strip()
        if edu:
            parts.append(f"*Research note:* {edu}")

    # ── Follow-up question or supportive close ─────────────────────────────────
    if short_response_streak == 1:
        # One short message — gently invite more, not yet in full open-up mode
        parts.append(random.choice(_GENTLE_REOPEN_QUESTIONS))
    elif reasoning.primary_framework == TherapeuticFramework.SUPPORTIVE or message_count <= 3:
        parts.append(random.choice(_FOLLOW_UP_QUESTIONS))
    else:
        parts.append(random.choice(_SUPPORTIVE_CLOSING))

    return "\n\n".join(p for p in parts if p.strip())

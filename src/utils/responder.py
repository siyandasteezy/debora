"""
Rule-based response composer.

Anti-repeat: every phrase picked from a pool is recorded in recent_phrases
(passed in as a mutable list, modified in place). _pick() skips anything
in that list, so no phrase repeats within a session unless all options
are exhausted.

No stage prefixes ("As we go deeper...") — they read like a script.
Framework insights stand alone.
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


def _pick(pool: list[str], used: list[str]) -> str:
    """Return a random item from pool not recently used. Records the choice in used."""
    keys = [p[:60] for p in used]
    available = [p for p in pool if p[:60] not in keys]
    choice = random.choice(available if available else pool)
    used.append(choice[:60])
    return choice


# ── Empathetic openings ────────────────────────────────────────────────────────

_EMPATHETIC_OPENINGS: dict[EmotionCategory, list[str]] = {
    EmotionCategory.SADNESS: [
        "I can hear how much pain you're carrying right now.",
        "It sounds like you're going through something really heavy.",
        "What you're describing sounds incredibly hard.",
        "That kind of sadness can make everything feel heavier than it should.",
        "There's real weight in what you're sharing.",
        "Something in what you said tells me you've been hurting for a while.",
        "That's a lot to be sitting with.",
        "I hear the pain underneath what you're describing.",
        "What you're going through sounds genuinely difficult.",
        "That kind of hurt doesn't just go away on its own.",
    ],
    EmotionCategory.ANXIETY: [
        "It sounds like your mind has been working overtime.",
        "I can hear how much tension and uncertainty you're holding.",
        "Living with that level of anxiety is genuinely exhausting.",
        "That constant alertness wears on a person.",
        "Anxiety has a way of making everything feel urgent at once.",
        "It sounds like your nervous system has been in overdrive.",
        "The worry you're describing sounds relentless.",
        "That kind of underlying dread is really hard to carry.",
        "When the mind won't slow down, everything feels harder than it needs to.",
        "It makes sense that you're worn out — anxiety takes a lot out of you.",
    ],
    EmotionCategory.ANGER: [
        "It sounds like you've reached a real breaking point.",
        "That frustration makes a lot of sense given what you're describing.",
        "I hear how much this has worn you down.",
        "Anger like this usually means something important has been ignored for too long.",
        "Something has crossed a line for you — and that matters.",
        "It sounds like you've been patient with this for a long time.",
        "The anger comes through clearly. It sounds justified.",
        "There's a lot of energy behind what you're feeling.",
        "It makes sense that you'd feel this way given everything.",
        "That kind of frustration builds when things keep not changing.",
    ],
    EmotionCategory.HOPELESSNESS: [
        "When hope feels this far away, everything takes so much more effort.",
        "I hear how stuck and depleted you feel right now.",
        "That kind of heaviness is real, and I'm glad you're talking about it.",
        "That sense that nothing will change is one of the hardest things to sit with.",
        "When the future feels closed off, even small things become difficult.",
        "Hopelessness is exhausting in a way that's hard to describe to other people.",
        "It sounds like you've been fighting this feeling for a while.",
        "That emptiness you're describing — I hear it.",
        "When you can't see a way forward, it's hard to take any step at all.",
        "You're still here, still talking — that matters even when it doesn't feel like it.",
    ],
    EmotionCategory.OVERWHELM: [
        "It sounds like there's just too much, and not enough of you to hold it all.",
        "When everything piles up like this, it can feel impossible to find solid ground.",
        "Too much at once, with no clear way through — that's exhausting.",
        "It sounds like you've been running on empty for a while.",
        "That feeling of being completely swamped is real.",
        "Everything coming at once, with no pause — that takes a real toll.",
        "It makes sense you feel overwhelmed. That's a lot for one person.",
        "When there's no breathing room, even small things become too much.",
        "You've been carrying more than your fair share.",
        "That sense of being buried — I hear it in what you're saying.",
    ],
    EmotionCategory.LONELINESS: [
        "That sense of being alone with all of this is one of the hardest things.",
        "Feeling unseen and disconnected is a real kind of pain.",
        "Going through hard things without someone to share it with makes everything harder.",
        "Loneliness can sit right alongside a full life — it doesn't care how many people are around.",
        "The ache of not being truly known by anyone — that's real.",
        "It sounds like you've been carrying this alone for a long time.",
        "Feeling like no one really understands is its own kind of grief.",
        "That isolation you're describing sounds heavy.",
        "Being in pain and feeling like there's no one to tell — that's a lot.",
        "You reached out here, which tells me part of you is still looking for connection.",
    ],
    EmotionCategory.GRIEF: [
        "Grief moves at its own pace, and what you're feeling is completely understandable.",
        "Loss touches everything, doesn't it. I'm sorry you're going through this.",
        "There's no right way to grieve, and what you're feeling is real.",
        "Grief doesn't follow a schedule — and it's allowed to be messy.",
        "That loss is still very present for you, I can hear it.",
        "Grief has a way of resurfacing when you least expect it.",
        "You're allowed to still be affected by this.",
        "What you lost mattered. It makes sense this still hurts.",
        "Grief is the cost of loving something. That doesn't make it easier.",
        "There's no timeline on this — however long it takes is however long it takes.",
    ],
    EmotionCategory.SHAME: [
        "Shame is one of the most isolating feelings — it tells us we're alone in what we feel.",
        "I want you to know that feeling this way doesn't make it true.",
        "Shame thrives in silence. The fact that you're speaking about it matters.",
        "Carrying shame is exhausting. You don't have to hold that alone.",
        "Shame distorts things — it makes us believe the worst about ourselves.",
        "What you're describing sounds like shame, and shame lies.",
        "A lot of people feel exactly what you're feeling. You're not the exception you think you are.",
        "The fact that you feel shame tells me you care deeply about how you act. That's not nothing.",
        "Shame keeps us small. You deserve more room than that.",
        "You don't have to earn the right to feel okay about yourself.",
    ],
    EmotionCategory.GUILT: [
        "It sounds like you've been holding yourself responsible for a lot.",
        "Guilt can be a really heavy burden to carry.",
        "I hear how much you're judging yourself right now.",
        "Holding yourself to account is one thing — punishing yourself is another.",
        "You've been carrying this for a while, haven't you.",
        "There's a difference between taking responsibility and taking the blame for everything.",
        "Guilt can keep us stuck in a loop of self-criticism.",
        "It sounds like you've already paid a high price for whatever happened.",
        "You're being much harder on yourself than you'd be on anyone else.",
        "Whatever happened, I don't think you need to keep punishing yourself for it.",
    ],
    EmotionCategory.FRUSTRATION: [
        "That frustration is completely understandable — hitting walls is draining.",
        "I can hear how stuck you feel with this.",
        "Feeling like nothing is working is genuinely exhausting.",
        "When effort isn't producing results, frustration is the natural response.",
        "It sounds like you've been trying, and it keeps not being enough.",
        "That kind of friction — where things just won't move — wears on you.",
        "The frustration makes total sense given what you've been through.",
        "You've been pushing against something that won't give. That's tiring.",
        "I hear the impatience in what you're saying. It makes sense.",
        "Something that should be simpler keeps being difficult — of course that's frustrating.",
    ],
    EmotionCategory.JOY: [
        "It's really good to hear some brightness in what you're sharing.",
        "That sounds like a genuinely meaningful moment.",
        "I'm glad something is bringing you some light right now.",
        "Good moments matter — I'm glad this one landed.",
        "Something good found you. That's worth noticing.",
        "It's nice to hear that.",
    ],
    EmotionCategory.RELIEF: [
        "I'm glad to hear some of that pressure has lifted.",
        "Relief after a hard stretch is worth acknowledging.",
        "That sounds like a weight off.",
        "Good — some breathing room.",
        "That shift matters, even if things aren't fully resolved.",
    ],
    EmotionCategory.NEUTRAL: [
        "Thank you for sharing this with me.",
        "I'm glad you felt you could bring this here.",
        "I'm listening.",
        "I hear you.",
        "Tell me more.",
        "I'm here.",
        "Go on — I'm with you.",
    ],
}

_DEFAULT_OPENINGS = [
    "I hear you.",
    "Thank you for sharing this.",
    "I'm here.",
    "Tell me more.",
    "I'm listening.",
    "Go ahead — I'm with you.",
    "I'm glad you brought this here.",
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
        "Sometimes it's hard to put what we're carrying into words — you don't have to have it "
        "all figured out. We can work through it together.\n\n"
        "What's been on your mind?"
    ),
    (
        "I'm glad you're here.\n\n"
        "You don't have to come in with a clear explanation or a tidy summary of what's wrong. "
        "A lot of people don't. Whatever you're feeling, we can start there.\n\n"
        "What's going on for you right now?"
    ),
    (
        "Hello. Thank you for reaching out — it takes something to do that.\n\n"
        "There's no rush here, and nothing you bring is too small or too complicated. "
        "I'm just here to listen.\n\n"
        "What's been weighing on you?"
    ),
]

# ── Stressor acknowledgments (varied templates) ────────────────────────────────

_STRESSOR_ACK_TEMPLATES = [
    "It sounds like {stressor} is weighing on you.",
    "The weight of {stressor} comes through in what you're saying.",
    "{stressor} — that's a real thing to be dealing with.",
    "It makes sense that {stressor} would be so present for you right now.",
    "Carrying {stressor} on top of everything else isn't easy.",
    "Something about {stressor} feels like it's at the centre of this.",
    "{stressor} is clearly taking up a lot of space right now.",
    "It's clear that {stressor} has been on your mind.",
]

# ── Reflection templates (varied) ─────────────────────────────────────────────

_REFLECTION_TEMPLATES = [
    'When you say "{phrase}" — I want to make sure I understand what that\'s like for you.',
    '"{phrase}" — can you tell me more about that?',
    'Something about "{phrase}" stands out to me. What does that mean for you right now?',
    'I heard "{phrase}" and I don\'t want to rush past it.',
    'That phrase — "{phrase}" — I\'d like to stay with that for a moment.',
    '"{phrase}" — that\'s a real thing to be feeling.',
    'I noticed "{phrase}". What\'s underneath that?',
    'When you say "{phrase}", what does that actually feel like day to day?',
]

# ── Opening-up mode (short/closed responses) ──────────────────────────────────

_OPEN_UP_REFLECTIONS = [
    "It sounds like there might be more beneath what you just said — and that's okay.",
    "Sometimes the hardest things to talk about are the ones that matter most.",
    "A lot can hide inside a short answer.",
    "You don't have to have it all figured out before you speak.",
    "Whatever you're holding, you can bring it here at whatever pace feels right.",
    "It's okay if the words are hard to find right now.",
    "You don't have to give me the full picture all at once.",
    "Sometimes it helps just to say the messy version.",
    "There's no wrong way to talk about this.",
    "Take your time. I'm not going anywhere.",
]

_PARTIAL_DISCLOSURE_INVITES = [
    (
        "You don't need to share more than feels right. "
        "But if there's a bit more to it — I'm here, and there's no rush."
    ),
    (
        "You can take this one small piece at a time. "
        "Even just naming what it feels like in your body — tight, heavy, hollow — "
        "can be a place to start."
    ),
    (
        "There's no pressure to get to the main thing straightaway. "
        "What's one small detail about what's going on that you haven't said yet?"
    ),
    (
        "We don't have to go anywhere in a hurry. "
        "Sometimes just sitting with something out loud is enough for now."
    ),
    (
        "You can say as little or as much as you want. "
        "Even 'I don't know where to start' is a perfectly fine place to begin."
    ),
    (
        "If there are words you can't quite find yet, that's okay. "
        "Sometimes it helps to describe it around the edges — what it feels like, "
        "rather than what it is."
    ),
]

_GENTLE_REOPEN_QUESTIONS = [
    "What does a typical day feel like for you right now?",
    "When did things start feeling this way — was there a moment, or did it creep up gradually?",
    "What does it feel like in your body when this comes up?",
    "Is there anyone in your life who knows you're feeling this way?",
    "What have you already tried, even if it didn't fully work?",
    "What would 'a little bit better' actually look like for you?",
    "What's the part of this that's hardest to say out loud?",
    "When did you last feel okay — genuinely okay?",
    "What does this feel like at its worst?",
    "Is there something specific that happened recently, or has this been building?",
    "What's the thing you haven't been able to tell anyone else?",
    "How long have you been carrying this?",
]

# ── Normal follow-up questions ────────────────────────────────────────────────

_FOLLOW_UP_QUESTIONS = [
    "What feels most pressing for you right now?",
    "Is there a part of this you'd like to go into more?",
    "What would feel most useful — talking through what happened, or thinking about what to do next?",
    "What do you need most right now — to be heard, or to think through what to do?",
    "When this comes up, where do you notice it most — in your thoughts, your body, or your relationships?",
    "What do you think has been making this harder recently?",
    "What's the part of this that keeps coming back to you?",
    "Has anything shifted for you since this started?",
    "What does your gut tell you about what you need right now?",
    "Is there anything you've been avoiding thinking about?",
    "What would you say to a close friend going through exactly this?",
    "Is there a small thing that's made any of this easier, even briefly?",
    "What feels true about what you just shared?",
    "What else is going on that I should know about?",
]

_SUPPORTIVE_CLOSING = [
    "I'm here. Keep going.",
    "You don't have to figure all of this out at once.",
    "Take whatever time you need.",
    "Whatever you're feeling, you can bring it here.",
    "You're not carrying this alone right now.",
    "None of this has to be resolved today.",
    "I'm glad you're talking about this.",
    "You've shared something important. I hear it.",
    "There's no rush. I'm with you.",
    "Keep going — I'm listening.",
    "That took something to say. I appreciate you trusting me with it.",
    "I'm not going anywhere.",
]

# ── Recommendation intro variety ──────────────────────────────────────────────

_REC_INTROS = [
    "One thing that research supports for situations like this:",
    "Something that's helped others in similar situations:",
    "There's an approach that might be worth trying:",
    "A technique that can make a real difference here:",
    "Research points to something practical for this:",
    "Something concrete you might find useful:",
    "This is something that tends to help with what you're describing:",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _opening(emotion: DetectedEmotion | None, used: list[str]) -> str:
    if emotion is None:
        return _pick(_DEFAULT_OPENINGS, used)
    pool = _EMPATHETIC_OPENINGS.get(emotion.category, _DEFAULT_OPENINGS)
    return _pick(pool, used)


def _stressor_ack(stressor: str, used: list[str]) -> str:
    template = _pick(_STRESSOR_ACK_TEMPLATES, used)
    return template.format(stressor=stressor)


def _reflect_message(user_message: str, used: list[str]) -> str:
    sentences = re.split(r'[.!?]+', user_message.strip())
    sentences = [s.strip() for s in sentences if len(s.strip()) > 8]
    if not sentences:
        return ""
    raw = sentences[0].lower()
    raw = re.sub(r"^i\s+(feel|am|have|was|don't|cant|can't|just)\s+", '', raw)
    raw = raw[:100].strip()
    if not raw:
        return ""
    template = _pick(_REFLECTION_TEMPLATES, used)
    result = template.format(phrase=raw)
    return result


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
        return f"{g.affirmation_of_progress} {g.growth_reframe}"
    return ""


def _recommendation_snippet(rec: Recommendation, used: list[str]) -> str:
    if not rec.strategies:
        return ""
    s = rec.strategies[0]
    short_instructions = s.instructions[:180] + "…" if len(s.instructions) > 180 else s.instructions
    intro = _pick(_REC_INTROS, used)
    return f"{intro} **{s.name}** — {short_instructions}"


# ── Main response builder ─────────────────────────────────────────────────────

def build_response(
    reasoning: ReasoningOutput,
    recommendation: Recommendation,
    stage: str,
    message_count: int,
    user_message: str = "",
    short_response_streak: int = 0,
    recent_phrases: list[str] | None = None,
) -> str:
    used: list[str] = recent_phrases if recent_phrases is not None else []

    # ── First message ──────────────────────────────────────────────────────────
    if message_count <= 1:
        choice = _pick(_FIRST_MESSAGE_WELCOME, used)
        return choice

    parts: list[str] = []
    emotion = reasoning.emotion_analysis.top_emotion

    # ── Empathetic opening ─────────────────────────────────────────────────────
    parts.append(_opening(emotion, used))

    # ── Stressor acknowledgment ────────────────────────────────────────────────
    stressors = reasoning.emotion_analysis.stressors[:1]
    if stressors:
        parts.append(_stressor_ack(stressors[0], used))

    # ── Reflective listening (first 5 turns, only for substantive messages) ────
    if user_message and message_count <= 5 and len(user_message.split()) >= 8:
        reflection = _reflect_message(user_message, used)
        if reflection:
            parts.append(reflection)

    # ── Open-up mode: user has given 2+ short replies in a row ────────────────
    if short_response_streak >= 2:
        parts.append(_pick(_OPEN_UP_REFLECTIONS, used))
        parts.append(_pick(_PARTIAL_DISCLOSURE_INVITES, used))
        parts.append(_pick(_GENTLE_REOPEN_QUESTIONS, used))
        return "\n\n".join(p for p in parts if p.strip())

    # ── Framework insight (not every turn — skip occasionally to avoid feeling scripted)
    if message_count > 1:
        insight = _framework_insight(reasoning)
        # Skip 30% of the time on even turns to vary the rhythm
        if insight and not (message_count % 2 == 0 and random.random() < 0.3):
            parts.append(insight)

    # ── Practical recommendation (from message 3 onwards, only when user is sharing)
    if message_count >= 3 and short_response_streak == 0 and recommendation.strategies:
        snippet = _recommendation_snippet(recommendation, used)
        if snippet:
            parts.append(snippet)

    # ── Psychoeducation from RAG ───────────────────────────────────────────────
    if recommendation.psychoeducation and short_response_streak == 0:
        edu = recommendation.psychoeducation[:250].strip()
        if edu:
            parts.append(f"*Worth knowing:* {edu}")

    # ── Closing: question or supportive statement ──────────────────────────────
    if short_response_streak == 1:
        parts.append(_pick(_GENTLE_REOPEN_QUESTIONS, used))
    elif reasoning.primary_framework == TherapeuticFramework.SUPPORTIVE or message_count <= 3:
        parts.append(_pick(_FOLLOW_UP_QUESTIONS, used))
    else:
        # Alternate between a question and a supportive statement
        if message_count % 2 == 0:
            parts.append(_pick(_FOLLOW_UP_QUESTIONS, used))
        else:
            parts.append(_pick(_SUPPORTIVE_CLOSING, used))

    return "\n\n".join(p for p in parts if p.strip())

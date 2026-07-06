"""
Rule-based response composer implementing the 6-step conversation protocol:
  1. Understand  — internal analysis (done by reasoning engine)
  2. Validate    — acknowledge the emotion naturally
  3. Explore     — one question, never an interrogation
  4. Reflect     — brief summary of what was understood (turns 4+)
  5. Help        — one practical idea, only after understanding is established
  6. Collaborate — never tell; ask and invite

Principles:
  - No advice before turn 4
  - One question per response, never stacked
  - Permission-seek before giving suggestions
  - Reflect before helping
  - Anti-repeat: _pick() skips recently used phrases
  - No stage prefixes, no self-help-book language
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
    keys = [p[:60] for p in used]
    available = [p for p in pool if p[:60] not in keys]
    choice = random.choice(available if available else pool)
    used.append(choice[:60])
    return choice


# ── Step 1 welcome (first message) ────────────────────────────────────────────

_FIRST_MESSAGE_WELCOME = [
    (
        "Thank you for being here.\n\n"
        "A lot of people find it hard to know where to start — that's completely okay. "
        "You don't need to have it all figured out.\n\n"
        "What's been sitting with you most lately?"
    ),
    (
        "I'm glad you reached out.\n\n"
        "There's no right way to begin this, and no pressure to explain everything at once. "
        "Whatever brought you here is worth talking about.\n\n"
        "Where would you like to start?"
    ),
    (
        "Welcome. I'm here and I'm not going anywhere.\n\n"
        "Sometimes it's hard to put what we're carrying into words — you don't have to have it "
        "all sorted. We can work through it together.\n\n"
        "What's been on your mind?"
    ),
    (
        "I'm glad you're here.\n\n"
        "You don't need a tidy explanation of what's wrong. "
        "Whatever you're feeling, we can start there.\n\n"
        "What's going on for you right now?"
    ),
    (
        "Hello. Thank you for reaching out — it takes something to do that.\n\n"
        "There's no rush here, and nothing you bring is too small or too complicated.\n\n"
        "What's been weighing on you?"
    ),
]

# ── Step 2: Validate ───────────────────────────────────────────────────────────
# Keyed by emotion. Short, natural, not overdone.

_VALIDATION: dict[EmotionCategory, list[str]] = {
    EmotionCategory.SADNESS: [
        "That sounds really painful.",
        "I can hear how heavy this has been.",
        "That's a lot to carry.",
        "That kind of hurt doesn't just go away on its own.",
        "What you're going through sounds genuinely hard.",
        "There's real weight in what you're sharing.",
        "I can see why this has been weighing on you.",
        "That makes a lot of sense, honestly.",
        "Something in what you said tells me you've been hurting for a while.",
        "It sounds exhausting.",
    ],
    EmotionCategory.ANXIETY: [
        "That sounds exhausting — being on edge like that takes a real toll.",
        "I can see why you'd be wound up about this.",
        "Anxiety has a way of making everything feel urgent at once.",
        "It makes sense that this has been sitting heavily.",
        "Living with that kind of worry day to day is genuinely draining.",
        "Your nervous system's been working overtime.",
        "That constant alertness is tiring.",
        "It makes sense you feel unsettled — that's a lot of uncertainty.",
        "Being caught between all of that sounds really hard.",
        "That underlying dread sounds relentless.",
    ],
    EmotionCategory.ANGER: [
        "That frustration makes complete sense.",
        "It sounds like you've been patient with this for a long time.",
        "Something has crossed a line for you — and that matters.",
        "I can see why you'd feel that way.",
        "That kind of friction builds up.",
        "There's a lot of energy behind what you're feeling — and it sounds justified.",
        "It makes sense you'd reach a breaking point.",
        "I hear how much this has worn you down.",
        "Anger like that usually means something important's been ignored for too long.",
        "That's a lot to have been holding.",
    ],
    EmotionCategory.HOPELESSNESS: [
        "That sounds incredibly heavy.",
        "I can hear how stuck you feel.",
        "When things feel that closed off, everything becomes harder.",
        "That kind of emptiness is real.",
        "It makes sense that you'd feel depleted.",
        "Hopelessness is exhausting in a way that's hard to describe to other people.",
        "I hear you. That sounds really hard to sit with.",
        "You're still here, still talking — that matters even when it doesn't feel like it.",
        "When you can't see a way forward, it's hard to take any step at all.",
        "That sense that nothing will change is one of the hardest things to sit with.",
    ],
    EmotionCategory.OVERWHELM: [
        "That sounds like a lot for one person.",
        "It makes sense you'd feel swamped.",
        "When there's no breathing room, even small things become too much.",
        "You've been carrying more than your fair share.",
        "That's a lot coming at you at once.",
        "Everything at once, with no pause — that takes a real toll.",
        "I can see why this feels like too much.",
        "It sounds like you've been running on empty.",
        "That sense of being buried — I hear it.",
        "Too much at once, with no clear way through. That's exhausting.",
    ],
    EmotionCategory.LONELINESS: [
        "That kind of loneliness is its own kind of pain.",
        "Going through something hard without someone to share it with makes everything heavier.",
        "Feeling unseen is real — and it hurts.",
        "It sounds like you've been carrying this alone for a while.",
        "Loneliness can sit right alongside a full life. It doesn't care how many people are around.",
        "Being in pain and feeling like there's no one to tell — that's a lot.",
        "I can hear how isolated you've been feeling.",
        "The ache of not being truly known — that's real.",
        "It makes sense you'd feel disconnected.",
        "You reached out here. Part of you is still looking for connection.",
    ],
    EmotionCategory.GRIEF: [
        "I'm sorry. That's a real loss.",
        "Grief doesn't follow a schedule. However long it takes is however long it takes.",
        "What you lost mattered. It makes sense this still hurts.",
        "There's no right way to grieve.",
        "Loss touches everything, doesn't it.",
        "Grief has a way of resurfacing when you least expect it.",
        "You're allowed to still be affected by this.",
        "Grief is the cost of loving something. That doesn't make it easier.",
        "That loss is still very present for you — I can hear it.",
        "I'm sorry you're going through this.",
    ],
    EmotionCategory.SHAME: [
        "Shame is one of the most isolating things to carry.",
        "I want you to know — feeling this way doesn't make it true.",
        "Shame distorts things. It makes us believe the worst about ourselves.",
        "That sounds really hard to sit with.",
        "Carrying shame is exhausting. You don't have to hold it alone.",
        "A lot of people feel exactly what you're feeling. You're not the exception you think you are.",
        "Shame thrives in silence. The fact that you're speaking about it matters.",
        "You don't have to earn the right to feel okay about yourself.",
        "What you're describing sounds like shame, and shame lies.",
        "That's a heavy thing to be carrying.",
    ],
    EmotionCategory.GUILT: [
        "It sounds like you've been really hard on yourself about this.",
        "That's a heavy thing to be sitting with.",
        "There's a difference between taking responsibility and punishing yourself.",
        "I can hear how much you're judging yourself.",
        "You've been carrying this for a while, haven't you.",
        "It sounds like you've already paid a high price for whatever happened.",
        "You're being much harder on yourself than you'd be on anyone else.",
        "Guilt can keep us stuck in a loop of self-criticism.",
        "I hear how much this is weighing on you.",
        "That sounds exhausting — holding yourself responsible for that.",
    ],
    EmotionCategory.FRUSTRATION: [
        "That frustration makes complete sense.",
        "Hitting the same wall over and over is draining.",
        "When effort isn't producing results, of course you'd feel frustrated.",
        "It sounds like you've been trying, and it keeps not being enough.",
        "I can hear how stuck you feel.",
        "That kind of friction wears on you.",
        "The frustration sounds completely justified.",
        "You've been pushing against something that won't give.",
        "I can see why you'd be at your limit with this.",
        "Something that should be simpler keeps being difficult — of course that's frustrating.",
    ],
    EmotionCategory.JOY: [
        "That's really good to hear.",
        "That sounds like a meaningful moment.",
        "Good — something is working.",
        "I'm glad something is bringing you some light.",
        "That's worth holding onto.",
    ],
    EmotionCategory.RELIEF: [
        "I'm glad some of that pressure has lifted.",
        "That sounds like a weight off.",
        "Good — some breathing room.",
        "That shift matters.",
    ],
    EmotionCategory.NEUTRAL: [
        "I hear you.",
        "Thanks for sharing that.",
        "Tell me more.",
        "I'm listening.",
        "Go on.",
        "I'm with you.",
    ],
}

_DEFAULT_VALIDATION = [
    "I hear you.",
    "That makes sense.",
    "Thanks for sharing that.",
    "I'm listening.",
    "I'm with you.",
]

# ── Step 3: Explore — one question only ───────────────────────────────────────

_EXPLORE_EARLY = [
    "What's been the hardest part of this for you?",
    "When did things start feeling this way?",
    "What does this feel like day to day?",
    "Is there anyone in your life who knows you're feeling this way?",
    "What does it feel like in your body when this comes up?",
    "How long have you been carrying this?",
    "Was there a moment when things shifted, or did it creep up gradually?",
    "What's the thing that's been hardest to say out loud about this?",
    "What's been going on recently that's made this feel more present?",
    "What do you think is underneath all of this?",
    "When did you last feel okay — genuinely okay?",
    "What does a typical day look like for you right now?",
]

_EXPLORE_DEEPER = [
    "What part of this is weighing on you most right now?",
    "Is there something specific that keeps coming back to you about this?",
    "What have you already tried, even if it didn't fully work?",
    "What do you think you actually need right now?",
    "What would 'a little bit better' look like for you?",
    "What feels most stuck?",
    "What do you think is keeping this from shifting?",
    "Is there anything you've been avoiding thinking about?",
    "What would you say to a close friend going through exactly this?",
    "What does your gut tell you about what needs to change?",
    "Has anything made this slightly easier, even briefly?",
    "What feels true about what you just said?",
]

# ── Step 3 (open-up mode): user is giving very short replies ──────────────────

_OPEN_UP_VALIDATES = [
    "It sounds like there might be more beneath that — and that's okay.",
    "Sometimes the hardest things to talk about are the ones that matter most.",
    "You don't have to have it all figured out before you speak.",
    "Whatever you're holding, you can bring it here at your own pace.",
    "It's okay if the words are hard to find right now.",
    "There's no wrong way to talk about this.",
    "You can say as little or as much as you want.",
    "Sometimes just saying the messy version is enough.",
    "Take your time. I'm not going anywhere.",
    "A lot can hide inside a short answer.",
]

_OPEN_UP_INVITES = [
    "You don't need to share more than feels right. But if there's more to it — I'm here.",
    "You can take this one piece at a time. Even just naming what it feels like in your body can be a place to start.",
    "We don't have to go anywhere in a hurry. Sometimes just sitting with something out loud is enough.",
    "Even 'I don't know where to start' is a perfectly fine place to begin.",
    "If the words aren't there yet, you could try describing it around the edges — what it feels like, rather than what it is.",
    "There's no pressure to get to the main thing straightaway.",
    "You can say as little as you need to. I'll work with whatever you give me.",
]

_OPEN_UP_QUESTIONS = [
    "What does a typical day feel like for you right now?",
    "When did things start feeling this way?",
    "What does it feel like in your body when this comes up?",
    "What's the part of this that's hardest to say out loud?",
    "When did you last feel okay — genuinely okay?",
    "Is there something specific that happened recently, or has this been building?",
    "How long have you been carrying this?",
    "What's the thing you haven't been able to tell anyone else?",
    "What does this feel like at its worst?",
    "Is there anyone who knows what you're going through?",
]

# ── Step 4: Reflect — brief summary before helping ────────────────────────────

_REFLECT_TEMPLATES = [
    "So if I'm understanding right — {summary}. Does that sound accurate?",
    "Let me make sure I've got this right. {summary}. Is that close?",
    "From what you've shared — {summary}. Does that feel like a fair picture?",
    "It sounds like {summary}. Am I getting that right?",
    "What I'm hearing is {summary}. Tell me if I'm missing something.",
]

# ── Step 5: Help — permission-seeking before advice ───────────────────────────

_PERMISSION_ASKS = [
    "Would it be okay if I shared something that sometimes helps with this kind of thing?",
    "There's something that research suggests might be useful here — would it help to hear it?",
    "Can I offer one idea? You don't have to take it.",
    "Would it help if we explored something practical together?",
    "There's an approach that tends to work for situations like this — want to hear it?",
    "I've got one thought — would it be okay to share it?",
]

_REC_INTROS = [
    "Something that tends to help with this:",
    "One thing that's worked for others in similar situations:",
    "A small thing worth trying:",
    "Research points to something practical here:",
    "One idea — take it or leave it:",
    "Something concrete that might make a difference:",
]

# ── Step 6: Collaborate ────────────────────────────────────────────────────────

_COLLABORATE = [
    "Does that sound like something worth exploring?",
    "What do you think — does any part of that feel relevant to you?",
    "Would it help if we looked at that together?",
    "What feels realistic from where you're standing right now?",
    "Does that resonate at all?",
    "What do you think would make this even slightly easier?",
    "Is there a version of that that would work for you?",
    "What's your gut reaction to that?",
    "Does that land, or does it feel off?",
    "What feels most true about that?",
]

# ── Supportive closes (no question) ───────────────────────────────────────────

_SUPPORTIVE_CLOSING = [
    "I'm here. Keep going.",
    "You don't have to figure this out today.",
    "Take your time. I'm with you.",
    "Whatever you're feeling, you can bring it here.",
    "You're not carrying this alone right now.",
    "I'm glad you're talking about this.",
    "You've shared something important. I hear it.",
    "None of this has to be resolved today.",
    "That took something to say. I appreciate you trusting me with it.",
    "I'm not going anywhere.",
    "I hear you.",
    "Keep going — I'm listening.",
]

# ── Reflection helpers ─────────────────────────────────────────────────────────

def _build_reflect_summary(reasoning: ReasoningOutput) -> str:
    parts = []
    emotions = reasoning.emotion_analysis.primary_emotions[:2]
    if emotions:
        emotion_words = " and ".join(e.category.value for e in emotions)
        parts.append(f"you've been feeling {emotion_words}")
    stressors = reasoning.emotion_analysis.stressors[:1]
    if stressors:
        parts.append(f"and {stressors[0]} has been a big part of that")
    themes = reasoning.emotion_analysis.themes[:2]
    if themes and not stressors:
        parts.append(f"and there's something around {' and '.join(themes)}")
    return ", ".join(parts) if parts else "this has been weighing on you"


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


def _reflect_user_phrase(user_message: str, used: list[str]) -> str:
    sentences = re.split(r'[.!?]+', user_message.strip())
    sentences = [s.strip() for s in sentences if len(s.strip()) > 8]
    if not sentences:
        return ""
    raw = sentences[0].lower()
    raw = re.sub(r"^i\s+(feel|am|have|was|don't|cant|can't|just)\s+", '', raw)
    raw = raw[:90].strip()
    if not raw:
        return ""
    templates = [
        f'When you say "{raw}" — can you tell me more about that?',
        f'"{raw.capitalize()}" — what does that feel like day to day?',
        f'I noticed "{raw}". What\'s underneath that?',
        f'That phrase — "{raw}" — I don\'t want to rush past it.',
        f'Something about "{raw}" feels important. What does that mean for you?',
        f'I heard "{raw}" and I\'d like to stay with that a moment.',
    ]
    return _pick(templates, used)


def _recommendation_snippet(rec: Recommendation, used: list[str]) -> str:
    if not rec.strategies:
        return ""
    s = rec.strategies[0]
    short = s.instructions[:160] + "…" if len(s.instructions) > 160 else s.instructions
    intro = _pick(_REC_INTROS, used)
    return f"{intro} **{s.name}** — {short}"


# ── Main builder ──────────────────────────────────────────────────────────────

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
    emotion = reasoning.emotion_analysis.top_emotion
    parts: list[str] = []

    # ── Turn 1: Welcome only ───────────────────────────────────────────────────
    if message_count <= 1:
        return _pick(_FIRST_MESSAGE_WELCOME, used)

    # ── Open-up mode: user giving very short replies ───────────────────────────
    if short_response_streak >= 2:
        parts.append(_pick(_OPEN_UP_VALIDATES, used))
        parts.append(_pick(_OPEN_UP_INVITES, used))
        parts.append(_pick(_OPEN_UP_QUESTIONS, used))
        return "\n\n".join(p for p in parts if p.strip())

    # ── Step 2: Validate ───────────────────────────────────────────────────────
    pool = _VALIDATION.get(emotion.category if emotion else EmotionCategory.NEUTRAL, _DEFAULT_VALIDATION)
    parts.append(_pick(pool, used))

    # ── Step 3: Explore — one question or reflection ───────────────────────────
    # On first short reply, gently invite more before asking
    if short_response_streak == 1:
        parts.append(_pick(_OPEN_UP_INVITES, used))
        parts.append(_pick(_OPEN_UP_QUESTIONS, used))
        return "\n\n".join(p for p in parts if p.strip())

    # Reflect a phrase from the user's message (turns 2-5, substantive messages)
    if user_message and message_count <= 5 and len(user_message.split()) >= 8:
        reflection = _reflect_user_phrase(user_message, used)
        if reflection:
            parts.append(reflection)
            return "\n\n".join(p for p in parts if p.strip())

    # Ask one explore question (no advice yet before turn 4)
    if message_count <= 3:
        parts.append(_pick(_EXPLORE_EARLY, used))
        return "\n\n".join(p for p in parts if p.strip())

    # ── Step 4: Reflect (turns 4-5) ───────────────────────────────────────────
    if message_count in (4, 5):
        summary = _build_reflect_summary(reasoning)
        template = _pick(_REFLECT_TEMPLATES, used)
        parts.append(template.format(summary=summary))
        # Add one deeper explore question after reflecting
        parts.append(_pick(_EXPLORE_DEEPER, used))
        return "\n\n".join(p for p in parts if p.strip())

    # ── Step 5 + 6: Help + Collaborate (turn 6+) ──────────────────────────────
    # Framework insight (not every turn — skip 25% of the time to vary rhythm)
    insight = _framework_insight(reasoning)
    if insight and random.random() > 0.25:
        parts.append(insight)

    # Permission-seek before offering a recommendation
    if recommendation.strategies:
        parts.append(_pick(_PERMISSION_ASKS, used))
        snippet = _recommendation_snippet(recommendation, used)
        if snippet:
            parts.append(snippet)
        # Collaborative close
        parts.append(_pick(_COLLABORATE, used))
    else:
        # No recommendation — supportive close or deeper question
        if message_count % 2 == 0:
            parts.append(_pick(_EXPLORE_DEEPER, used))
        else:
            parts.append(_pick(_SUPPORTIVE_CLOSING, used))

    # Psychoeducation from RAG (if available and not too much already)
    if recommendation.psychoeducation and len(parts) < 4:
        edu = recommendation.psychoeducation[:200].strip()
        if edu:
            parts.append(f"*Worth knowing:* {edu}")

    return "\n\n".join(p for p in parts if p.strip())

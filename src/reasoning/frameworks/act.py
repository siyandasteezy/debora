"""ACT framework — template-based, no external API."""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from src.reasoning.emotion_detector import EmotionThemeAnalysis


@dataclass
class ACTGuidance:
    acceptance_prompt: str
    defusion_exercise: str
    values_exploration: str
    committed_action_step: str
    present_moment_anchor: str
    metaphor: str | None
    relevant_processes: list[str]


_ACCEPTANCE_PROMPTS = [
    "What if, just for now, you allowed this feeling to be here without fighting it?",
    "Can you make a little room for this emotion — not to like it, but just to let it exist?",
    "What would it feel like to stop struggling with this feeling for just a moment?",
    "This feeling is uncomfortable — and it doesn't have to go away for you to move forward.",
]

_DEFUSION_EXERCISES = [
    "Try saying 'I notice I'm having the thought that…' before your most painful thought. Notice how that small shift changes your relationship to it.",
    "Imagine your thoughts as leaves floating down a stream. You don't have to grab any of them — just watch them pass.",
    "Name the thought: 'There's the self-critic again.' Giving it a name creates distance between you and the story.",
    "Say the painful thought in a funny voice, or very slowly. Notice how it becomes just words, rather than absolute truth.",
]

_VALUES_QUESTIONS = [
    "Setting the struggle aside for a moment — what matters most to you in this area of your life?",
    "If this difficult feeling weren't in the way, what would you be moving towards?",
    "What kind of person do you want to be, regardless of how you feel right now?",
    "What would you be doing differently if you were living according to your deepest values?",
]

_COMMITTED_ACTIONS = [
    "What's one tiny step, no bigger than five minutes, that moves toward what matters to you today?",
    "Even while carrying this, what is one thing you could do that would feel meaningful?",
    "What would taking one small step look like — not to fix the feeling, but to keep living by your values?",
]

_GROUNDING = [
    "Right now, plant both feet on the floor. Feel the ground beneath you. Take one slow breath. You are here.",
    "Notice three things in your physical environment right now. What do you see? What do you hear? What do you feel against your skin?",
    "Take a slow breath in for four counts, hold for four, out for six. Just this breath, right now.",
]

_METAPHORS = [
    "Imagine your mind as a sky and your thoughts as weather — storms pass, and the sky remains.",
    "Think of yourself as a chess board, not the chess pieces. The struggle happens on you, not as you.",
    "Emotions are like waves — they build, peak, and pass. You are the ocean, not the wave.",
    None,
]


async def apply_act(
    user_message: str,
    emotion_analysis: EmotionThemeAnalysis,
) -> ACTGuidance:
    has_goals = bool(emotion_analysis.goals_mentioned)
    processes = ["acceptance", "defusion", "present_moment"]
    if has_goals:
        processes += ["values", "committed_action"]

    return ACTGuidance(
        acceptance_prompt=random.choice(_ACCEPTANCE_PROMPTS),
        defusion_exercise=random.choice(_DEFUSION_EXERCISES),
        values_exploration=random.choice(_VALUES_QUESTIONS),
        committed_action_step=random.choice(_COMMITTED_ACTIONS),
        present_moment_anchor=random.choice(_GROUNDING),
        metaphor=random.choice(_METAPHORS),
        relevant_processes=processes[:4],
    )

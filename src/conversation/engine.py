"""
Conversation Engine — the main orchestrator.

Pipeline per turn:
  1. Safety check (always first, can short-circuit)
  2. Load/update memory context
  3. Run reasoning (parallel: emotion + distortion → framework)
  4. RAG retrieval (parallel with reasoning)
  5. Build recommendations
  6. Compose system prompt
  7. Generate response
  8. Persist everything
"""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from src.memory.context import ConversationContext
from src.memory.store import (
    get_cross_session_summary,
    load_context,
    persist_message,
    save_context,
    update_memory_from_analysis,
)
from src.rag.pipeline import RAGResult, build_rag_query, run_rag
from src.reasoning.engine import ReasoningOutput, run_reasoning
from src.recommendations.engine import build_recommendations, format_recommendations_for_response
from src.safety.layer import SafetyResult, append_disclaimer, run_safety_check
from src.utils.logger import get_logger
from src.utils.responder import build_response

logger = get_logger(__name__)


@dataclass
class TurnInput:
    user_message: str
    session_id: uuid.UUID
    user_id: uuid.UUID
    has_consent: bool = False
    country_code: str = "US"


@dataclass
class TurnOutput:
    response: str
    session_id: uuid.UUID
    safety_triggered: bool = False
    safety_event_id: uuid.UUID | None = None
    framework_used: str = ""
    emotions_detected: list[str] = field(default_factory=list)
    themes_detected: list[str] = field(default_factory=list)
    rag_sources: list[dict] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0


async def process_turn(turn: TurnInput, db: AsyncSession) -> TurnOutput:
    """Process one conversation turn end-to-end."""
    logger.info("turn_start", session_id=str(turn.session_id))

    # ── 1. Safety check (always first) ────────────────────────────────────────
    context = await load_context(turn.session_id)
    history_str = context.to_history_string()

    safety_result = await run_safety_check(
        text=turn.user_message,
        session_id=turn.session_id,
        user_id=turn.user_id,
        db=db,
        conversation_context=history_str,
        country_code=turn.country_code,
    )

    # Persist user message
    user_msg = await persist_message(
        session_id=turn.session_id,
        role="user",
        content=turn.user_message,
        db=db,
        analysis={
            "safety_flags": [
                s.crisis_type.value
                for s in safety_result.assessment.signals
            ]
        } if safety_result.assessment.signals else None,
    )
    context.add_message("user", turn.user_message, str(user_msg.id))

    # Safety override: bypass full pipeline and return crisis response
    if safety_result.should_override_response and safety_result.crisis_response:
        final_response = safety_result.crisis_response
        assistant_msg = await persist_message(
            session_id=turn.session_id,
            role="assistant",
            content=final_response,
            db=db,
        )
        context.add_message("assistant", final_response, str(assistant_msg.id))
        await save_context(turn.session_id, context)
        return TurnOutput(
            response=final_response,
            session_id=turn.session_id,
            safety_triggered=True,
            safety_event_id=safety_result.safety_event_id,
        )

    # ── 2. Load cross-session context ─────────────────────────────────────────
    cross_session_summary = ""
    if turn.has_consent:
        cross_session_summary = await get_cross_session_summary(turn.user_id, db)
    if cross_session_summary:
        context.session_summary = cross_session_summary

    # ── Engagement tracking: score the previous framework based on this reply ──
    word_count = len(turn.user_message.split())
    if context.last_framework_used:
        engagement = min(1.0, word_count / 50.0)
        scores = context.framework_scores.setdefault(context.last_framework_used, [])
        scores.append(engagement)
        context.framework_scores[context.last_framework_used] = scores[-10:]

    context.short_response_streak = (
        context.short_response_streak + 1 if word_count < 20 else 0
    )

    # ── 3 & 4. Reasoning + RAG in parallel ────────────────────────────────────
    reasoning_task = asyncio.create_task(
        run_reasoning(
            user_message=turn.user_message,
            conversation_history=context.to_history_string(),
            message_count=context.message_count,
            framework_scores=context.framework_scores,
        )
    )

    # Build RAG query optimistically while reasoning runs
    preliminary_rag_query = turn.user_message[:200]
    rag_task = asyncio.create_task(
        run_rag(
            query=preliminary_rag_query,
            user_context=history_str[:300],
        )
    )

    reasoning_output, rag_result = await asyncio.gather(reasoning_task, rag_task)

    # ── 5. Build recommendations ───────────────────────────────────────────────
    recommendations = await build_recommendations(reasoning_output, rag_result)

    # ── 6 & 7. Build response from templates ──────────────────────────────────
    response_text = build_response(
        reasoning=reasoning_output,
        recommendation=recommendations,
        stage=reasoning_output.conversation_stage,
        message_count=context.message_count,
        user_message=turn.user_message,
        short_response_streak=context.short_response_streak,
    )
    context.last_framework_used = reasoning_output.primary_framework.value
    input_tokens, output_tokens = 0, 0

    if safety_result.disclaimer_needed:
        response_text = append_disclaimer(response_text)

    # ── 8. Persist assistant response ──────────────────────────────────────────
    assistant_msg = await persist_message(
        session_id=turn.session_id,
        role="assistant",
        content=response_text,
        db=db,
        token_count=output_tokens,
        rag_sources=rag_result.sources_as_dicts if rag_result else [],
    )
    context.add_message("assistant", response_text, str(assistant_msg.id))

    # Update memory from analysis (with consent)
    await update_memory_from_analysis(
        session_id=turn.session_id,
        user_id=turn.user_id,
        context=context,
        emotion_analysis=reasoning_output.emotion_analysis,
        db=db,
        has_consent=turn.has_consent,
    )

    await save_context(turn.session_id, context)

    logger.info(
        "turn_complete",
        session_id=str(turn.session_id),
        framework=reasoning_output.primary_framework.value,
        stage=reasoning_output.conversation_stage,
        tokens_in=input_tokens,
        tokens_out=output_tokens,
    )

    return TurnOutput(
        response=response_text,
        session_id=turn.session_id,
        safety_triggered=safety_result.assessment.is_crisis,
        safety_event_id=safety_result.safety_event_id,
        framework_used=reasoning_output.primary_framework.value,
        emotions_detected=[
            e.category.value for e in reasoning_output.emotion_analysis.primary_emotions
        ],
        themes_detected=reasoning_output.emotion_analysis.themes,
        rag_sources=rag_result.sources_as_dicts if rag_result else [],
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


def _format_framework_guidance(reasoning: ReasoningOutput) -> str:
    """Convert framework-specific dataclass to a readable instruction block."""
    from src.reasoning.frameworks.cbt import CBTGuidance
    from src.reasoning.frameworks.act import ACTGuidance
    from src.reasoning.frameworks.dbt import DBTGuidance
    from src.reasoning.frameworks.motivational_interviewing import MIGuidance
    from src.reasoning.frameworks.positive_psychology import PPGuidance

    g = reasoning.framework_guidance
    fw = reasoning.primary_framework.value
    rationale = reasoning.reasoning_rationale

    if g is None:
        return f"Framework: {fw}\nRationale: {rationale}\nFocus on empathic listening."

    lines = [f"Framework: {fw.upper()}", f"Rationale: {rationale}"]

    if isinstance(g, CBTGuidance):
        lines += [
            f"Thought challenge: {g.thought_challenge}",
            f"Balanced alternative: {g.balanced_thought}",
            f"Socratic questions to consider: {'; '.join(g.socratic_questions[:2])}",
        ]
    elif isinstance(g, ACTGuidance):
        lines += [
            f"Acceptance prompt: {g.acceptance_prompt}",
            f"Defusion: {g.defusion_exercise}",
            f"Values exploration: {g.values_exploration}",
        ]
    elif isinstance(g, DBTGuidance):
        lines += [
            f"VALIDATION: {g.validation_statement}",
            f"DBT skill ({g.module}): {g.skill_name} — {g.immediate_exercise}",
            f"Wise mind: {g.wise_mind_reflection}",
        ]
    elif isinstance(g, MIGuidance):
        lines += [
            f"Reflection: {g.reflection}",
            f"Affirmation: {g.affirmation}",
            f"Evoking question: {g.evoking_question}",
        ]
    elif isinstance(g, PPGuidance):
        lines += [
            f"Strength spotting: {', '.join(g.strength_spotting[:3])}",
            f"Meaning reflection: {g.meaning_reflection}",
            f"Growth reframe: {g.growth_reframe}",
        ]

    return "\n".join(lines)

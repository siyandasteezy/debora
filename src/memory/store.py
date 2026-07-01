"""
Memory persistence — stores conversation context in Redis (fast session cache)
and PostgreSQL (durable cross-session memory) with user consent gating.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.db.models import ConversationSession, MemorySnapshot, Message, User, UserGoal
from src.memory.context import ConversationContext, ContextMessage
from src.reasoning.emotion_detector import EmotionThemeAnalysis
from src.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

_redis: aioredis.Redis | None = None


async def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = await aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


def _session_key(session_id: uuid.UUID) -> str:
    return f"session:{session_id}:context"


async def load_context(session_id: uuid.UUID) -> ConversationContext:
    """Load conversation context from Redis cache."""
    redis = await _get_redis()
    raw = await redis.get(_session_key(session_id))
    if not raw:
        return ConversationContext()
    data = json.loads(raw)
    ctx = ConversationContext(
        session_summary=data.get("session_summary", ""),
        user_goals=data.get("user_goals", []),
        recurring_themes=data.get("recurring_themes", []),
        identified_strengths=data.get("identified_strengths", []),
        stressors=data.get("stressors", []),
        framework_scores=data.get("framework_scores", {}),
        last_framework_used=data.get("last_framework_used", ""),
        short_response_streak=data.get("short_response_streak", 0),
    )
    for m in data.get("messages", []):
        ctx.messages.append(ContextMessage(**m))
    return ctx


async def save_context(session_id: uuid.UUID, context: ConversationContext) -> None:
    """Persist context to Redis with TTL."""
    redis = await _get_redis()
    data = {
        "session_summary": context.session_summary,
        "user_goals": context.user_goals,
        "recurring_themes": context.recurring_themes,
        "identified_strengths": context.identified_strengths,
        "stressors": context.stressors,
        "framework_scores": context.framework_scores,
        "last_framework_used": context.last_framework_used,
        "short_response_streak": context.short_response_streak,
        "messages": [
            {"role": m.role, "content": m.content, "message_id": m.message_id}
            for m in context.messages
        ],
    }
    await redis.setex(_session_key(session_id), settings.redis_ttl_seconds, json.dumps(data))


async def persist_message(
    session_id: uuid.UUID,
    role: str,
    content: str,
    db: AsyncSession,
    token_count: int | None = None,
    analysis: dict | None = None,
    rag_sources: list | None = None,
) -> Message:
    """Write a message to PostgreSQL."""
    msg = Message(
        session_id=session_id,
        role=role,
        content=content,
        token_count=token_count,
        emotions=analysis.get("emotions", []) if analysis else [],
        cognitive_distortions=analysis.get("distortions", []) if analysis else [],
        themes=analysis.get("themes", []) if analysis else [],
        safety_flags=analysis.get("safety_flags", []) if analysis else [],
        rag_sources=rag_sources or [],
    )
    db.add(msg)
    await db.flush()
    return msg


async def update_memory_from_analysis(
    session_id: uuid.UUID,
    user_id: uuid.UUID,
    context: ConversationContext,
    emotion_analysis: EmotionThemeAnalysis,
    db: AsyncSession,
    has_consent: bool = True,
) -> None:
    """Merge new analysis into session context and DB snapshot (with consent)."""
    # Update in-memory context
    for goal in emotion_analysis.goals_mentioned:
        if goal not in context.user_goals:
            context.user_goals.append(goal)
    for theme in emotion_analysis.themes:
        if theme not in context.recurring_themes:
            context.recurring_themes.append(theme)
    for strength in emotion_analysis.strengths:
        if strength not in context.identified_strengths:
            context.identified_strengths.append(strength)
    for stressor in emotion_analysis.stressors:
        if stressor not in context.stressors:
            context.stressors.append(stressor)

    if not has_consent:
        return

    # Persist goals to DB
    for goal_text in emotion_analysis.goals_mentioned:
        existing = await db.scalar(
            select(UserGoal).where(
                UserGoal.user_id == user_id,
                UserGoal.description == goal_text,
                UserGoal.status == "active",
            )
        )
        if not existing:
            db.add(UserGoal(user_id=user_id, description=goal_text, confidence_score=0.7))

    # Update DB session record
    session = await db.get(ConversationSession, session_id)
    if session:
        session.detected_emotions = [
            {"category": e.category.value, "intensity": e.intensity}
            for e in emotion_analysis.primary_emotions
        ]
        session.detected_themes = emotion_analysis.themes

    await db.flush()


async def get_cross_session_summary(user_id: uuid.UUID, db: AsyncSession) -> str:
    """Load last memory snapshot for cross-session continuity."""
    result = await db.scalars(
        select(MemorySnapshot)
        .where(
            MemorySnapshot.user_id == user_id,
            MemorySnapshot.snapshot_type == "cross_session",
        )
        .order_by(MemorySnapshot.created_at.desc())
        .limit(1)
    )
    snapshot = result.first()
    if not snapshot:
        return ""
    parts = []
    if snapshot.goals_summary:
        parts.append(f"Previous goals: {snapshot.goals_summary}")
    if snapshot.recurring_themes:
        parts.append(f"Recurring themes: {', '.join(snapshot.recurring_themes)}")
    if snapshot.strengths:
        parts.append(f"Known strengths: {', '.join(snapshot.strengths)}")
    return " | ".join(parts)

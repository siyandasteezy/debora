"""SQLAlchemy ORM models for all modules."""
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin, UUIDMixin


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    anonymous_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    preferred_language: Mapped[str] = mapped_column(String(10), default="en")
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)

    sessions: Mapped[list["ConversationSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    goals: Mapped[list["UserGoal"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class ConversationSession(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "conversation_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(
        Enum("active", "ended", "crisis_escalated", name="session_status"),
        default="active",
    )
    primary_theme: Mapped[str | None] = mapped_column(String(128))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    summary: Mapped[str | None] = mapped_column(Text)
    detected_emotions: Mapped[list] = mapped_column(JSON, default=list)
    detected_themes: Mapped[list] = mapped_column(JSON, default=list)

    user: Mapped["User"] = relationship(back_populates="sessions")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="Message.created_at"
    )
    memory_snapshots: Mapped[list["MemorySnapshot"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    safety_events: Mapped[list["SafetyEvent"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class Message(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "messages"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversation_sessions.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(
        Enum("user", "assistant", "system", name="message_role"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer)

    # Analysis results attached to user messages
    emotions: Mapped[list] = mapped_column(JSON, default=list)
    cognitive_distortions: Mapped[list] = mapped_column(JSON, default=list)
    themes: Mapped[list] = mapped_column(JSON, default=list)
    safety_flags: Mapped[list] = mapped_column(JSON, default=list)

    # RAG sources used in assistant response
    rag_sources: Mapped[list] = mapped_column(JSON, default=list)

    session: Mapped["ConversationSession"] = relationship(back_populates="messages")


class MemorySnapshot(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "memory_snapshots"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversation_sessions.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    snapshot_type: Mapped[str] = mapped_column(
        Enum("session", "cross_session", name="snapshot_type"), default="session"
    )
    goals_summary: Mapped[str | None] = mapped_column(Text)
    stressors: Mapped[list] = mapped_column(JSON, default=list)
    strengths: Mapped[list] = mapped_column(JSON, default=list)
    recurring_themes: Mapped[list] = mapped_column(JSON, default=list)
    coping_strategies_tried: Mapped[list] = mapped_column(JSON, default=list)
    progress_notes: Mapped[str | None] = mapped_column(Text)

    session: Mapped["ConversationSession"] = relationship(back_populates="memory_snapshots")


class UserGoal(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "user_goals"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("active", "achieved", "abandoned", name="goal_status"), default="active"
    )
    confidence_score: Mapped[float] = mapped_column(Float, default=0.8)
    source_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL")
    )

    user: Mapped["User"] = relationship(back_populates="goals")


class SafetyEvent(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "safety_events"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversation_sessions.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    event_type: Mapped[str] = mapped_column(
        Enum(
            "suicidal_ideation",
            "self_harm",
            "abuse",
            "psychosis",
            "mania",
            "general_crisis",
            name="safety_event_type",
        )
    )
    severity: Mapped[str] = mapped_column(
        Enum("low", "moderate", "high", "critical", name="safety_severity")
    )
    confidence: Mapped[float] = mapped_column(Float)
    triggering_message_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    response_sent: Mapped[str | None] = mapped_column(Text)
    resources_provided: Mapped[list] = mapped_column(JSON, default=list)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)

    session: Mapped["ConversationSession"] = relationship(back_populates="safety_events")


class KnowledgeSource(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "knowledge_sources"

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    authors: Mapped[list] = mapped_column(JSON, default=list)
    source_type: Mapped[str] = mapped_column(
        Enum("pubmed", "who", "nice", "cochrane", "apa", "nhs", "other", name="source_type")
    )
    url: Mapped[str | None] = mapped_column(String(1024))
    doi: Mapped[str | None] = mapped_column(String(256))
    pubmed_id: Mapped[str | None] = mapped_column(String(64))
    publication_year: Mapped[int | None] = mapped_column(Integer)
    abstract: Mapped[str | None] = mapped_column(Text)
    full_text_available: Mapped[bool] = mapped_column(Boolean, default=False)
    qdrant_vector_id: Mapped[str | None] = mapped_column(String(256))
    tags: Mapped[list] = mapped_column(JSON, default=list)
    evidence_level: Mapped[str | None] = mapped_column(String(64))

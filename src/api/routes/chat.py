"""Chat endpoint — single entry point for all conversations."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.conversation.engine import TurnInput, TurnOutput, process_turn
from src.db.models import ConversationSession, User
from src.db.session import get_db
from src.utils.logger import get_logger

router = APIRouter(prefix="/chat", tags=["chat"])
logger = get_logger(__name__)


class ChatRequest(BaseModel):
    session_id: uuid.UUID
    message: str = Field(min_length=1, max_length=4000)
    country_code: str = Field(default="US", max_length=5)


class SourceCitation(BaseModel):
    id: str
    title: str
    source_type: str
    citation: str
    year: int | None = None
    url: str | None = None
    evidence_level: str | None = None
    similarity_score: float


class ChatResponse(BaseModel):
    response: str
    session_id: str
    safety_triggered: bool
    framework_used: str
    emotions_detected: list[str]
    themes_detected: list[str]
    sources: list[SourceCitation]
    message_id: str | None = None


@router.post("", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    # Validate session
    session = await db.get(ConversationSession, req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status == "ended":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Session has ended. Please create a new session.",
        )

    user = await db.get(User, session.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    turn = TurnInput(
        user_message=req.message,
        session_id=req.session_id,
        user_id=session.user_id,
        has_consent=user.consent_given,
        country_code=req.country_code,
    )

    try:
        result: TurnOutput = await process_turn(turn, db)
    except Exception as e:
        logger.error(
            "turn_processing_failed",
            session_id=str(req.session_id),
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred processing your message. Please try again.",
        )

    # If crisis, update session status
    if result.safety_triggered and session.status != "crisis_escalated":
        session.status = "crisis_escalated"
        await db.flush()

    return ChatResponse(
        response=result.response,
        session_id=str(result.session_id),
        safety_triggered=result.safety_triggered,
        framework_used=result.framework_used,
        emotions_detected=result.emotions_detected,
        themes_detected=result.themes_detected,
        sources=[SourceCitation(**s) for s in result.rag_sources],
    )

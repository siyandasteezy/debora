"""Session management endpoints."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import ConversationSession, User
from src.db.session import get_db
from src.utils.logger import get_logger

router = APIRouter(prefix="/sessions", tags=["sessions"])
logger = get_logger(__name__)


class CreateSessionRequest(BaseModel):
    anonymous_id: str
    consent_given: bool = False
    country_code: str = "US"
    preferred_language: str = "en"


class SessionResponse(BaseModel):
    session_id: str
    user_id: str
    status: str
    consent_given: bool


class ConsentUpdateRequest(BaseModel):
    consent_given: bool


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    req: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    # Upsert user by anonymous_id
    user = await db.scalar(
        select(User).where(User.anonymous_id == req.anonymous_id)
    )
    if not user:
        user = User(
            anonymous_id=req.anonymous_id,
            consent_given=req.consent_given,
            preferred_language=req.preferred_language,
        )
        db.add(user)
        await db.flush()
    elif req.consent_given and not user.consent_given:
        user.consent_given = True
        await db.flush()

    session = ConversationSession(user_id=user.id)
    db.add(session)
    await db.flush()

    logger.info("session_created", session_id=str(session.id), user_id=str(user.id))

    return SessionResponse(
        session_id=str(session.id),
        user_id=str(user.id),
        status=session.status,
        consent_given=user.consent_given,
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    session = await db.get(ConversationSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    user = await db.get(User, session.user_id)
    return SessionResponse(
        session_id=str(session.id),
        user_id=str(session.user_id),
        status=session.status,
        consent_given=user.consent_given if user else False,
    )


@router.patch("/{session_id}/consent", response_model=SessionResponse)
async def update_consent(
    session_id: uuid.UUID,
    req: ConsentUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    session = await db.get(ConversationSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    user = await db.get(User, session.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.consent_given = req.consent_given
    await db.flush()
    return SessionResponse(
        session_id=str(session.id),
        user_id=str(session.user_id),
        status=session.status,
        consent_given=user.consent_given,
    )


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def end_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    session = await db.get(ConversationSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    from datetime import datetime, timezone
    session.status = "ended"
    session.ended_at = datetime.now(timezone.utc)
    await db.flush()
    logger.info("session_ended", session_id=str(session_id))

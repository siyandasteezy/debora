"""
Safety Layer — always the first module executed in the pipeline.
Wraps crisis detection, protocol selection, audit logging, and DB persistence.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import SafetyEvent
from src.safety.crisis_detector import CrisisAssessment, Severity, assess_crisis
from src.safety.protocols import SYSTEM_BOUNDARY_STATEMENT, build_crisis_response
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SafetyResult:
    assessment: CrisisAssessment
    should_override_response: bool
    crisis_response: str | None
    safety_event_id: uuid.UUID | None = None
    disclaimer_needed: bool = False


async def run_safety_check(
    text: str,
    session_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
    conversation_context: str = "",
    country_code: str = "US",
) -> SafetyResult:
    """
    Execute safety layer. Returns SafetyResult that the conversation engine MUST inspect
    before generating any response.
    """
    assessment = await assess_crisis(text, conversation_context)

    if not assessment.is_crisis:
        return SafetyResult(
            assessment=assessment,
            should_override_response=False,
            crisis_response=None,
            disclaimer_needed=_needs_disclaimer(text),
        )

    signal = assessment.primary_signal
    crisis_response = build_crisis_response(assessment, country_code)

    event = SafetyEvent(
        session_id=session_id,
        user_id=user_id,
        event_type=signal.crisis_type.value,
        severity=signal.severity.value,
        confidence=signal.confidence,
        response_sent=crisis_response,
        resources_provided=[
            {"type": s.crisis_type.value, "confidence": s.confidence}
            for s in assessment.signals
        ],
    )
    db.add(event)
    await db.flush()

    logger.warning(
        "safety_event_logged",
        event_id=str(event.id),
        session_id=str(session_id),
        event_type=signal.crisis_type.value,
        severity=signal.severity.value,
    )

    should_override = (
        signal.severity in (Severity.HIGH, Severity.CRITICAL)
        or signal.requires_immediate_response
    )

    return SafetyResult(
        assessment=assessment,
        should_override_response=should_override,
        crisis_response=crisis_response,
        safety_event_id=event.id,
        disclaimer_needed=True,
    )


def _needs_disclaimer(text: str) -> bool:
    """Soft trigger: mention of diagnosis, medication, or therapy."""
    import re
    pattern = re.compile(
        r"\b(diagnos|medicat|prescri|psychiatr|therapist|counsell|antidepress|antipsychot)\b",
        re.IGNORECASE,
    )
    return bool(pattern.search(text))


def append_disclaimer(response: str) -> str:
    return f"{response}\n\n---\n*{SYSTEM_BOUNDARY_STATEMENT}*"

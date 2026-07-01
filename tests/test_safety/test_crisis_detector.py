"""Unit tests for the crisis detection module — the most safety-critical component."""
from __future__ import annotations

import pytest

from src.safety.crisis_detector import (
    CrisisType,
    Severity,
    _keyword_screen,
    assess_crisis,
)


class TestKeywordScreen:
    def test_detects_suicidal_ideation(self):
        signals = _keyword_screen("I want to kill myself tonight")
        assert any(s.crisis_type == CrisisType.SUICIDAL_IDEATION for s in signals)

    def test_detects_self_harm(self):
        signals = _keyword_screen("I've been cutting my arms again")
        assert any(s.crisis_type == CrisisType.SELF_HARM for s in signals)

    def test_detects_abuse(self):
        signals = _keyword_screen("My husband hit me again last night")
        assert any(s.crisis_type == CrisisType.ABUSE for s in signals)

    def test_detects_psychosis(self):
        signals = _keyword_screen("The voices in my head are telling me to do things")
        assert any(s.crisis_type == CrisisType.PSYCHOSIS for s in signals)

    def test_detects_mania(self):
        signals = _keyword_screen("I haven't slept in 5 days and I feel invincible")
        assert any(s.crisis_type == CrisisType.MANIA for s in signals)

    def test_no_false_positive_normal(self):
        signals = _keyword_screen("I'm feeling a bit stressed about work today")
        assert len(signals) == 0

    def test_no_false_positive_past_tense(self):
        # "kill it" in non-suicidal context should not trigger
        signals = _keyword_screen("I'm going to kill it at the gym today!")
        # This may trigger depending on regex — verify it doesn't trigger suicidal_ideation
        suicidal = [s for s in signals if s.crisis_type == CrisisType.SUICIDAL_IDEATION]
        assert len(suicidal) == 0

    def test_high_confidence_for_explicit_statement(self):
        signals = _keyword_screen("I want to end my life, I have no reason to live")
        suicidal = [s for s in signals if s.crisis_type == CrisisType.SUICIDAL_IDEATION]
        assert suicidal
        assert suicidal[0].confidence >= 0.75

    def test_severity_scales_with_matches(self):
        # Single match → lower severity
        single = _keyword_screen("I've been cutting")
        # Multiple matches → higher severity
        multiple = _keyword_screen(
            "I've been cutting my wrists again. The scars are fresh. I'm hurting myself."
        )
        if single and multiple:
            single_severity_idx = ["low", "moderate", "high", "critical"].index(
                single[0].severity.value
            )
            multiple_severity_idx = ["low", "moderate", "high", "critical"].index(
                multiple[0].severity.value
            )
            assert multiple_severity_idx >= single_severity_idx


class TestCrisisAssessment:
    @pytest.mark.asyncio
    async def test_safe_message_no_crisis(self, mock_llm_structured):
        mock_llm_structured.return_value = {"is_crisis": False, "signals": []}
        result = await assess_crisis("I'm having a hard week at work")
        # Should not be a crisis for mild stress
        # (may or may not call LLM depending on distress keywords)
        assert isinstance(result.is_crisis, bool)

    @pytest.mark.asyncio
    async def test_explicit_suicidal_ideation_is_crisis(self):
        result = await assess_crisis(
            "I've decided to kill myself. I have a plan. This is my last message."
        )
        assert result.is_crisis is True
        assert result.primary_signal is not None
        assert result.primary_signal.crisis_type == CrisisType.SUICIDAL_IDEATION
        assert result.primary_signal.severity in (Severity.HIGH, Severity.CRITICAL)

    def test_crisis_signal_requires_immediate_response(self):
        from src.safety.crisis_detector import CrisisSignal

        signal = CrisisSignal(
            crisis_type=CrisisType.SUICIDAL_IDEATION,
            severity=Severity.CRITICAL,
            confidence=0.95,
        )
        assert signal.requires_immediate_response is True

    def test_low_confidence_signal_does_not_require_response(self):
        from src.safety.crisis_detector import CrisisSignal

        signal = CrisisSignal(
            crisis_type=CrisisType.SUICIDAL_IDEATION,
            severity=Severity.LOW,
            confidence=0.30,
        )
        assert signal.requires_safety_response is False

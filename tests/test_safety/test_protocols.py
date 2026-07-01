"""Tests for safe messaging protocol generation."""
from __future__ import annotations

import pytest

from src.safety.crisis_detector import CrisisAssessment, CrisisSignal, CrisisType, Severity
from src.safety.protocols import build_crisis_response
from src.safety.resources import format_resources_for_response, get_resources


def _make_assessment(
    crisis_type: CrisisType,
    severity: Severity = Severity.HIGH,
    confidence: float = 0.90,
) -> CrisisAssessment:
    signal = CrisisSignal(
        crisis_type=crisis_type,
        severity=severity,
        confidence=confidence,
    )
    return CrisisAssessment(is_crisis=True, signals=[signal], primary_signal=signal)


class TestCrisisResponse:
    def test_suicidal_critical_mentions_emergency_services(self):
        assessment = _make_assessment(CrisisType.SUICIDAL_IDEATION, Severity.CRITICAL)
        response = build_crisis_response(assessment, "US")
        assert "emergency" in response.lower() or "911" in response

    def test_suicidal_critical_includes_resources(self):
        assessment = _make_assessment(CrisisType.SUICIDAL_IDEATION, Severity.CRITICAL)
        response = build_crisis_response(assessment, "US")
        assert "988" in response  # US suicide lifeline

    def test_abuse_response_does_not_diagnose(self):
        assessment = _make_assessment(CrisisType.ABUSE)
        response = build_crisis_response(assessment, "US")
        assert "disorder" not in response.lower()
        assert "diagnos" not in response.lower()

    def test_response_is_non_judgmental(self):
        assessment = _make_assessment(CrisisType.SELF_HARM)
        response = build_crisis_response(assessment)
        # Should not contain shaming language
        assert "stupid" not in response.lower()
        assert "wrong" not in response.lower()
        assert "shouldn't" not in response.lower()

    def test_south_africa_resources(self):
        assessment = _make_assessment(CrisisType.SUICIDAL_IDEATION, Severity.HIGH)
        response = build_crisis_response(assessment, "ZA")
        assert "SADAG" in response or "Lifeline" in response

    def test_psychosis_recommends_medical_help(self):
        assessment = _make_assessment(CrisisType.PSYCHOSIS)
        response = build_crisis_response(assessment, "US")
        assert "doctor" in response.lower() or "medical" in response.lower() or "healthcare" in response.lower()


class TestResources:
    def test_us_resources_for_suicidal_ideation(self):
        resources = get_resources(CrisisType.SUICIDAL_IDEATION, "US")
        assert len(resources) >= 1
        assert any("988" in (r.phone or "") for r in resources)

    def test_gb_resources_include_samaritans(self):
        resources = get_resources(CrisisType.GENERAL_CRISIS, "GB")
        assert any("Samaritans" in r.name for r in resources)

    def test_format_resources_not_empty(self):
        resources = get_resources(CrisisType.SUICIDAL_IDEATION, "US")
        formatted = format_resources_for_response(resources)
        assert len(formatted) > 50
        assert "**" in formatted

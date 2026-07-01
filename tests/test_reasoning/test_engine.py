"""Tests for the reasoning engine framework selection logic."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from src.reasoning.distortion_detector import CognitiveDistortion, DetectedDistortion, DistortionAnalysis
from src.reasoning.emotion_detector import DetectedEmotion, EmotionCategory, EmotionThemeAnalysis
from src.reasoning.engine import TherapeuticFramework, _select_framework


def _make_emotion(category: EmotionCategory, intensity: float) -> DetectedEmotion:
    return DetectedEmotion(
        category=category,
        intensity=intensity,
        confidence=0.85,
        valence=-0.7 if intensity > 0.5 else 0.1,
        explicit=True,
        evidence="test evidence",
    )


def _make_distortion(distortion: CognitiveDistortion, confidence: float) -> DetectedDistortion:
    return DetectedDistortion(
        distortion=distortion,
        confidence=confidence,
        evidence="I always fail",
        reframe_suggestion="Is it really always?",
    )


class TestFrameworkSelection:
    def test_high_distress_selects_dbt(self):
        emotion = EmotionThemeAnalysis(
            primary_emotions=[_make_emotion(EmotionCategory.OVERWHELM, 0.9)],
            distress_level=0.85,
            overall_valence=-0.8,
        )
        distortion = DistortionAnalysis()
        framework, rationale = _select_framework(emotion, distortion)
        assert framework == TherapeuticFramework.DBT
        assert "distress" in rationale.lower()

    def test_cognitive_distortions_selects_cbt(self):
        emotion = EmotionThemeAnalysis(
            primary_emotions=[_make_emotion(EmotionCategory.SADNESS, 0.6)],
            distress_level=0.5,
            overall_valence=-0.5,
        )
        distortion = DistortionAnalysis(
            distortions=[
                _make_distortion(CognitiveDistortion.ALL_OR_NOTHING, 0.85),
                _make_distortion(CognitiveDistortion.CATASTROPHISING, 0.80),
            ],
            overall_distortion_level=0.75,
        )
        framework, rationale = _select_framework(emotion, distortion)
        assert framework == TherapeuticFramework.CBT

    def test_low_distress_selects_positive_psychology(self):
        emotion = EmotionThemeAnalysis(
            primary_emotions=[_make_emotion(EmotionCategory.NEUTRAL, 0.2)],
            distress_level=0.2,
            overall_valence=0.1,
        )
        distortion = DistortionAnalysis()
        framework, _ = _select_framework(emotion, distortion)
        assert framework == TherapeuticFramework.POSITIVE_PSYCHOLOGY

    def test_ambivalence_themes_selects_mi(self):
        emotion = EmotionThemeAnalysis(
            primary_emotions=[_make_emotion(EmotionCategory.CONFUSION, 0.5)],
            distress_level=0.4,
            themes=["motivation", "change"],
            goals_mentioned=["stop procrastinating"],
            overall_valence=-0.2,
        )
        distortion = DistortionAnalysis()
        framework, _ = _select_framework(emotion, distortion)
        assert framework == TherapeuticFramework.MI

    def test_existential_themes_selects_act(self):
        emotion = EmotionThemeAnalysis(
            primary_emotions=[_make_emotion(EmotionCategory.LONELINESS, 0.55)],
            distress_level=0.45,
            themes=["meaning", "values"],
            overall_valence=-0.3,
        )
        distortion = DistortionAnalysis()
        framework, _ = _select_framework(emotion, distortion)
        assert framework == TherapeuticFramework.ACT


class TestReasoningEngine:
    @pytest.mark.asyncio
    async def test_run_reasoning_returns_output(self):
        emotion_return = {
            "primary_emotions": [
                {
                    "category": "sadness",
                    "intensity": 0.6,
                    "confidence": 0.8,
                    "valence": -0.6,
                    "explicit": True,
                    "evidence": "I feel sad",
                }
            ],
            "secondary_emotions": [],
            "themes": ["loneliness"],
            "stressors": ["isolation"],
            "strengths": [],
            "goals_mentioned": [],
            "overall_valence": -0.5,
            "distress_level": 0.5,
        }
        distortion_return = {
            "distortions": [],
            "overall_distortion_level": 0.0,
        }
        cbt_return = {
            "thought_challenge": "test challenge",
            "balanced_thought": "test balanced",
            "socratic_questions": ["Q1?", "Q2?"],
        }

        call_count = [0]
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return emotion_return
            if call_count[0] == 2:
                return distortion_return
            return cbt_return

        from src.reasoning.engine import run_reasoning

        with patch("src.reasoning.emotion_detector.structured_completion", side_effect=side_effect), \
             patch("src.reasoning.distortion_detector.structured_completion", side_effect=lambda *a, **k: distortion_return), \
             patch("src.reasoning.frameworks.cbt.structured_completion", return_value=cbt_return), \
             patch("src.reasoning.frameworks.act.structured_completion", return_value={}), \
             patch("src.reasoning.frameworks.dbt.structured_completion", return_value={}), \
             patch("src.reasoning.frameworks.motivational_interviewing.structured_completion", return_value={}), \
             patch("src.reasoning.frameworks.positive_psychology.structured_completion", return_value={}):

            with patch("src.reasoning.emotion_detector.structured_completion", return_value=emotion_return), \
                 patch("src.reasoning.distortion_detector.structured_completion", return_value=distortion_return):
                result = await run_reasoning("I feel really sad and lonely today")

        assert result is not None
        assert result.emotion_analysis is not None
        assert result.distortion_analysis is not None
        assert result.primary_framework is not None

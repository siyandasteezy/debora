"""Tests for the coping strategy recommendation engine."""
from __future__ import annotations

import pytest

from src.recommendations.strategies import CopingStrategy, get_strategies_for


class TestStrategyRecommendation:
    def test_anxiety_themes_return_relevant_strategies(self):
        strategies = get_strategies_for(themes=["anxiety", "stress"], distress_level=0.6)
        assert len(strategies) > 0
        ids = {s.id for s in strategies}
        # Box breathing is highly relevant for anxiety
        assert "box_breathing" in ids or "5_4_3_2_1_grounding" in ids

    def test_high_distress_returns_appropriate_strategies(self):
        strategies = get_strategies_for(themes=["overwhelm", "crisis"], distress_level=0.85)
        for s in strategies:
            assert s.min_distress <= 0.85 <= s.max_distress

    def test_low_distress_filters_crisis_strategies(self):
        strategies = get_strategies_for(themes=["existential", "meaning"], distress_level=0.15)
        # TIPP skill requires distress >= 0.6 — should not appear for low distress
        ids = {s.id for s in strategies}
        assert "tipp_skill" not in ids

    def test_depression_returns_behavioural_activation(self):
        strategies = get_strategies_for(
            themes=["depression", "sadness", "hopelessness"],
            distress_level=0.5,
        )
        ids = {s.id for s in strategies}
        assert "behavioural_activation" in ids

    def test_max_count_respected(self):
        strategies = get_strategies_for(
            themes=["anxiety", "stress", "depression", "overwhelm"],
            distress_level=0.6,
            max_count=2,
        )
        assert len(strategies) <= 2

    def test_all_strategies_have_evidence_level(self):
        from src.recommendations.strategies import STRATEGIES
        for strategy in STRATEGIES:
            assert strategy.evidence_level in ("high", "moderate", "emerging")

    def test_all_strategies_have_instructions(self):
        from src.recommendations.strategies import STRATEGIES
        for strategy in STRATEGIES:
            assert len(strategy.instructions) > 20

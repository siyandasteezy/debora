"""Integration tests for the API endpoints."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestSessionsEndpoint:
    @pytest.mark.asyncio
    async def test_create_session(self, client):
        response = await client.post(
            "/api/v1/sessions",
            json={"anonymous_id": str(uuid.uuid4()), "consent_given": True},
        )
        assert response.status_code == 201
        data = response.json()
        assert "session_id" in data
        assert "user_id" in data
        assert data["status"] == "active"

    @pytest.mark.asyncio
    async def test_create_session_without_consent(self, client):
        response = await client.post(
            "/api/v1/sessions",
            json={"anonymous_id": str(uuid.uuid4()), "consent_given": False},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["consent_given"] is False

    @pytest.mark.asyncio
    async def test_get_session(self, client):
        # Create first
        create_resp = await client.post(
            "/api/v1/sessions",
            json={"anonymous_id": str(uuid.uuid4())},
        )
        session_id = create_resp.json()["session_id"]

        # Then fetch
        get_resp = await client.get(f"/api/v1/sessions/{session_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["session_id"] == session_id

    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self, client):
        response = await client.get(f"/api/v1/sessions/{uuid.uuid4()}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_consent(self, client):
        create_resp = await client.post(
            "/api/v1/sessions",
            json={"anonymous_id": str(uuid.uuid4()), "consent_given": False},
        )
        session_id = create_resp.json()["session_id"]

        patch_resp = await client.patch(
            f"/api/v1/sessions/{session_id}/consent",
            json={"consent_given": True},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["consent_given"] is True

    @pytest.mark.asyncio
    async def test_end_session(self, client):
        create_resp = await client.post(
            "/api/v1/sessions",
            json={"anonymous_id": str(uuid.uuid4())},
        )
        session_id = create_resp.json()["session_id"]

        delete_resp = await client.delete(f"/api/v1/sessions/{session_id}")
        assert delete_resp.status_code == 204


class TestChatEndpoint:
    @pytest.mark.asyncio
    async def test_chat_requires_valid_session(self, client):
        response = await client.post(
            "/api/v1/chat",
            json={"session_id": str(uuid.uuid4()), "message": "Hello"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_chat_success(self, client, mock_redis):
        # Create session
        create_resp = await client.post(
            "/api/v1/sessions",
            json={"anonymous_id": str(uuid.uuid4()), "consent_given": True},
        )
        session_id = create_resp.json()["session_id"]

        with patch("src.conversation.engine.run_safety_check") as mock_safety, \
             patch("src.conversation.engine.run_reasoning") as mock_reasoning, \
             patch("src.conversation.engine.run_rag") as mock_rag, \
             patch("src.conversation.engine.chat_completion") as mock_chat, \
             patch("src.memory.store._get_redis") as mock_store_redis:

            # Configure mocks
            from src.safety.crisis_detector import CrisisAssessment
            from src.safety.layer import SafetyResult
            from src.reasoning.engine import ReasoningOutput, TherapeuticFramework
            from src.reasoning.emotion_detector import EmotionThemeAnalysis
            from src.reasoning.distortion_detector import DistortionAnalysis

            mock_safety.return_value = SafetyResult(
                assessment=CrisisAssessment(is_crisis=False),
                should_override_response=False,
                crisis_response=None,
            )
            mock_reasoning.return_value = ReasoningOutput(
                emotion_analysis=EmotionThemeAnalysis(
                    primary_emotions=[],
                    secondary_emotions=[],
                    themes=["stress"],
                    stressors=["work"],
                    strengths=[],
                    goals_mentioned=[],
                    overall_valence=-0.3,
                    distress_level=0.4,
                ),
                distortion_analysis=DistortionAnalysis(),
                primary_framework=TherapeuticFramework.SUPPORTIVE,
                framework_guidance=None,
                reasoning_rationale="Low distress, supportive listening",
                conversation_stage="explore",
            )
            mock_rag.return_value = None
            mock_chat.return_value = ("I hear you. Can you tell me more?", 100, 30)

            redis_mock = AsyncMock()
            redis_mock.get.return_value = None
            redis_mock.setex.return_value = True
            mock_store_redis.return_value = redis_mock

            response = await client.post(
                "/api/v1/chat",
                json={"session_id": session_id, "message": "I'm feeling stressed"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "safety_triggered" in data
        assert data["safety_triggered"] is False

    @pytest.mark.asyncio
    async def test_message_too_long_rejected(self, client):
        create_resp = await client.post(
            "/api/v1/sessions",
            json={"anonymous_id": str(uuid.uuid4())},
        )
        session_id = create_resp.json()["session_id"]

        response = await client.post(
            "/api/v1/chat",
            json={"session_id": session_id, "message": "x" * 4001},
        )
        assert response.status_code == 422  # Pydantic validation error

    @pytest.mark.asyncio
    async def test_ended_session_rejected(self, client):
        create_resp = await client.post(
            "/api/v1/sessions",
            json={"anonymous_id": str(uuid.uuid4())},
        )
        session_id = create_resp.json()["session_id"]
        await client.delete(f"/api/v1/sessions/{session_id}")

        response = await client.post(
            "/api/v1/chat",
            json={"session_id": session_id, "message": "Hello"},
        )
        assert response.status_code == 409

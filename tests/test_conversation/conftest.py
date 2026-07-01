"""Conftest for API integration tests — patches Redis and mocks lifespan."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.db.session import get_db


@pytest.fixture(autouse=True)
def mock_all_redis():
    """Patch every Redis connection so tests don't need a live Redis."""
    redis_mock = AsyncMock()
    redis_mock.get.return_value = None
    redis_mock.setex.return_value = True
    redis_mock.incr.return_value = 1
    redis_mock.expire.return_value = True
    redis_mock.ping.return_value = True

    with patch("src.api.middleware._get_redis", return_value=redis_mock), \
         patch("src.memory.store._get_redis", return_value=redis_mock), \
         patch("src.rag.embedder._get_redis", return_value=redis_mock):
        yield redis_mock


@pytest_asyncio.fixture
async def client(db):
    from src.main import create_app

    app = create_app()
    app.dependency_overrides[get_db] = lambda: db

    # Disable lifespan so startup doesn't try to connect to Qdrant
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=True),
        base_url="http://test",
    ) as ac:
        yield ac

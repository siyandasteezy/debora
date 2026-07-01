"""Shared test fixtures. DB fixtures are NOT autouse — only tests that import them pay the cost."""
from __future__ import annotations

import os
import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Ensure required env vars are present during tests
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-32chars-minimum-xyz!!")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_mhe.db")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")

from src.db.base import Base
from src.db.models import ConversationSession, User
from src.db.session import get_db

# ── In-memory SQLite for tests ─────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_mhe.db"

_test_engine = None
_TestSessionFactory = None


def _get_test_engine():
    global _test_engine, _TestSessionFactory
    if _test_engine is None:
        _test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
        _TestSessionFactory = async_sessionmaker(
            bind=_test_engine, expire_on_commit=False, autoflush=False
        )
    return _test_engine, _TestSessionFactory


@pytest_asyncio.fixture(scope="module")
async def db_engine():
    """Create tables once per module, tear down after."""
    engine, _ = _get_test_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db(db_engine) -> AsyncGenerator[AsyncSession, None]:
    _, factory = _get_test_engine()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    from src.main import create_app
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def test_user(db: AsyncSession) -> User:
    user = User(anonymous_id=str(uuid.uuid4()), consent_given=True)
    db.add(user)
    await db.flush()
    return user


@pytest_asyncio.fixture
async def test_session(db: AsyncSession, test_user: User) -> ConversationSession:
    session = ConversationSession(user_id=test_user.id)
    db.add(session)
    await db.flush()
    return session


# ── Mock LLM to avoid API calls ───────────────────────────────────────────
@pytest.fixture
def mock_llm_chat():
    with patch("src.utils.llm.chat_completion") as mock:
        mock.return_value = (
            "I hear you. It sounds like you're going through a difficult time. "
            "Can you tell me more about what's been happening?",
            150,
            60,
        )
        yield mock


@pytest.fixture
def mock_llm_structured():
    with patch("src.utils.llm.structured_completion") as mock:
        mock.return_value = {}
        yield mock


@pytest.fixture
def mock_redis():
    with patch("src.memory.store._get_redis") as mock:
        redis_mock = AsyncMock()
        redis_mock.get.return_value = None
        redis_mock.setex.return_value = True
        redis_mock.incr.return_value = 1
        redis_mock.expire.return_value = True
        mock.return_value = redis_mock
        yield redis_mock

"""FastAPI application factory and startup."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.middleware import AccessLogMiddleware, RateLimitMiddleware, RequestIDMiddleware
from src.api.routes import chat, health, sessions
from src.config import get_settings
from src.db.base import Base
from src.db.session import engine
from src.rag.retriever import ensure_collection
from src.utils.logger import configure_logging, get_logger

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info("startup", env=settings.app_env)

    # Ensure DB tables exist (in production use Alembic migrations instead)
    if settings.app_env == "development":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    # Ensure Qdrant collection exists
    try:
        await ensure_collection()
    except Exception as e:
        logger.warning("qdrant_init_failed", error=str(e))

    yield

    logger.info("shutdown")
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Mental Health Reasoning Engine",
        description=(
            "Research-backed emotional support, psychoeducation, and coping guidance. "
            "NOT a substitute for professional mental health care."
        ),
        version="1.0.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["*"],
    )

    # Custom middleware (outermost first)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RequestIDMiddleware)

    # Routes
    app.include_router(health.router)
    app.include_router(sessions.router, prefix="/api/v1")
    app.include_router(chat.router, prefix="/api/v1")

    return app


app = create_app()

"""
Text embedding with local sentence-transformers or OpenAI as fallback.
Embeddings are cached in Redis to avoid re-computing for identical text.
"""
from __future__ import annotations

import hashlib
import json
from typing import cast

import redis.asyncio as aioredis

from src.config import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

_local_model = None
_redis_client: aioredis.Redis | None = None

EMBEDDING_DIM = 384  # all-MiniLM-L6-v2 dimension


def _get_local_model():
    global _local_model
    if _local_model is None:
        from sentence_transformers import SentenceTransformer
        _local_model = SentenceTransformer(settings.embedding_model)
        logger.info("embedding_model_loaded", model=settings.embedding_model)
    return _local_model


async def _get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = await aioredis.from_url(
            settings.redis_url, encoding="utf-8", decode_responses=True
        )
    return _redis_client


def _cache_key(text: str) -> str:
    return f"emb:{hashlib.sha256(text.encode()).hexdigest()[:16]}"


async def embed_text(text: str) -> list[float]:
    """Embed a single text string. Cached per unique text hash."""
    redis = await _get_redis()
    key = _cache_key(text)

    cached = await redis.get(key)
    if cached:
        return cast(list[float], json.loads(cached))

    embedding = await _compute_embedding(text)
    await redis.setex(key, settings.redis_ttl_seconds, json.dumps(embedding))
    return embedding


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Batch embed multiple texts."""
    return [await embed_text(t) for t in texts]


async def _compute_embedding(text: str) -> list[float]:
    if settings.embedding_provider == "local":
        model = _get_local_model()
        vector = model.encode(text, normalize_embeddings=True)
        return vector.tolist()
    else:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.embeddings.create(
            model=settings.embedding_model,
            input=text,
        )
        return response.data[0].embedding

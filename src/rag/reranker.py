"""Reranking by similarity score — no external API."""
from __future__ import annotations

from src.config import get_settings
from src.rag.sources import SourceDocument
from src.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


async def rerank(
    query: str,
    documents: list[SourceDocument],
    top_k: int | None = None,
) -> list[SourceDocument]:
    k = top_k or settings.rag_rerank_top_k
    sorted_docs = sorted(documents, key=lambda d: getattr(d, "similarity_score", 0.0), reverse=True)
    return sorted_docs[:k]

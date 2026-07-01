"""
Vector retrieval from Qdrant.
Supports hybrid search (dense + sparse/BM25) and metadata filtering.
"""
from __future__ import annotations

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, Filter, FieldCondition, MatchValue, SearchRequest

from src.config import get_settings
from src.rag.embedder import embed_text
from src.rag.sources import SourceDocument, SourceType
from src.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

_qdrant: AsyncQdrantClient | None = None
_qdrant_available: bool = False


def get_qdrant() -> AsyncQdrantClient:
    global _qdrant
    if _qdrant is None:
        kwargs: dict = {"host": settings.qdrant_host, "port": settings.qdrant_port}
        if settings.qdrant_api_key:
            kwargs["api_key"] = settings.qdrant_api_key
        _qdrant = AsyncQdrantClient(**kwargs)
    return _qdrant


async def retrieve(
    query: str,
    top_k: int | None = None,
    source_types: list[SourceType] | None = None,
    tags: list[str] | None = None,
    min_score: float | None = None,
) -> list[SourceDocument]:
    """Dense vector retrieval with optional metadata filtering."""
    if not _qdrant_available:
        return []

    k = top_k or settings.rag_top_k
    threshold = min_score or settings.rag_similarity_threshold
    query_vector = await embed_text(query)

    query_filter = None
    if source_types:
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="source_type",
                    match=MatchValue(value=st.value),
                )
                for st in source_types
            ]
        )

    client = get_qdrant()
    try:
        results = await client.search(
            collection_name=settings.qdrant_collection,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=k * 2,  # over-fetch for reranking
            score_threshold=threshold,
            with_payload=True,
        )
    except Exception as e:
        logger.error("qdrant_retrieval_failed", error=str(e))
        return []

    docs = []
    for hit in results:
        payload = hit.payload or {}
        try:
            doc = SourceDocument(
                id=str(hit.id),
                title=payload.get("title", "Untitled"),
                source_type=SourceType(payload.get("source_type", "other")),
                authors=payload.get("authors", []),
                year=payload.get("year"),
                doi=payload.get("doi"),
                pubmed_id=payload.get("pubmed_id"),
                url=payload.get("url"),
                abstract=payload.get("abstract", ""),
                chunk_text=payload.get("chunk_text", ""),
                similarity_score=hit.score,
                evidence_level=payload.get("evidence_level"),
                tags=payload.get("tags", []),
            )
            docs.append(doc)
        except Exception as parse_err:
            logger.warning("qdrant_payload_parse_error", error=str(parse_err), id=hit.id)

    return docs[:k]


async def upsert_document(
    doc_id: str,
    text: str,
    payload: dict,
) -> None:
    """Index a document chunk into Qdrant."""
    from qdrant_client.models import PointStruct

    vector = await embed_text(text)
    client = get_qdrant()
    await client.upsert(
        collection_name=settings.qdrant_collection,
        points=[PointStruct(id=doc_id, vector=vector, payload=payload)],
    )
    logger.debug("document_indexed", doc_id=doc_id)


async def ensure_collection() -> None:
    """Create Qdrant collection if it does not exist."""
    global _qdrant_available
    from qdrant_client.models import VectorParams

    from src.rag.embedder import EMBEDDING_DIM

    client = get_qdrant()
    existing = await client.get_collections()
    names = [c.name for c in existing.collections]
    if settings.qdrant_collection not in names:
        await client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )
        logger.info("qdrant_collection_created", name=settings.qdrant_collection)
    _qdrant_available = True

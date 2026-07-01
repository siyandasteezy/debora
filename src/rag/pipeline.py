"""
RAG Pipeline — retrieval and reranking. Synthesis is now done via template concatenation.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.rag.reranker import rerank
from src.rag.retriever import retrieve
from src.rag.sources import SourceDocument, SourceType
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RAGResult:
    synthesised_content: str
    sources: list[SourceDocument]
    query_used: str
    citations_inline: str

    @property
    def sources_as_dicts(self) -> list[dict]:
        return [s.to_response_dict() for s in self.sources]


async def run_rag(
    query: str,
    user_context: str = "",
    source_types: list[SourceType] | None = None,
    force_retrieval: bool = False,
) -> RAGResult | None:
    search_query = f"{query}\n{user_context}".strip() if user_context else query

    documents = await retrieve(search_query, source_types=source_types)

    if not documents:
        logger.info("rag_no_results", query=query[:80])
        return None

    top_docs = await rerank(search_query, documents)

    if not top_docs:
        return None

    # Concatenate top source excerpts directly — no LLM synthesis
    excerpts = []
    for i, doc in enumerate(top_docs[:2]):
        excerpt = doc.chunk_text[:300].strip()
        if excerpt:
            excerpts.append(f"{excerpt} ({doc.citation})")

    synthesised = " ".join(excerpts) if excerpts else top_docs[0].citation

    citations = "\n".join(
        f"[{i + 1}] {doc.citation}" + (f" | Evidence: {doc.evidence_label}" if doc.evidence_level else "")
        for i, doc in enumerate(top_docs)
    )

    logger.info("rag_complete", query=query[:60], docs_retrieved=len(documents), docs_used=len(top_docs))

    return RAGResult(
        synthesised_content=synthesised,
        sources=top_docs,
        query_used=search_query,
        citations_inline=citations,
    )


def build_rag_query(theme: str, framework: str, emotion: str | None = None) -> str:
    parts = [theme, framework]
    if emotion:
        parts.append(emotion)
    return " ".join(parts) + " evidence-based intervention psychotherapy"

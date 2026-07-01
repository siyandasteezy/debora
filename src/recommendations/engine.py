"""
Recommendation Engine — combines strategy library with RAG-grounded psychoeducation.
Produces actionable, evidence-linked recommendations without diagnosing.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.rag.pipeline import RAGResult
from src.rag.sources import SourceType
from src.reasoning.engine import ReasoningOutput, TherapeuticFramework
from src.recommendations.strategies import CopingStrategy, get_strategies_for
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Recommendation:
    strategies: list[CopingStrategy]
    psychoeducation: str | None
    rag_result: RAGResult | None
    framework_used: str
    when_to_seek_help: str


_WHEN_TO_SEEK_HELP = (
    "If what you're experiencing feels persistent (more than two weeks), significantly "
    "interferes with daily life, or if you're having thoughts of harming yourself or others, "
    "please speak with a mental health professional or GP. You deserve real human support."
)


async def build_recommendations(
    reasoning: ReasoningOutput,
    rag_result: RAGResult | None,
) -> Recommendation:
    emotion_analysis = reasoning.emotion_analysis
    strategies = get_strategies_for(
        themes=emotion_analysis.themes + [e.category.value for e in emotion_analysis.primary_emotions],
        distress_level=emotion_analysis.distress_level,
    )

    psychoeducation = None
    if rag_result:
        psychoeducation = rag_result.synthesised_content

    return Recommendation(
        strategies=strategies,
        psychoeducation=psychoeducation,
        rag_result=rag_result,
        framework_used=reasoning.primary_framework.value,
        when_to_seek_help=_WHEN_TO_SEEK_HELP,
    )


def format_recommendations_for_response(rec: Recommendation) -> str:
    """Format for inclusion in the assistant's response."""
    parts: list[str] = []

    if rec.psychoeducation:
        parts.append(f"**What the research says:**\n{rec.psychoeducation}")

    if rec.strategies:
        parts.append("\n**Evidence-based tools you might try:**")
        for i, strategy in enumerate(rec.strategies[:2], 1):
            parts.append(
                f"\n*{i}. {strategy.name}* ({strategy.evidence_level} evidence)\n"
                f"{strategy.description}\n"
                f"*How:* {strategy.instructions[:200]}..."
                if len(strategy.instructions) > 200
                else (
                    f"\n*{i}. {strategy.name}* ({strategy.evidence_level} evidence)\n"
                    f"{strategy.description}\n"
                    f"*How:* {strategy.instructions}"
                )
            )

    parts.append(f"\n---\n*{rec.when_to_seek_help}*")

    return "\n".join(parts)

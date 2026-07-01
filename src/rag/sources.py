"""
Source metadata and provenance tracking for RAG results.
Every claim surfaced in a response must be traceable to a specific source.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SourceType(str, Enum):
    PUBMED = "pubmed"
    WHO = "who"
    NICE = "nice"
    COCHRANE = "cochrane"
    APA = "apa"
    NHS = "nhs"
    OTHER = "other"


_EVIDENCE_LEVEL_DESCRIPTIONS = {
    "1a": "Systematic review of RCTs (highest)",
    "1b": "Individual RCT with narrow CI",
    "2a": "Systematic review of cohort studies",
    "2b": "Individual cohort study / low-quality RCT",
    "3a": "Systematic review of case-control studies",
    "3b": "Individual case-control study",
    "4":  "Case series / poor cohort study",
    "5":  "Expert opinion",
}


@dataclass
class SourceDocument:
    id: str
    title: str
    source_type: SourceType
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    doi: str | None = None
    pubmed_id: str | None = None
    url: str | None = None
    abstract: str = ""
    chunk_text: str = ""
    similarity_score: float = 0.0
    evidence_level: str | None = None
    tags: list[str] = field(default_factory=list)

    @property
    def citation(self) -> str:
        """APA-ish short citation string."""
        author_str = (
            f"{self.authors[0].split()[-1]} et al." if len(self.authors) > 1
            else self.authors[0] if self.authors
            else "Unknown"
        )
        year = f" ({self.year})" if self.year else ""
        doi = f" doi:{self.doi}" if self.doi else ""
        return f"{author_str}{year}. {self.title}.{doi}"

    @property
    def evidence_label(self) -> str:
        if not self.evidence_level:
            return ""
        desc = _EVIDENCE_LEVEL_DESCRIPTIONS.get(self.evidence_level, "")
        return f"[Level {self.evidence_level}: {desc}]" if desc else f"[Level {self.evidence_level}]"

    def to_response_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "source_type": self.source_type.value,
            "citation": self.citation,
            "year": self.year,
            "url": self.url,
            "evidence_level": self.evidence_level,
            "similarity_score": round(self.similarity_score, 3),
        }

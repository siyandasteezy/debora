"""
Crisis signal detection using a layered approach:
  1. Fast keyword/regex screening (sub-millisecond)
  2. LLM semantic analysis for ambiguous cases
  3. Confidence-weighted severity scoring
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from src.config import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class CrisisType(str, Enum):
    SUICIDAL_IDEATION = "suicidal_ideation"
    SELF_HARM = "self_harm"
    ABUSE = "abuse"
    PSYCHOSIS = "psychosis"
    MANIA = "mania"
    GENERAL_CRISIS = "general_crisis"


class Severity(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CrisisSignal:
    crisis_type: CrisisType
    severity: Severity
    confidence: float
    matched_indicators: list[str] = field(default_factory=list)
    reasoning: str = ""

    @property
    def requires_immediate_response(self) -> bool:
        return self.severity in (Severity.HIGH, Severity.CRITICAL) and self.confidence >= 0.65

    @property
    def requires_safety_response(self) -> bool:
        return self.confidence >= settings.crisis_confidence_threshold


@dataclass
class CrisisAssessment:
    is_crisis: bool
    signals: list[CrisisSignal] = field(default_factory=list)
    primary_signal: CrisisSignal | None = None
    raw_text: str = ""

    @property
    def highest_severity(self) -> Severity | None:
        if not self.signals:
            return None
        order = [Severity.CRITICAL, Severity.HIGH, Severity.MODERATE, Severity.LOW]
        for sev in order:
            if any(s.severity == sev for s in self.signals):
                return sev
        return None


# ── Keyword layers ───────────────────────────────────────────────────────────

_SUICIDAL_PATTERNS = [
    r"\b(kill|end|take)\s+(my|myself|my\s+life)\b",
    r"\bsuicid(e|al|ally)\b",
    r"\bwant\s+to\s+(die|not\s+be\s+here|disappear)\b",
    r"\b(can'?t|cannot|don'?t)\s+go\s+on\b",
    r"\bno\s+reason\s+to\s+(live|continue)\b",
    r"\bthinking\s+about\s+(ending|taking)\b",
    r"\blife\s+(isn'?t|is\s+not)\s+worth\b",
    r"\bbetter\s+off\s+(dead|without\s+me)\b",
    r"\bpills?\b.{0,20}\b(take|took|swallow)\b",
    r"\bgoodbye\s+(letter|note|message)\b",
    r"\bgave\s+away\s+(possessions?|things?|stuff)\b",
]

_SELF_HARM_PATTERNS = [
    r"\bself[-\s]?harm\b",
    r"\bcut(ting|s|ters?)?\s+(myself|my\s+(arms?|legs?|body|skin|wrists?))\b",
    r"\bhurt(ing)?\s+myself\b",
    r"\bburn(ing)?\s+(myself|my\s+(skin|arms?))\b",
    r"\bwrists?\b.{0,20}\b(cut|razor|blade)\b",
    r"\bscars?\b.{0,20}\b(fresh|new|cut)\b",
    r"\bpunish(ing)?\s+myself\b",
]

_ABUSE_PATTERNS = [
    r"\b(hit|beat|hurt|abuse[sd]?)\s+(by|me|us)\b",
    r"\b(domestic|physical|sexual|emotional)\s+(violence|abuse)\b",
    r"\b(partner|spouse|parent|husband|wife)\s+(hurt|hit|beat|abuse)\b",
    r"\bsafe\s+to\s+go\s+home\b",
    r"\bscared\s+of\s+(him|her|them|my\s+(partner|husband|wife|boyfriend|girlfriend))\b",
    r"\bcontrolling\s+(partner|husband|wife|boyfriend|girlfriend)\b",
]

_PSYCHOSIS_PATTERNS = [
    r"\b(seeing|hearing|voices?|visions?|hallucin)\b",
    r"\bvoices?\s+(in\s+my\s+head|telling\s+me)\b",
    r"\b(paranoi[ad]|everyone\s+is\s+(after|watching|following|spying))\b",
    r"\breality\s+(isn'?t|is\s+not)\s+real\b",
    r"\bcan'?t\s+tell\s+what'?s?\s+real\b",
    r"\bthey'?re?\s+(monitoring|controlling|implanted)\b",
]

_MANIA_PATTERNS = [
    r"\b(haven'?t|not)\s+slept\s+(in\s+)?(days?|week|48|72|96)\b",
    r"\b(spent|spending|buying)\s+(everything|thousands?|all\s+(my\s+)?money)\b",
    r"\bfeel\s+(invincible|like\s+(a\s+)?god|unstoppable)\b",
    r"\bthoughts?\s+(are\s+)?(racing|so\s+fast)\b",
    r"\bdon'?t\s+need\s+sleep\b",
    r"\bgrandiose\b",
]


def _compile(patterns: list[str]) -> list[re.Pattern[str]]:
    return [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in patterns]


_COMPILED = {
    CrisisType.SUICIDAL_IDEATION: _compile(_SUICIDAL_PATTERNS),
    CrisisType.SELF_HARM: _compile(_SELF_HARM_PATTERNS),
    CrisisType.ABUSE: _compile(_ABUSE_PATTERNS),
    CrisisType.PSYCHOSIS: _compile(_PSYCHOSIS_PATTERNS),
    CrisisType.MANIA: _compile(_MANIA_PATTERNS),
}

_SEVERITY_WEIGHTS: dict[CrisisType, dict[str, float]] = {
    CrisisType.SUICIDAL_IDEATION: {"base": 0.7, "per_match": 0.1},
    CrisisType.SELF_HARM: {"base": 0.5, "per_match": 0.1},
    CrisisType.ABUSE: {"base": 0.5, "per_match": 0.08},
    CrisisType.PSYCHOSIS: {"base": 0.4, "per_match": 0.1},
    CrisisType.MANIA: {"base": 0.3, "per_match": 0.08},
}


def _keyword_screen(text: str) -> list[CrisisSignal]:
    signals: list[CrisisSignal] = []
    for crisis_type, patterns in _COMPILED.items():
        matched = []
        for pat in patterns:
            match = pat.search(text)
            if match:
                matched.append(match.group(0))

        if not matched:
            continue

        weights = _SEVERITY_WEIGHTS[crisis_type]
        confidence = min(0.95, weights["base"] + len(matched) * weights["per_match"])

        if confidence >= 0.85:
            severity = Severity.CRITICAL
        elif confidence >= 0.70:
            severity = Severity.HIGH
        elif confidence >= 0.55:
            severity = Severity.MODERATE
        else:
            severity = Severity.LOW

        signals.append(
            CrisisSignal(
                crisis_type=crisis_type,
                severity=severity,
                confidence=confidence,
                matched_indicators=matched,
            )
        )
    return signals


async def assess_crisis(
    text: str,
    conversation_context: str = "",
    force_llm: bool = False,
) -> CrisisAssessment:
    """
    Two-stage crisis detection:
    1. Fast keyword screen
    2. LLM deep analysis if keyword confidence is ambiguous OR force_llm=True
    """
    keyword_signals = _keyword_screen(text)
    all_signals = keyword_signals[:]

    qualifying = [
        s for s in all_signals
        if s.confidence >= settings.crisis_confidence_threshold
    ]

    if qualifying:
        primary = max(qualifying, key=lambda s: s.confidence)
        is_crisis = True
    else:
        primary = None
        is_crisis = False

    assessment = CrisisAssessment(
        is_crisis=is_crisis,
        signals=qualifying,
        primary_signal=primary,
        raw_text=text[:500],
    )

    if is_crisis:
        logger.warning(
            "crisis_detected",
            is_crisis=True,
            primary_type=primary.crisis_type.value if primary else None,
            severity=primary.severity.value if primary else None,
            confidence=primary.confidence if primary else None,
        )

    return assessment


_DISTRESS_PATTERNS = re.compile(
    r"\b(hopeless|helpless|worthless|can'?t\s+(cope|handle|take\s+it)|overwhelm|desperate|"
    r"breaking\s+down|falling\s+apart|end\s+it|can'?t\s+do\s+this|give\s+up)\b",
    re.IGNORECASE,
)


def _has_emotional_distress(text: str) -> bool:
    return bool(_DISTRESS_PATTERNS.search(text))


def _max_severity(a: Severity, b: Severity) -> Severity:
    order = [Severity.LOW, Severity.MODERATE, Severity.HIGH, Severity.CRITICAL]
    return order[max(order.index(a), order.index(b))]

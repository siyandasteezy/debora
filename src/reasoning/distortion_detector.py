"""
Cognitive distortion detection — pattern matching, no external API.
Based on Aaron Beck's CBT model.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from src.utils.logger import get_logger

logger = get_logger(__name__)


class CognitiveDistortion(str, Enum):
    ALL_OR_NOTHING = "all_or_nothing"
    OVERGENERALISATION = "overgeneralisation"
    MENTAL_FILTER = "mental_filter"
    DISCOUNTING_POSITIVES = "discounting_positives"
    MIND_READING = "mind_reading"
    FORTUNE_TELLING = "fortune_telling"
    CATASTROPHISING = "catastrophising"
    MINIMISATION = "minimisation"
    EMOTIONAL_REASONING = "emotional_reasoning"
    SHOULD_STATEMENTS = "should_statements"
    LABELLING = "labelling"
    PERSONALISATION = "personalisation"
    BLAME = "blame"
    MAGNIFICATION = "magnification"


_DISTORTION_DESCRIPTIONS = {
    CognitiveDistortion.ALL_OR_NOTHING: "Seeing things in black-and-white, with no middle ground.",
    CognitiveDistortion.OVERGENERALISATION: "Drawing broad conclusions from single events (always, never).",
    CognitiveDistortion.MENTAL_FILTER: "Dwelling on negatives while filtering out positives.",
    CognitiveDistortion.DISCOUNTING_POSITIVES: "Dismissing positive experiences as not counting.",
    CognitiveDistortion.MIND_READING: "Assuming you know what others are thinking.",
    CognitiveDistortion.FORTUNE_TELLING: "Predicting negative outcomes as facts.",
    CognitiveDistortion.CATASTROPHISING: "Imagining the worst-case scenario will occur.",
    CognitiveDistortion.MINIMISATION: "Shrinking the importance of positive things.",
    CognitiveDistortion.EMOTIONAL_REASONING: "Assuming feelings reflect reality ('I feel it, so it must be true').",
    CognitiveDistortion.SHOULD_STATEMENTS: "Rigid rules about how you/others must behave.",
    CognitiveDistortion.LABELLING: "Attaching global negative labels to self or others.",
    CognitiveDistortion.PERSONALISATION: "Blaming yourself for events outside your control.",
    CognitiveDistortion.BLAME: "Blaming others for your emotional pain.",
    CognitiveDistortion.MAGNIFICATION: "Exaggerating the importance of problems.",
}

_REFRAMES: dict[CognitiveDistortion, str] = {
    CognitiveDistortion.ALL_OR_NOTHING: "Is there a middle ground here? What might a balanced view look like?",
    CognitiveDistortion.OVERGENERALISATION: "Is this always true, or could there be exceptions?",
    CognitiveDistortion.MENTAL_FILTER: "Are there any positive aspects of this situation you might be overlooking?",
    CognitiveDistortion.DISCOUNTING_POSITIVES: "What would it mean to let this positive experience count, even just a little?",
    CognitiveDistortion.MIND_READING: "What evidence do you have for what they're thinking? Could there be another explanation?",
    CognitiveDistortion.FORTUNE_TELLING: "What are some other possible outcomes, besides the worst one?",
    CognitiveDistortion.CATASTROPHISING: "Even if the worst happened, how might you cope with it?",
    CognitiveDistortion.MINIMISATION: "If a friend achieved this, how would you see it?",
    CognitiveDistortion.EMOTIONAL_REASONING: "Feelings are real, but do they always reflect facts? What does the evidence say?",
    CognitiveDistortion.SHOULD_STATEMENTS: "Where did this rule come from? What would happen if you replaced 'should' with 'could'?",
    CognitiveDistortion.LABELLING: "Is one event or quality the whole story of who you are?",
    CognitiveDistortion.PERSONALISATION: "What other factors might have contributed to this situation?",
    CognitiveDistortion.BLAME: "What part, if any, of this situation is within your control to change?",
    CognitiveDistortion.MAGNIFICATION: "How significant will this feel in a week, a month, or a year?",
}

_PATTERNS: dict[CognitiveDistortion, list[str]] = {
    CognitiveDistortion.ALL_OR_NOTHING: [
        r"\b(always|never|completely|totally|absolutely|entire|all or nothing|perfect|failure)\b",
        r"\b(everyone|nobody|no one|nothing|everything)\b",
        r"\b(complete failure|total disaster|absolutely wrong|completely hopeless)\b",
    ],
    CognitiveDistortion.OVERGENERALISATION: [
        r"\b(always|never|every time|all the time|constantly|forever)\b",
        r"\b(everyone|nobody|no one|people always|people never)\b",
        r"\b(this always happens|it never works|i always mess up)\b",
    ],
    CognitiveDistortion.CATASTROPHISING: [
        r"\b(disaster|catastrophe|terrible|horrible|awful|end of the world|ruined|destroyed)\b",
        r"\b(can'?t survive|will never recover|it'?s over|worst.*ever|everything is ruined)\b",
        r"\b(devastating|unbearable|unacceptable|impossible)\b",
    ],
    CognitiveDistortion.MIND_READING: [
        r"\b(they think|he thinks|she thinks|they must think|everyone thinks)\b",
        r"\b(i know (?:they|he|she|people)|must be thinking|probably thinks)\b",
        r"\b(judging me|hate me|think i.?m|looking at me like)\b",
    ],
    CognitiveDistortion.FORTUNE_TELLING: [
        r"\b(will never|will always|i.?ll fail|i.?ll never|it won.?t work|going to fail)\b",
        r"\b(know it.?ll|it.?s going to|definitely going to|bound to fail)\b",
        r"\b(there.?s no point|won.?t get better|nothing will change)\b",
    ],
    CognitiveDistortion.SHOULD_STATEMENTS: [
        r"\b(should|shouldn.?t|must|mustn.?t|ought to|have to|supposed to|need to)\b",
        r"\b(it.?s wrong to|it.?s bad to|i.?m obligated|i.?m required)\b",
    ],
    CognitiveDistortion.LABELLING: [
        r"\bi.?m (?:a |an )?(failure|loser|idiot|stupid|worthless|useless|pathetic|weak)\b",
        r"\b(i am (?:such a|a complete|a total) \w+)\b",
        r"\b(he.?s|she.?s|they.?re) (?:a |an )?(idiot|loser|narcissist|toxic)\b",
    ],
    CognitiveDistortion.PERSONALISATION: [
        r"\b(my fault|i caused|it.?s because of me|i.?m responsible|i made this happen)\b",
        r"\b(blame myself|it.?s all my fault|i should have known)\b",
    ],
    CognitiveDistortion.EMOTIONAL_REASONING: [
        r"\bi feel (?:like )?(?:i.?m|it.?s|this is)\b",
        r"\bbecause i feel.{0,30}(must be|it is|therefore)\b",
        r"\b(i feel so .{0,20} so i must be|feeling \w+ means)\b",
    ],
    CognitiveDistortion.MENTAL_FILTER: [
        r"\b(only seeing|can.?t see anything good|focus on the bad|nothing.?s going right)\b",
        r"\b(despite.{0,30}(still|only|but).{0,30}(bad|wrong|terrible))\b",
    ],
    CognitiveDistortion.DISCOUNTING_POSITIVES: [
        r"\b(doesn.?t count|doesn.?t matter|it.?s not a big deal|anyone could|so what)\b",
        r"\b(yeah but|but still|that.?s nothing|it wasn.?t that hard)\b",
    ],
    CognitiveDistortion.MAGNIFICATION: [
        r"\b(huge|massive|enormous|gigantic|colossal).{0,20}(problem|mistake|issue|deal)\b",
        r"\b(the biggest|the worst|the most).{0,20}(ever|in my life|imaginable)\b",
    ],
    CognitiveDistortion.MINIMISATION: [
        r"\b(just|only|merely|barely).{0,20}(small|little|minor|tiny)\b",
        r"\b(it.?s not that|not really|doesn.?t really|hardly counts)\b",
    ],
    CognitiveDistortion.BLAME: [
        r"\b(their fault|it.?s (?:his|her|their) fault|they caused|they made me)\b",
        r"\b(because of (?:him|her|them)|ruined by|they are to blame)\b",
    ],
}

_COMPILED: dict[CognitiveDistortion, list[re.Pattern]] = {
    d: [re.compile(p, re.IGNORECASE) for p in patterns]
    for d, patterns in _PATTERNS.items()
}


@dataclass
class DetectedDistortion:
    distortion: CognitiveDistortion
    confidence: float
    evidence: str
    reframe_suggestion: str
    description: str = field(init=False)

    def __post_init__(self) -> None:
        self.description = _DISTORTION_DESCRIPTIONS.get(self.distortion, "")


@dataclass
class DistortionAnalysis:
    distortions: list[DetectedDistortion] = field(default_factory=list)
    overall_distortion_level: float = 0.0

    @property
    def has_significant_distortions(self) -> bool:
        return any(d.confidence >= 0.60 for d in self.distortions)

    @property
    def top_distortion(self) -> DetectedDistortion | None:
        if not self.distortions:
            return None
        return max(self.distortions, key=lambda d: d.confidence)


async def detect_cognitive_distortions(text: str) -> DistortionAnalysis:
    found: list[DetectedDistortion] = []

    for distortion, patterns in _COMPILED.items():
        matches = []
        for pat in patterns:
            m = pat.search(text)
            if m:
                matches.append(m.group(0))

        if not matches:
            continue

        base = 0.45 + min(len(matches) * 0.15, 0.45)
        confidence = round(min(base, 0.92), 2)

        found.append(DetectedDistortion(
            distortion=distortion,
            confidence=confidence,
            evidence="; ".join(matches[:2]),
            reframe_suggestion=_REFRAMES[distortion],
        ))

    found.sort(key=lambda d: d.confidence, reverse=True)
    top = found[:4]

    overall = max((d.confidence for d in top), default=0.0) * 0.8 if top else 0.0

    return DistortionAnalysis(
        distortions=top,
        overall_distortion_level=round(overall, 2),
    )

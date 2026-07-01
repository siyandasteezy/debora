"""
Emotion and theme detection — keyword scoring, no external API.
Maps text signals to Plutchik-extended emotion categories.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from src.utils.logger import get_logger

logger = get_logger(__name__)


class EmotionCategory(str, Enum):
    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    DISGUST = "disgust"
    SURPRISE = "surprise"
    TRUST = "trust"
    ANTICIPATION = "anticipation"
    SHAME = "shame"
    GUILT = "guilt"
    LONELINESS = "loneliness"
    ANXIETY = "anxiety"
    OVERWHELM = "overwhelm"
    HOPELESSNESS = "hopelessness"
    GRIEF = "grief"
    NUMBNESS = "numbness"
    FRUSTRATION = "frustration"
    CONFUSION = "confusion"
    RELIEF = "relief"
    GRATITUDE = "gratitude"
    PRIDE = "pride"
    LOVE = "love"
    NEUTRAL = "neutral"


@dataclass
class DetectedEmotion:
    category: EmotionCategory
    intensity: float
    confidence: float
    valence: float
    explicit: bool
    evidence: str


@dataclass
class EmotionThemeAnalysis:
    primary_emotions: list[DetectedEmotion] = field(default_factory=list)
    secondary_emotions: list[DetectedEmotion] = field(default_factory=list)
    themes: list[str] = field(default_factory=list)
    stressors: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    goals_mentioned: list[str] = field(default_factory=list)
    overall_valence: float = 0.0
    distress_level: float = 0.0

    @property
    def top_emotion(self) -> DetectedEmotion | None:
        return self.primary_emotions[0] if self.primary_emotions else None


# ── Keyword banks ────────────────────────────────────────────────────────────

_EMOTION_KEYWORDS: dict[EmotionCategory, list[str]] = {
    EmotionCategory.JOY: [
        "happy", "happiness", "joy", "joyful", "excited", "great", "wonderful",
        "fantastic", "amazing", "thrilled", "elated", "glad", "delighted", "pleased",
        "content", "cheerful", "ecstatic", "overjoyed", "blissful",
    ],
    EmotionCategory.SADNESS: [
        "sad", "sadness", "unhappy", "depressed", "down", "miserable", "crying",
        "tears", "cry", "heartbroken", "hurt", "pain", "sorrow", "sorrowful",
        "gloomy", "blue", "low", "upset", "devastated", "crushed",
    ],
    EmotionCategory.ANGER: [
        "angry", "anger", "furious", "rage", "mad", "irritated", "frustrated",
        "annoyed", "resentful", "hostile", "outraged", "infuriated", "livid",
        "bitter", "hate", "hatred", "despise",
    ],
    EmotionCategory.FEAR: [
        "afraid", "fear", "scared", "terrified", "frightened", "anxious", "nervous",
        "panic", "dread", "horror", "phobia", "worried", "apprehensive",
    ],
    EmotionCategory.ANXIETY: [
        "anxiety", "anxious", "worry", "worrying", "stressed", "stress", "tense",
        "tension", "uneasy", "restless", "on edge", "overthinking", "racing thoughts",
        "what if", "catastrophe", "panic attack",
    ],
    EmotionCategory.HOPELESSNESS: [
        "hopeless", "hopelessness", "no hope", "pointless", "meaningless", "no point",
        "can't see a way", "never get better", "nothing will change", "never change",
        "will never change", "giving up", "futile", "useless", "worthless", "no future",
        "always fail", "never succeed", "always mess up", "never work",
    ],
    EmotionCategory.SHAME: [
        "ashamed", "shame", "embarrassed", "embarrassment", "humiliated", "humiliation",
        "disgrace", "disgusted with myself", "pathetic", "weak", "loser",
        "failure", "such a failure", "complete failure", "total failure",
        "hate myself", "hate who i am",
    ],
    EmotionCategory.GUILT: [
        "guilty", "guilt", "blame myself", "my fault", "i caused", "i let down",
        "should have", "could have", "regret", "remorse", "sorry for",
    ],
    EmotionCategory.LONELINESS: [
        "lonely", "loneliness", "alone", "isolated", "no one", "nobody", "no friends",
        "no support", "disconnected", "cut off", "abandoned", "left out",
    ],
    EmotionCategory.OVERWHELM: [
        "overwhelmed", "overwhelm", "too much", "can't cope", "can't handle",
        "falling apart", "breaking down", "drowning", "swamped", "buried",
        "exhausted", "burnt out", "burnout", "drained",
    ],
    EmotionCategory.GRIEF: [
        "grief", "grieving", "loss", "lost", "bereavement", "mourning", "miss",
        "missing", "passed away", "died", "death", "gone",
    ],
    EmotionCategory.FRUSTRATION: [
        "frustrated", "frustration", "stuck", "going nowhere", "not working",
        "keeps happening", "fed up", "sick of", "tired of", "enough",
    ],
    EmotionCategory.CONFUSION: [
        "confused", "confusion", "don't understand", "lost", "unclear",
        "don't know what to do", "no idea", "mixed up", "uncertain",
    ],
    EmotionCategory.NUMBNESS: [
        "numb", "numbness", "empty", "nothing", "feel nothing", "can't feel",
        "disconnected", "detached", "hollow", "flat",
    ],
    EmotionCategory.RELIEF: [
        "relief", "relieved", "finally", "thankfully", "glad it's over",
        "weight lifted", "better now",
    ],
    EmotionCategory.GRATITUDE: [
        "grateful", "gratitude", "thankful", "appreciate", "appreciation",
        "blessed", "lucky",
    ],
    EmotionCategory.PRIDE: [
        "proud", "pride", "accomplished", "achievement", "did it", "managed",
        "succeeded", "proud of myself",
    ],
    EmotionCategory.LOVE: [
        "love", "loving", "care", "caring", "affection", "adore", "cherish",
        "close to", "connection",
    ],
}

_EMOTION_VALENCE: dict[EmotionCategory, float] = {
    EmotionCategory.JOY: 0.9,
    EmotionCategory.SADNESS: -0.7,
    EmotionCategory.ANGER: -0.6,
    EmotionCategory.FEAR: -0.7,
    EmotionCategory.ANXIETY: -0.6,
    EmotionCategory.HOPELESSNESS: -0.9,
    EmotionCategory.SHAME: -0.7,
    EmotionCategory.GUILT: -0.6,
    EmotionCategory.LONELINESS: -0.7,
    EmotionCategory.OVERWHELM: -0.65,
    EmotionCategory.GRIEF: -0.8,
    EmotionCategory.FRUSTRATION: -0.5,
    EmotionCategory.CONFUSION: -0.3,
    EmotionCategory.NUMBNESS: -0.5,
    EmotionCategory.RELIEF: 0.6,
    EmotionCategory.GRATITUDE: 0.8,
    EmotionCategory.PRIDE: 0.7,
    EmotionCategory.LOVE: 0.85,
    EmotionCategory.DISGUST: -0.6,
    EmotionCategory.SURPRISE: 0.0,
    EmotionCategory.TRUST: 0.5,
    EmotionCategory.ANTICIPATION: 0.2,
    EmotionCategory.NEUTRAL: 0.0,
}

# Emotions that contribute to distress scoring
_DISTRESS_EMOTIONS = {
    EmotionCategory.SADNESS, EmotionCategory.ANXIETY, EmotionCategory.HOPELESSNESS,
    EmotionCategory.SHAME, EmotionCategory.GUILT, EmotionCategory.OVERWHELM,
    EmotionCategory.GRIEF, EmotionCategory.FEAR, EmotionCategory.NUMBNESS,
    EmotionCategory.LONELINESS,
}

# Theme detection keyword groups
_THEME_PATTERNS: dict[str, list[str]] = {
    "relationship conflict": ["relationship", "partner", "boyfriend", "girlfriend", "husband", "wife",
                              "argument", "fight", "broke up", "divorce", "cheating"],
    "work stress": ["work", "job", "boss", "colleague", "deadline", "fired", "unemployed",
                    "career", "workplace", "office", "manager"],
    "family issues": ["family", "parent", "mother", "father", "sibling", "brother", "sister",
                      "children", "kids", "son", "daughter"],
    "grief": ["died", "death", "passed away", "loss", "funeral", "missing", "grief", "mourning"],
    "self-esteem": ["worthless", "useless", "failure", "not good enough", "hate myself",
                    "self-esteem", "confidence", "insecure"],
    "anxiety": ["anxiety", "worried", "panic", "stress", "overthinking", "nervous", "dread"],
    "depression": ["depressed", "depression", "hopeless", "can't get up", "no motivation",
                   "empty", "numb", "pointless"],
    "change": ["change", "different", "new", "trying to", "working on", "want to"],
    "motivation": ["motivation", "motivated", "lazy", "procrastination", "can't start",
                   "want to but", "stuck"],
    "health": ["sick", "illness", "pain", "doctor", "hospital", "diagnosis", "chronic"],
    "existential": ["meaning", "purpose", "what's the point", "why am I", "life meaning"],
    "social isolation": ["alone", "lonely", "no friends", "isolated", "nobody cares"],
    "avoidance": ["avoiding", "avoid", "can't face", "hiding", "running away from"],
    "rumination": ["keep thinking", "can't stop thinking", "overthinking", "replaying"],
}

_STRENGTH_PATTERNS = [
    "trying", "working on", "managed to", "reached out", "asking for help",
    "still here", "keeping going", "despite", "resilient", "strong", "getting through",
]

_GOAL_PATTERNS = [
    r"want to ([\w\s]+)",
    r"wish I could ([\w\s]+)",
    r"hope to ([\w\s]+)",
    r"trying to ([\w\s]+)",
    r"working on ([\w\s]+)",
    r"goal is to ([\w\s]+)",
    r"would like to ([\w\s]+)",
]

_STRESSOR_PATTERNS = [
    r"because of ([\w\s]+)",
    r"due to ([\w\s]+)",
    r"struggling with ([\w\s]+)",
    r"dealing with ([\w\s]+)",
    r"caused by ([\w\s]+)",
]


def _score_emotions(text: str) -> list[tuple[EmotionCategory, float, list[str]]]:
    text_lower = text.lower()
    words = re.findall(r"\b\w+\b", text_lower)
    word_set = set(words)
    results = []

    for category, keywords in _EMOTION_KEYWORDS.items():
        matched = [kw for kw in keywords if kw in text_lower]
        if not matched:
            continue
        # Score: base hit ratio with diminishing returns for more matches
        raw = min(1.0, 0.4 + (len(matched) / max(len(keywords), 1)) * 0.8)
        explicit = any(kw in word_set for kw in keywords[:5])  # first 5 are direct labels
        results.append((category, raw, matched))

    results.sort(key=lambda x: x[1], reverse=True)
    return results


def _detect_themes(text: str) -> list[str]:
    text_lower = text.lower()
    found = []
    for theme, keywords in _THEME_PATTERNS.items():
        if any(kw in text_lower for kw in keywords):
            found.append(theme)
    return found[:5]


def _detect_stressors(text: str) -> list[str]:
    stressors = []
    for pat in _STRESSOR_PATTERNS:
        for m in re.finditer(pat, text, re.IGNORECASE):
            stressor = m.group(1).strip()[:50]
            if stressor:
                stressors.append(stressor)
    return stressors[:3]


def _detect_goals(text: str) -> list[str]:
    goals = []
    for pat in _GOAL_PATTERNS:
        for m in re.finditer(pat, text, re.IGNORECASE):
            goal = m.group(1).strip()[:50]
            if goal:
                goals.append(goal)
    return goals[:3]


def _detect_strengths(text: str) -> list[str]:
    text_lower = text.lower()
    return [s for s in _STRENGTH_PATTERNS if s in text_lower][:3]


async def analyse_emotions_and_themes(
    text: str,
    conversation_history: str = "",
) -> EmotionThemeAnalysis:
    scored = _score_emotions(text)

    if not scored:
        neutral = DetectedEmotion(
            category=EmotionCategory.NEUTRAL,
            intensity=0.5,
            confidence=0.6,
            valence=0.0,
            explicit=False,
            evidence="No strong emotional language detected",
        )
        return EmotionThemeAnalysis(
            primary_emotions=[neutral],
            overall_valence=0.0,
            distress_level=0.1,
        )

    primary_raw = scored[:2]
    secondary_raw = scored[2:5]

    def make_emotion(cat: EmotionCategory, score: float, matched: list[str]) -> DetectedEmotion:
        return DetectedEmotion(
            category=cat,
            intensity=round(min(score, 1.0), 2),
            confidence=round(min(score * 0.9, 0.95), 2),
            valence=_EMOTION_VALENCE.get(cat, 0.0),
            explicit=len(matched) > 0,
            evidence=f"Keywords: {', '.join(matched[:3])}",
        )

    primary = [make_emotion(c, s, m) for c, s, m in primary_raw]
    secondary = [make_emotion(c, s, m) for c, s, m in secondary_raw]

    # Overall valence: weighted average of top emotions
    all_scored = primary_raw + secondary_raw
    if all_scored:
        total_weight = sum(s for _, s, _ in all_scored)
        overall_valence = sum(
            _EMOTION_VALENCE.get(c, 0.0) * s for c, s, _ in all_scored
        ) / max(total_weight, 0.01)
    else:
        overall_valence = 0.0

    # Distress: intensity of distressing emotions
    distress_scores = [s for c, s, _ in all_scored if c in _DISTRESS_EMOTIONS]
    distress_level = round(min(max(distress_scores, default=0.0) * 1.1, 1.0), 2)

    return EmotionThemeAnalysis(
        primary_emotions=primary,
        secondary_emotions=secondary,
        themes=_detect_themes(text),
        stressors=_detect_stressors(text),
        strengths=_detect_strengths(text),
        goals_mentioned=_detect_goals(text),
        overall_valence=round(overall_valence, 2),
        distress_level=distress_level,
    )

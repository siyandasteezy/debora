"""
Evidence-based coping strategy library.
Each strategy maps to frameworks, themes, and distress levels.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CopingStrategy:
    id: str
    name: str
    description: str
    instructions: str
    framework: str
    evidence_summary: str
    suitable_for: frozenset[str]  # themes/emotions
    min_distress: float
    max_distress: float
    duration_minutes: int
    evidence_level: str  # "high" | "moderate" | "emerging"


STRATEGIES: list[CopingStrategy] = [
    CopingStrategy(
        id="box_breathing",
        name="Box Breathing (4-4-4-4)",
        description="A structured breathing technique that activates the parasympathetic nervous system.",
        instructions=(
            "1. Inhale slowly for 4 counts.\n"
            "2. Hold your breath for 4 counts.\n"
            "3. Exhale slowly for 4 counts.\n"
            "4. Hold for 4 counts.\n"
            "Repeat 4–6 times."
        ),
        framework="DBT/mindfulness",
        evidence_summary=(
            "Diaphragmatic breathing reduces cortisol and activates the vagus nerve. "
            "Supported by RCTs for acute anxiety (Ma et al., 2017, Frontiers in Psychology)."
        ),
        suitable_for=frozenset({"anxiety", "overwhelm", "panic", "stress", "anger"}),
        min_distress=0.3,
        max_distress=1.0,
        duration_minutes=5,
        evidence_level="high",
    ),
    CopingStrategy(
        id="5_4_3_2_1_grounding",
        name="5-4-3-2-1 Sensory Grounding",
        description="Grounds you in the present moment by engaging all five senses.",
        instructions=(
            "Name out loud or in your mind:\n"
            "- 5 things you can SEE\n"
            "- 4 things you can TOUCH\n"
            "- 3 things you can HEAR\n"
            "- 2 things you can SMELL\n"
            "- 1 thing you can TASTE"
        ),
        framework="DBT/ACT",
        evidence_summary=(
            "Grounding techniques interrupt hyperarousal and dissociation. "
            "Recommended in NICE guidelines for trauma and PTSD (NICE CG26)."
        ),
        suitable_for=frozenset({"anxiety", "panic", "trauma", "dissociation", "overwhelm"}),
        min_distress=0.5,
        max_distress=1.0,
        duration_minutes=3,
        evidence_level="high",
    ),
    CopingStrategy(
        id="thought_record",
        name="CBT Thought Record",
        description="Examine the evidence for and against a distressing automatic thought.",
        instructions=(
            "Write down:\n"
            "1. The situation that triggered the feeling\n"
            "2. The automatic thought (what your mind said)\n"
            "3. Emotions and their intensity (0–100%)\n"
            "4. Evidence FOR the thought\n"
            "5. Evidence AGAINST the thought\n"
            "6. A more balanced alternative thought\n"
            "7. How you feel now (0–100%)"
        ),
        framework="CBT",
        evidence_summary=(
            "Thought records are a core CBT technique with Level 1a evidence for depression "
            "and anxiety (Beck et al. meta-analysis; NICE depression guidelines CG90)."
        ),
        suitable_for=frozenset({"depression", "anxiety", "sadness", "hopelessness", "guilt", "shame"}),
        min_distress=0.2,
        max_distress=0.8,
        duration_minutes=15,
        evidence_level="high",
    ),
    CopingStrategy(
        id="progressive_muscle_relaxation",
        name="Progressive Muscle Relaxation",
        description="Systematically tense and release muscle groups to release physical tension.",
        instructions=(
            "Starting from your feet, tense each muscle group for 5 seconds, "
            "then release for 30 seconds. Move up: calves → thighs → abdomen → "
            "hands → arms → shoulders → face."
        ),
        framework="Behavioural/mindfulness",
        evidence_summary=(
            "PMR has RCT-level evidence for anxiety, insomnia, and somatic tension "
            "(Jacobson, 1938; Cochrane review on relaxation for anxiety)."
        ),
        suitable_for=frozenset({"anxiety", "stress", "insomnia", "tension", "anger"}),
        min_distress=0.2,
        max_distress=0.9,
        duration_minutes=15,
        evidence_level="high",
    ),
    CopingStrategy(
        id="behavioural_activation",
        name="Behavioural Activation",
        description="Schedule small, pleasurable activities to counteract depression-driven withdrawal.",
        instructions=(
            "1. List 5 activities you used to enjoy.\n"
            "2. Choose the smallest, most achievable one.\n"
            "3. Schedule it for a specific time today or tomorrow.\n"
            "4. After doing it, rate your mood before and after (0–10)."
        ),
        framework="CBT",
        evidence_summary=(
            "Behavioural Activation is as effective as full CBT for depression "
            "(Cuijpers et al., 2007; Level 1a evidence; NICE CG90 recommended)."
        ),
        suitable_for=frozenset({"depression", "sadness", "loneliness", "hopelessness", "numbness"}),
        min_distress=0.2,
        max_distress=0.75,
        duration_minutes=20,
        evidence_level="high",
    ),
    CopingStrategy(
        id="values_clarification",
        name="ACT Values Clarification",
        description="Reconnect with what matters most to guide meaningful action.",
        instructions=(
            "Ask yourself:\n"
            "- What kind of person do I want to be?\n"
            "- What would I want people to say about me at 80?\n"
            "- In the area of [relationships / work / health], what truly matters to me?\n"
            "Write 3 core values and one small action aligned with each."
        ),
        framework="ACT",
        evidence_summary=(
            "Values clarification improves psychological flexibility and reduces avoidance. "
            "Hayes et al. (2006) meta-analysis: ACT shows moderate-to-large effects."
        ),
        suitable_for=frozenset({"existential", "meaning", "rumination", "avoidance", "ambivalence"}),
        min_distress=0.1,
        max_distress=0.7,
        duration_minutes=20,
        evidence_level="high",
    ),
    CopingStrategy(
        id="tipp_skill",
        name="DBT TIPP Skill",
        description="Temperature, Intense exercise, Paced breathing, Progressive relaxation — for crisis tolerance.",
        instructions=(
            "Choose one:\n"
            "T – Hold ice cubes or splash cold water on your face (activates dive reflex)\n"
            "I – Do 30 seconds of intense exercise (jumping jacks, running in place)\n"
            "P – Slow your breathing (breathe out longer than in: 5 in, 7 out)\n"
            "P – Progressive muscle relaxation (see separate exercise)"
        ),
        framework="DBT",
        evidence_summary=(
            "TIPP skills are DBT distress tolerance techniques. DBT has Level 1a evidence "
            "for suicidal behaviour and emotional dysregulation (Linehan et al., 2015)."
        ),
        suitable_for=frozenset({"overwhelm", "anger", "panic", "self_harm_urge", "crisis", "anxiety"}),
        min_distress=0.6,
        max_distress=1.0,
        duration_minutes=5,
        evidence_level="high",
    ),
    CopingStrategy(
        id="self_compassion_break",
        name="Self-Compassion Break",
        description="Kristin Neff's 3-step self-compassion practice.",
        instructions=(
            "Place one hand on your heart. Then say to yourself:\n"
            "1. 'This is a moment of suffering.' (Mindfulness — acknowledge without over-identifying)\n"
            "2. 'Suffering is part of life.' (Common humanity — you are not alone)\n"
            "3. 'May I be kind to myself in this moment.' (Self-kindness)\n"
            "Stay with the feeling for 30 seconds."
        ),
        framework="Positive Psychology / Mindfulness",
        evidence_summary=(
            "Self-compassion interventions show moderate effect sizes on anxiety and depression "
            "(Neff & Germer, 2013; MacBeth & Gumley, 2012 meta-analysis)."
        ),
        suitable_for=frozenset({"shame", "guilt", "self_criticism", "sadness", "grief", "failure"}),
        min_distress=0.2,
        max_distress=0.9,
        duration_minutes=5,
        evidence_level="moderate",
    ),
]


def get_strategies_for(
    themes: list[str],
    distress_level: float,
    max_count: int = 3,
) -> list[CopingStrategy]:
    """Filter and rank strategies by theme relevance and distress appropriateness."""
    theme_set = {t.lower().replace(" ", "_") for t in themes}
    scored: list[tuple[int, CopingStrategy]] = []

    for strategy in STRATEGIES:
        if not (strategy.min_distress <= distress_level <= strategy.max_distress):
            continue
        overlap = len(theme_set.intersection(strategy.suitable_for))
        if overlap > 0:
            scored.append((overlap, strategy))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in scored[:max_count]]

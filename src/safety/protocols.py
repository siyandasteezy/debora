"""
Safe messaging guidelines for crisis response.
Based on: Suicide Prevention Resource Center, AFSP, and WHO safe messaging guidelines.
"""
from __future__ import annotations

from src.safety.crisis_detector import CrisisAssessment, CrisisType, Severity
from src.safety.resources import format_resources_for_response, get_resources


_SUICIDAL_CRITICAL = """\
I hear you, and I'm deeply concerned about what you've shared. What you're going through \
sounds incredibly painful, and I want to make sure you get real support right now.

Please reach out to a crisis service immediately — they're trained to help with exactly \
what you're experiencing, and they won't judge you.

{resources}

If you're in immediate danger, please call emergency services (911, 999, 112, or your \
local emergency number) or go to your nearest emergency room.

I'm here with you. Can you tell me if you're safe right now?"""

_SUICIDAL_MODERATE = """\
Thank you for trusting me with something so difficult. What you're describing — \
{theme} — is a real crisis that deserves real human support.

I'm not a crisis counsellor, but trained people who truly understand are available \
right now:

{resources}

I'll stay here with you. Are you willing to reach out to one of these services?"""

_SELF_HARM_RESPONSE = """\
I'm really glad you shared this with me, even though I know it wasn't easy. \
Self-harm is often a way of coping with overwhelming pain — and there are people \
who understand that and can help in ways I'm not able to.

Please consider reaching out to someone trained in this:

{resources}

You don't have to face this alone. What's been going on that's brought you to this point?"""

_ABUSE_RESPONSE = """\
What you're describing is serious, and your safety matters most right now. \
You've shown real courage in saying something.

If you're in immediate danger, please call emergency services. \
If it's safe to make a call, these confidential services can help:

{resources}

You don't have to give your name. Are you somewhere safe right now?"""

_PSYCHOSIS_RESPONSE = """\
What you're experiencing sounds very frightening and disorienting. \
These kinds of experiences can have medical causes that are treatable, \
and getting support from a doctor or crisis team as soon as possible is important.

{resources}

Is there someone with you, or someone you trust who can be with you right now?"""

_MANIA_RESPONSE = """\
The way you're describing your thoughts and energy sounds like something \
worth talking to a doctor about urgently — sometimes our brain chemistry \
needs medical support, and what you're describing can be a sign of that.

{resources}

Is there someone who can accompany you to speak with a healthcare professional today?"""

_GENERAL_CRISIS = """\
It sounds like you're going through a really difficult time, and I want to make sure \
you have the right support.

{resources}

I'm here, and I'd like to understand more about what you're experiencing. \
What would feel most helpful right now?"""


def _theme_description(crisis_type: CrisisType) -> str:
    return {
        CrisisType.SUICIDAL_IDEATION: "thoughts of ending your life",
        CrisisType.SELF_HARM: "hurting yourself",
        CrisisType.ABUSE: "what's happening at home",
        CrisisType.PSYCHOSIS: "these experiences",
        CrisisType.MANIA: "what you're going through",
        CrisisType.GENERAL_CRISIS: "this crisis",
    }.get(crisis_type, "what you're going through")


def build_crisis_response(
    assessment: CrisisAssessment,
    country_code: str = "US",
) -> str:
    """Construct a safe, non-judgmental, resource-containing crisis response."""
    if not assessment.primary_signal:
        return _GENERAL_CRISIS.format(
            resources=format_resources_for_response(
                get_resources(CrisisType.GENERAL_CRISIS, country_code)
            )
        )

    signal = assessment.primary_signal
    ct = signal.crisis_type
    resources = format_resources_for_response(get_resources(ct, country_code))

    if ct == CrisisType.SUICIDAL_IDEATION:
        if signal.severity in (Severity.HIGH, Severity.CRITICAL):
            return _SUICIDAL_CRITICAL.format(resources=resources)
        return _SUICIDAL_MODERATE.format(
            theme=_theme_description(ct),
            resources=resources,
        )

    templates = {
        CrisisType.SELF_HARM: _SELF_HARM_RESPONSE,
        CrisisType.ABUSE: _ABUSE_RESPONSE,
        CrisisType.PSYCHOSIS: _PSYCHOSIS_RESPONSE,
        CrisisType.MANIA: _MANIA_RESPONSE,
        CrisisType.GENERAL_CRISIS: _GENERAL_CRISIS,
    }
    template = templates.get(ct, _GENERAL_CRISIS)
    return template.format(resources=resources)


SYSTEM_BOUNDARY_STATEMENT = """\
I want to be clear about what I am and what I'm not: I'm an AI that provides \
evidence-informed emotional support and psychoeducation. I am not a therapist, \
counsellor, or crisis worker, and I cannot replace professional mental health care. \
Everything I share is meant to complement — never replace — real human support."""

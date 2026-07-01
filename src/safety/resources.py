"""Evidence-based crisis resources, localised by country code."""
from __future__ import annotations

from dataclasses import dataclass

from src.safety.crisis_detector import CrisisType


@dataclass(frozen=True)
class CrisisResource:
    name: str
    phone: str | None
    text: str | None
    chat_url: str | None
    description: str
    country_codes: frozenset[str]
    crisis_types: frozenset[CrisisType]
    available_24_7: bool = True


_RESOURCES: list[CrisisResource] = [
    # ── International ──
    CrisisResource(
        name="Crisis Text Line",
        phone=None,
        text="HOME to 741741",
        chat_url="https://www.crisistextline.org/",
        description="Free, 24/7 crisis counselling via text message.",
        country_codes=frozenset({"US", "CA", "GB", "IE"}),
        crisis_types=frozenset({
            CrisisType.SUICIDAL_IDEATION,
            CrisisType.SELF_HARM,
            CrisisType.GENERAL_CRISIS,
            CrisisType.ABUSE,
        }),
    ),
    CrisisResource(
        name="International Association for Suicide Prevention",
        phone=None,
        text=None,
        chat_url="https://www.iasp.info/resources/Crisis_Centres/",
        description="Global directory of crisis centres.",
        country_codes=frozenset({"*"}),
        crisis_types=frozenset({CrisisType.SUICIDAL_IDEATION}),
    ),
    # ── United States ──
    CrisisResource(
        name="988 Suicide & Crisis Lifeline",
        phone="988",
        text="988",
        chat_url="https://988lifeline.org/chat/",
        description="National US suicide and mental health crisis line. Free, confidential, 24/7.",
        country_codes=frozenset({"US"}),
        crisis_types=frozenset({
            CrisisType.SUICIDAL_IDEATION,
            CrisisType.SELF_HARM,
            CrisisType.GENERAL_CRISIS,
        }),
    ),
    CrisisResource(
        name="SAMHSA National Helpline",
        phone="1-800-662-4357",
        text=None,
        chat_url="https://www.samhsa.gov/find-help/national-helpline",
        description="Free, confidential, 24/7 treatment referral for mental health and substance use.",
        country_codes=frozenset({"US"}),
        crisis_types=frozenset({CrisisType.GENERAL_CRISIS, CrisisType.MANIA}),
    ),
    CrisisResource(
        name="National Domestic Violence Hotline",
        phone="1-800-799-7233",
        text="START to 88788",
        chat_url="https://www.thehotline.org/",
        description="Confidential support for domestic violence survivors.",
        country_codes=frozenset({"US"}),
        crisis_types=frozenset({CrisisType.ABUSE}),
    ),
    # ── United Kingdom ──
    CrisisResource(
        name="Samaritans",
        phone="116 123",
        text=None,
        chat_url="https://www.samaritans.org/",
        description="Free, confidential emotional support, 24/7. Available any time.",
        country_codes=frozenset({"GB", "IE"}),
        crisis_types=frozenset({
            CrisisType.SUICIDAL_IDEATION,
            CrisisType.SELF_HARM,
            CrisisType.GENERAL_CRISIS,
        }),
    ),
    CrisisResource(
        name="NHS 111 Mental Health Crisis",
        phone="111",
        text=None,
        chat_url="https://111.nhs.uk/",
        description="NHS urgent mental health support. Press option 2 for mental health.",
        country_codes=frozenset({"GB"}),
        crisis_types=frozenset({
            CrisisType.PSYCHOSIS,
            CrisisType.MANIA,
            CrisisType.GENERAL_CRISIS,
        }),
    ),
    # ── South Africa ──
    CrisisResource(
        name="SADAG Suicide Crisis Line",
        phone="0800 567 567",
        text=None,
        chat_url="https://www.sadag.org/index.php?option=com_content&view=article&id=2547",
        description="South African Depression and Anxiety Group. Free 24/7 crisis line.",
        country_codes=frozenset({"ZA"}),
        crisis_types=frozenset({
            CrisisType.SUICIDAL_IDEATION,
            CrisisType.SELF_HARM,
            CrisisType.GENERAL_CRISIS,
        }),
    ),
    CrisisResource(
        name="Lifeline South Africa",
        phone="0861 322 322",
        text=None,
        chat_url="https://lifelinesa.co.za/",
        description="Trauma counselling, abuse support, and crisis intervention.",
        country_codes=frozenset({"ZA"}),
        crisis_types=frozenset({
            CrisisType.ABUSE,
            CrisisType.GENERAL_CRISIS,
            CrisisType.SUICIDAL_IDEATION,
        }),
    ),
    # ── Australia ──
    CrisisResource(
        name="Lifeline Australia",
        phone="13 11 14",
        text="0477 13 11 14",
        chat_url="https://www.lifeline.org.au/",
        description="24/7 crisis support and suicide prevention.",
        country_codes=frozenset({"AU"}),
        crisis_types=frozenset({
            CrisisType.SUICIDAL_IDEATION,
            CrisisType.SELF_HARM,
            CrisisType.GENERAL_CRISIS,
        }),
    ),
    # ── Canada ──
    CrisisResource(
        name="Talk Suicide Canada",
        phone="1-833-456-4566",
        text="45645",
        chat_url="https://talksuicide.ca/",
        description="Bilingual crisis support. Available 24/7.",
        country_codes=frozenset({"CA"}),
        crisis_types=frozenset({CrisisType.SUICIDAL_IDEATION, CrisisType.SELF_HARM}),
    ),
]


def get_resources(
    crisis_type: CrisisType,
    country_code: str = "US",
) -> list[CrisisResource]:
    """Return relevant crisis resources, prioritising local then international."""
    cc = country_code.upper()
    local = [
        r for r in _RESOURCES
        if crisis_type in r.crisis_types and cc in r.country_codes
    ]
    international = [
        r for r in _RESOURCES
        if crisis_type in r.crisis_types
        and "*" in r.country_codes
        and r not in local
    ]
    return (local + international)[:4]


def format_resources_for_response(resources: list[CrisisResource]) -> str:
    lines = ["**Crisis Support Resources:**"]
    for res in resources:
        contact_parts = []
        if res.phone:
            contact_parts.append(f"Call: **{res.phone}**")
        if res.text:
            contact_parts.append(f"Text: **{res.text}**")
        if res.chat_url:
            contact_parts.append(f"Chat: {res.chat_url}")
        contact = " | ".join(contact_parts)
        lines.append(f"\n- **{res.name}** — {res.description}\n  {contact}")
    return "\n".join(lines)

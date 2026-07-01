"""Anthropic Claude wrapper with retry, token tracking, and structured output."""
from __future__ import annotations

import json
from typing import Any

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

_client: anthropic.AsyncAnthropic | None = None


def get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
async def chat_completion(
    messages: list[dict[str, str]],
    system: str,
    max_tokens: int | None = None,
    temperature: float = 0.7,
    model: str | None = None,
) -> tuple[str, int, int]:
    """Return (content, input_tokens, output_tokens)."""
    client = get_client()
    response = await client.messages.create(
        model=model or settings.anthropic_model,
        max_tokens=max_tokens or settings.anthropic_max_tokens,
        temperature=temperature,
        system=system,
        messages=messages,
    )
    content = response.content[0].text
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    logger.debug(
        "llm_completion",
        model=response.model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
    return content, input_tokens, output_tokens


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
async def structured_completion(
    messages: list[dict[str, str]],
    system: str,
    output_schema: dict[str, Any],
    temperature: float = 0.2,
    model: str | None = None,
) -> dict[str, Any]:
    """Force JSON output conforming to output_schema using tool use."""
    client = get_client()
    tools = [
        {
            "name": "structured_output",
            "description": "Output the result as structured JSON conforming to the schema.",
            "input_schema": output_schema,
        }
    ]
    response = await client.messages.create(
        model=model or settings.anthropic_model,
        max_tokens=2048,
        temperature=temperature,
        system=system,
        messages=messages,
        tools=tools,
        tool_choice={"type": "any"},
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == "structured_output":
            return block.input  # type: ignore[return-value]
    raise ValueError("No structured output returned from LLM")

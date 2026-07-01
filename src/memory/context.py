"""
Conversation context window management.
Maintains a rolling window of messages that fits within the LLM context,
and builds a condensed history string for reasoning modules.
"""
from __future__ import annotations

from dataclasses import dataclass, field

_MAX_CONTEXT_CHARS = 8000
_MAX_MESSAGES = 20


@dataclass
class ContextMessage:
    role: str  # "user" | "assistant"
    content: str
    message_id: str | None = None


@dataclass
class ConversationContext:
    messages: list[ContextMessage] = field(default_factory=list)
    session_summary: str = ""
    user_goals: list[str] = field(default_factory=list)
    recurring_themes: list[str] = field(default_factory=list)
    identified_strengths: list[str] = field(default_factory=list)
    stressors: list[str] = field(default_factory=list)

    def add_message(self, role: str, content: str, message_id: str | None = None) -> None:
        self.messages.append(ContextMessage(role=role, content=content, message_id=message_id))
        # Trim to keep context manageable
        if len(self.messages) > _MAX_MESSAGES:
            self.messages = self.messages[-_MAX_MESSAGES:]

    def to_llm_messages(self) -> list[dict[str, str]]:
        """Format for Anthropic messages API."""
        return [{"role": m.role, "content": m.content} for m in self.messages]

    def to_history_string(self, max_chars: int = _MAX_CONTEXT_CHARS) -> str:
        """Condensed string for reasoning module context."""
        lines = []
        if self.session_summary:
            lines.append(f"[Session summary: {self.session_summary}]")
        if self.user_goals:
            lines.append(f"[Goals: {'; '.join(self.user_goals)}]")
        if self.recurring_themes:
            lines.append(f"[Themes: {'; '.join(self.recurring_themes)}]")

        for msg in self.messages[-10:]:
            prefix = "User" if msg.role == "user" else "Assistant"
            lines.append(f"{prefix}: {msg.content[:300]}")

        result = "\n".join(lines)
        return result[-max_chars:]

    @property
    def message_count(self) -> int:
        return len(self.messages)

    @property
    def last_user_message(self) -> str | None:
        for msg in reversed(self.messages):
            if msg.role == "user":
                return msg.content
        return None

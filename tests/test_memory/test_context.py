"""Tests for conversation context management."""
from __future__ import annotations

import pytest

from src.memory.context import ConversationContext


class TestConversationContext:
    def test_add_messages(self):
        ctx = ConversationContext()
        ctx.add_message("user", "Hello, I'm struggling today")
        ctx.add_message("assistant", "I hear you. Tell me more.")
        assert ctx.message_count == 2
        assert ctx.last_user_message == "Hello, I'm struggling today"

    def test_trim_to_max_messages(self):
        ctx = ConversationContext()
        for i in range(25):
            ctx.add_message("user", f"Message {i}")
        # Should be trimmed to _MAX_MESSAGES (20)
        assert ctx.message_count == 20

    def test_to_llm_messages_format(self):
        ctx = ConversationContext()
        ctx.add_message("user", "Hello")
        ctx.add_message("assistant", "Hi there")
        messages = ctx.to_llm_messages()
        assert len(messages) == 2
        assert messages[0] == {"role": "user", "content": "Hello"}
        assert messages[1] == {"role": "assistant", "content": "Hi there"}

    def test_to_history_string_includes_metadata(self):
        ctx = ConversationContext(
            user_goals=["feel less anxious"],
            recurring_themes=["work stress"],
        )
        ctx.add_message("user", "I'm stressed about work")
        history = ctx.to_history_string()
        assert "work stress" in history or "feel less anxious" in history

    def test_to_history_string_respects_max_chars(self):
        ctx = ConversationContext()
        for i in range(20):
            ctx.add_message("user", "x" * 500)
        history = ctx.to_history_string(max_chars=1000)
        assert len(history) <= 1000

    def test_last_user_message_skips_assistant(self):
        ctx = ConversationContext()
        ctx.add_message("user", "First message")
        ctx.add_message("assistant", "Response")
        assert ctx.last_user_message == "First message"

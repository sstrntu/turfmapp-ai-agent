"""
Unit tests for ConversationManager fallback logic.
"""

from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import AsyncMock, patch

import pytest

from app.services.conversation_manager import ConversationManager


@pytest.mark.asyncio
async def test_create_conversation_uses_fallback_when_db_unavailable():
    """
    Ensure a new conversation is created in fallback storage when the database call fails.
    """
    manager = ConversationManager()

    with patch.object(
        manager, "use_database_fallback", new=AsyncMock(return_value=None)
    ):
        conversation_id = await manager.create_conversation(
            user_id="user-123", title="My Conversation"
        )

    assert conversation_id in manager.fallback_conversation_metadata
    metadata = manager.fallback_conversation_metadata[conversation_id]
    assert metadata["user_id"] == "user-123"
    assert metadata["title"] == "My Conversation"
    assert conversation_id in manager.fallback_conversations
    assert manager.fallback_conversations[conversation_id] == []


@pytest.mark.asyncio
async def test_save_message_to_conversation_appends_to_fallback_on_failure():
    """
    Verify messages are appended to fallback storage when the database save fails.
    """
    manager = ConversationManager()
    manager.fallback_conversations["conv-123"] = []

    with patch.object(
        manager, "use_database_fallback", new=AsyncMock(return_value=None)
    ):
        result = await manager.save_message_to_conversation(
            conversation_id="conv-123",
            user_id="user-456",
            role="assistant",
            content="Hello from fallback",
            metadata={"sources": []},
        )

    assert result is True
    stored_messages: List[Dict[str, Any]] = manager.fallback_conversations["conv-123"]
    assert len(stored_messages) == 1
    message = stored_messages[0]
    assert message["role"] == "assistant"
    assert message["content"] == "Hello from fallback"
    assert message["metadata"] == {"sources": []}
    assert "timestamp" in message


@pytest.mark.asyncio
async def test_get_conversation_history_prefers_database_result():
    """
    Confirm conversation history uses the database result when available.
    """
    manager = ConversationManager()
    manager.fallback_conversations["conv-db"] = [
        {"role": "assistant", "content": "fallback", "metadata": {}}
    ]

    db_messages = [
        {"role": "user", "content": "db message", "metadata": {"source": "db"}}
    ]

    with patch.object(
        manager, "use_database_fallback", new=AsyncMock(return_value=db_messages)
    ):
        history = await manager.get_conversation_history(
            conversation_id="conv-db", user_id="user-1"
        )

    assert history == db_messages


@pytest.mark.asyncio
async def test_get_conversation_history_uses_fallback_when_db_empty():
    """
    Ensure fallback storage is used when database returns no data.
    """
    manager = ConversationManager()
    manager.fallback_conversations["conv-fallback"] = [
        {"role": "assistant", "content": "stored fallback", "metadata": {}}
    ]

    with patch.object(
        manager, "use_database_fallback", new=AsyncMock(return_value=None)
    ):
        history = await manager.get_conversation_history(
            conversation_id="conv-fallback", user_id="user-2"
        )

    assert history == manager.fallback_conversations["conv-fallback"]

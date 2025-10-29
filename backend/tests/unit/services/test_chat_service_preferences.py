"""
Tests for EnhancedChatService user preference loading.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.services.chat_service import EnhancedChatService


@pytest.mark.asyncio
async def test_get_user_preferences_returns_database_values():
    """
    Preferences should reflect values returned from the database layer.
    """
    service = EnhancedChatService()
    db_row = {"default_model": "claude-3-haiku-20240307", "system_prompt": "You are brief."}

    with patch(
        "app.database.execute_query_one",
        new=AsyncMock(return_value=db_row),
    ):
        prefs = await service.get_user_preferences(user_id="user-db")

    assert prefs["model"] == "claude-3-haiku-20240307"
    assert prefs["system_prompt"] == "You are brief."
    assert prefs["include_reasoning"] is False
    assert prefs["text_format"] == "text"


@pytest.mark.asyncio
async def test_get_user_preferences_returns_defaults_on_failure():
    """
    Defaults are returned when the database lookup fails.
    """
    service = EnhancedChatService()

    with patch(
        "app.database.execute_query_one",
        new=AsyncMock(side_effect=Exception("db unavailable")),
    ):
        prefs = await service.get_user_preferences(user_id="user-default")

    assert prefs["model"] == "gpt-4o"
    assert prefs["include_reasoning"] is False
    assert prefs["text_verbosity"] == "medium"
    assert prefs["reasoning_effort"] == "medium"

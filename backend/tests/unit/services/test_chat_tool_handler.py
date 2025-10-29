"""
Unit tests for ChatToolHandler wrappers.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.chat_tool_handler import ChatToolHandler


@pytest.mark.asyncio
async def test_handle_google_mcp_request_passes_available_tools(monkeypatch):
    """Wrapper should construct available tools and forward to handler."""
    dummy_tools = [{"type": "function", "function": {"name": "gmail_recent"}}]
    captured_kwargs = {}

    async def fake_handle(**kwargs):
        captured_kwargs.update(kwargs)
        return {"success": True}

    monkeypatch.setattr(
        "app.services.chat_tool_handler._build_google_function_tools",
        lambda enabled: dummy_tools if enabled["gmail"] else [],
    )
    monkeypatch.setattr(
        "app.services.chat_tool_handler._handle_google_mcp_request",
        fake_handle,
    )

    handler = ChatToolHandler(chat_api_client=SimpleNamespace())
    result = await handler.handle_google_mcp_request(
        "latest emails",
        [],
        "user-1",
        {"gmail": True},
    )

    assert result == {"success": True}
    assert captured_kwargs["available_tools"] == dummy_tools


def test_extract_gmail_search_query_delegates(monkeypatch):
    """Wrapper should delegate to extractor utility."""
    monkeypatch.setattr(
        "app.services.chat_tool_handler._extract_gmail_search_query",
        lambda message: f"extracted:{message}",
    )

    handler = ChatToolHandler(chat_api_client=None)
    assert handler.extract_gmail_search_query("query") == "extracted:query"


@pytest.mark.asyncio
async def test_handle_tool_calls_delegates(monkeypatch):
    """Wrapper should pass through to executor."""
    async def fake_handle(user_id, calls):
        return [{"user": user_id, "calls": calls}]

    monkeypatch.setattr(
        "app.services.chat_tool_handler._handle_tool_calls",
        fake_handle,
    )

    handler = ChatToolHandler(chat_api_client=None)
    calls = [{"id": "call-1"}]
    result = await handler.handle_tool_calls("user-1", calls)

    assert result == [{"user": "user-1", "calls": calls}]


def test_build_google_function_tools_delegates(monkeypatch):
    """Wrapper should use extracted tool definition builder."""
    monkeypatch.setattr(
        "app.services.chat_tool_handler._build_google_function_tools",
        lambda enabled: ["gmail"] if enabled.get("gmail") else [],
    )

    handler = ChatToolHandler(chat_api_client=None)
    assert handler.build_google_function_tools({"gmail": True}) == ["gmail"]

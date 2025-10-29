"""
Unit tests for GoogleMCPHandler orchestration.
"""

from __future__ import annotations

import pytest

from app.services.google_mcp_handler import GoogleMCPHandler


class StubMCPClient:
    def __init__(self, response=None, should_raise=False):
        self.calls = []
        self._response = response or {"success": True, "response": "ok"}
        self._should_raise = should_raise

    async def call_tool(self, name, params):
        self.calls.append((name, params))
        if self._should_raise:
            raise RuntimeError("boom")
        return self._response


@pytest.mark.asyncio
async def test_execute_tool_calls_returns_structured_results(monkeypatch):
    """Tool execution should enrich responses and capture errors."""
    stub_client = StubMCPClient()
    monkeypatch.setattr(
        "app.services.google_mcp_handler.google_mcp_client",
        stub_client,
    )

    handler = GoogleMCPHandler(call_responses_api_func=None)
    function_calls = [
        {"function": {"name": "gmail_recent", "arguments": {"max_results": 1}}},
        {"function": {"name": "drive_list_files", "arguments": {"max_results": 5}}},
    ]

    results = await handler.execute_tool_calls(function_calls, user_id="user-1")
    assert len(results) == 2
    assert results[0]["tool"] == "gmail_recent"
    assert results[0]["success"] is True
    assert stub_client.calls[0][1]["user_id"] == "user-1"


def test_get_available_tools_respects_enabled_flags():
    """Only requested tool families should be returned."""
    handler = GoogleMCPHandler(call_responses_api_func=None)
    tools = handler.get_available_tools({"gmail": True, "drive": False, "calendar": True})
    names = {tool["function"]["name"] for tool in tools}
    assert "gmail_recent" in names
    assert "calendar_upcoming_events" in names
    assert "drive_list_files" not in names


def test_get_no_tools_response_suggests_services():
    """User-facing guidance should depend on message intent."""
    handler = GoogleMCPHandler(call_responses_api_func=None)
    response = handler.get_no_tools_response("check my calendar")
    assert response["suggested_tools"] == ["calendar"]


def test_parse_function_calls_handles_multiple_formats():
    """Both function_call and tool_use content should be parsed."""
    handler = GoogleMCPHandler(call_responses_api_func=None)
    api_response = {
        "output": [
            {"type": "function_call", "name": "gmail_recent", "arguments": '{"max_results": 1}'},
            {
                "type": "message",
                "content": [
                    {"type": "tool_use", "name": "drive_list_files", "input": {"max_results": 3}}
                ],
            },
        ]
    }

    calls = handler.parse_function_calls(api_response)
    assert len(calls) == 2
    assert calls[0]["function"]["name"] == "gmail_recent"
    assert calls[0]["function"]["arguments"]["max_results"] == 1
    assert calls[1]["function"]["name"] == "drive_list_files"


@pytest.mark.asyncio
async def test_handle_fallback_tools_prefers_gmail(monkeypatch):
    """Fallback should call gmail_recent when Gmail enabled."""
    stub_client = StubMCPClient()
    monkeypatch.setattr(
        "app.services.google_mcp_handler.google_mcp_client",
        stub_client,
    )

    handler = GoogleMCPHandler(call_responses_api_func=None)
    results = await handler.handle_fallback_tools(
        "show me first email",
        {"gmail": True},
        "user-123",
    )

    assert results[0]["tool"] == "gmail_recent"
    assert stub_client.calls[0][0] == "gmail_recent"


@pytest.mark.asyncio
async def test_execute_tool_calls_handles_exceptions(monkeypatch):
    """Errors from MCP client should surface as error entries."""
    stub_client = StubMCPClient(should_raise=True)
    monkeypatch.setattr(
        "app.services.google_mcp_handler.google_mcp_client",
        stub_client,
    )

    handler = GoogleMCPHandler(call_responses_api_func=None)
    results = await handler.execute_tool_calls(
        [{"function": {"name": "drive_list_files", "arguments": {}}}],
        "user-1",
    )

    assert results[0]["success"] is False
    assert "boom" in results[0]["error"]

"""
Unit tests for generic tool executor routing.
"""

from __future__ import annotations

import pytest

from app.services import chat_tool_executor


class DummyAcquire:
    async def __aenter__(self):
        return DummyConnection()

    async def __aexit__(self, exc_type, exc, tb):
        return False


class DummyConnection:
    async def execute(self, *args, **kwargs):
        return None


class DummyPool:
    def acquire(self):
        return DummyAcquire()


@pytest.mark.asyncio
async def test_handle_tool_calls_routes_to_tool_manager(monkeypatch):
    """Non-Google tools should be executed via traditional tool manager."""
    captured = {}

    async def fake_execute(tool_name, user_id, **kwargs):
        captured.update({"tool_name": tool_name, "user_id": user_id, "kwargs": kwargs})
        return {"success": True, "response": "ok"}

    monkeypatch.setattr(
        "app.services.tool_manager.tool_manager",
        type("TM", (), {"execute_tool": staticmethod(fake_execute)}),
    )
    monkeypatch.setattr(
        "app.services.mcp_client.google_mcp_client",
        type("MCP", (), {"connect": staticmethod(lambda: None)}),
    )

    result = await chat_tool_executor.handle_tool_calls(
        "user-1",
        [
            {
                "id": "call-1",
                "function": {"name": "custom_tool", "arguments": '{"value": 5}'},
            }
        ],
    )

    assert result[0]["result"]["success"] is True
    assert captured["tool_name"] == "custom_tool"
    assert captured["kwargs"] == {"value": 5}


@pytest.mark.asyncio
async def test_handle_tool_calls_routes_to_google_mcp(monkeypatch):
    """Google tools should use the MCP client and append user_id."""
    calls = []

    class FakeMCP:
        async def connect(self):
            calls.append("connect")

        async def call_tool(self, name, params):
            calls.append((name, params))
            return {"success": True, "response": "done"}

    monkeypatch.setattr(
        "app.services.mcp_client.google_mcp_client",
        FakeMCP(),
    )
    monkeypatch.setattr(
        "app.services.tool_manager.tool_manager",
        type("TM", (), {"execute_tool": staticmethod(lambda *args, **kwargs: None)}),
    )

    result = await chat_tool_executor.handle_tool_calls(
        "user-2",
        [
            {
                "id": "call-gmail",
                "function": {
                    "name": "gmail_recent",
                    "arguments": '{"max_results": 3}',
                },
            }
        ],
    )

    assert calls[0] == "connect"
    assert calls[1][0] == "gmail_recent"
    assert calls[1][1]["user_id"] == "user-2"
    assert result[0]["result"]["success"] is True


@pytest.mark.asyncio
async def test_handle_tool_calls_image_generation(monkeypatch):
    """Image generation tool should delegate to OpenAI helper."""

    async def fake_generate_image(**kwargs):
        return {"success": True, "response": "![img](data:image/png;base64,abc)"}

    monkeypatch.setattr(
        "app.services.chat_tool_executor.generate_image_tool",
        fake_generate_image,
    )

    result = await chat_tool_executor.handle_tool_calls(
        "user-4",
        [
            {
                "id": "call-image",
                "function": {
                    "name": "generate_image",
                    "arguments": {"prompt": "A cat"},
                },
            }
        ],
    )

    assert result[0]["tool_name"] == "generate_image"
    assert result[0]["result"]["success"] is True


@pytest.mark.asyncio
async def test_handle_tool_calls_handles_invalid_json(monkeypatch):
    """Malformed JSON arguments should return an error entry."""
    monkeypatch.setattr(
        "app.services.tool_manager.tool_manager",
        type("TM", (), {"execute_tool": staticmethod(lambda *args, **kwargs: None)}),
    )
    monkeypatch.setattr(
        "app.services.mcp_client.google_mcp_client",
        type(
            "MCP",
            (),
            {
                "connect": staticmethod(lambda: None),
                "call_tool": staticmethod(lambda *args, **kwargs: {"success": True}),
            },
        ),
    )

    result = await chat_tool_executor.handle_tool_calls(
        "user-3",
        [
            {
                "id": "call-bad",
                "function": {"name": "gmail_recent", "arguments": "not json"},
            }
        ],
    )

    assert result[0]["result"]["success"] is False
    assert "expecting value" in result[0]["result"]["error"].lower()

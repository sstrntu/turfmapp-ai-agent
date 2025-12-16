"""
Unit tests for ChatApiClient request construction.
"""

from __future__ import annotations

from typing import Any, Dict, List

import pytest

from app.services.chat_api_client import ChatApiClient


class _StubResponse:
    def __init__(self, status_code: int, data: Dict[str, Any]):
        self.status_code = status_code
        self._data = data
        self.text = "stubbed"

    def json(self) -> Dict[str, Any]:
        return self._data


class _StubAsyncClient:
    """
    Minimal async client that records requests made by ChatApiClient.
    """

    def __init__(self):
        self.post_calls: List[Dict[str, Any]] = []

    async def __aenter__(self) -> "_StubAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        return None

    async def post(self, url: str, headers: Dict[str, Any], json: Dict[str, Any]):
        self.post_calls.append({"url": url, "headers": headers, "json": json})
        return _StubResponse(200, {"status": "completed", "output": []})

    async def get(self, *args, **kwargs):
        return _StubResponse(200, {"status": "completed"})


@pytest.mark.asyncio
async def test_call_responses_api_transforms_tools_and_messages(monkeypatch):
    """
    Verify the Responses API payload is constructed correctly with tool metadata.
    """
    stub_client = _StubAsyncClient()

    def _client_factory(*args, **kwargs):
        return stub_client

    monkeypatch.setattr(
        "app.services.chat_api_client.httpx.AsyncClient", _client_factory
    )

    api_client = ChatApiClient()
    messages = [
        {"role": "system", "content": "you are a helpful assistant"},
        {"role": "user", "content": "Where should I eat tonight?"},
    ]

    tools = [
        {
            "type": "function",
            "function": {
                "name": "restaurant_suggester",
                "description": "Suggests restaurants",
                "parameters": {"type": "object"},
            },
        },
        {"type": "web_search_preview", "search_context_size": "large"},
        {"type": "image_generation", "quality": "high"},
    ]

    result = await api_client.call_responses_api(
        messages,
        model="gpt-4o",
        include_reasoning=False,
        tools=tools,
        tool_choice="required",
        temperature=0.3,
    )

    assert result == {"status": "completed", "output": []}
    assert len(stub_client.post_calls) == 1

    payload = stub_client.post_calls[0]["json"]
    assert payload["model"] == "gpt-4o"
    assert payload["tool_choice"] == "required"
    assert payload["parallel_tool_calls"] is True
    assert payload["temperature"] == 0.3

    # Input string should contain conversation context and highlight the current user message
    assert "System: you are a helpful assistant" in payload["input"]
    assert "CURRENT USER QUESTION: Where should I eat tonight?" in payload["input"]

    converted_tools = payload["tools"]
    assert len(converted_tools) == 3

    function_tool = converted_tools[0]
    assert function_tool == {
        "type": "function",
        "name": "restaurant_suggester",
        "description": "Suggests restaurants",
        "parameters": {"type": "object"},
    }

    web_search_tool = next(tool for tool in converted_tools if tool["type"] == "web_search_preview")
    assert web_search_tool["search_context_size"] == "large"
    assert web_search_tool["user_location"]["type"] == "approximate"

    image_tool = next(tool for tool in converted_tools if tool["type"] == "image_generation")
    assert image_tool["quality"] == "high"
    assert image_tool["output_format"] == "png"


@pytest.mark.asyncio
async def test_call_responses_api_raises_on_http_error(monkeypatch):
    """HTTP failures should surface as exceptions."""

    class _ErrorResponse:
        status_code = 500
        text = "failure"

    class _FailingClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            return _ErrorResponse()

    monkeypatch.setattr(
        "app.services.chat_api_client.httpx.AsyncClient",
        lambda timeout: _FailingClient(),
    )

    api_client = ChatApiClient()
    with pytest.raises(Exception):
        await api_client.call_responses_api([{"role": "user", "content": "hi"}])

"""
Unit tests for Anthropic client helper.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.anthropic_client import AnthropicClient


def test_format_messages_filters_roles():
    """Only user/assistant roles should be forwarded."""
    client = AnthropicClient()
    formatted = client._format_messages(
        [
            {"role": "system", "content": "ignored"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
    )
    assert len(formatted) == 2
    assert formatted[0]["role"] == "user"
    assert formatted[0]["content"][0]["text"] == "Hello"


def test_convert_tools_to_anthropic_format_translates_supported_types():
    """Ensure web search and function tools are converted correctly."""
    client = AnthropicClient()
    tools = [
        {
            "type": "web_search_preview",
            "name": "search",
            "user_location": {"type": "approximate", "country": "TH"},
        },
        {
            "type": "function",
            "function": {
                "name": "do_work",
                "description": "Does work",
                "parameters": {"type": "object"},
            },
        },
    ]

    converted = client._convert_tools_to_anthropic_format(tools)
    assert converted[0]["type"] == "web_search_20250305"
    assert converted[0]["user_location"]["country"] == "TH"
    assert converted[1]["type"] == "custom"
    assert converted[1]["name"] == "do_work"


@pytest.mark.asyncio
async def test_call_messages_api_requires_api_key(monkeypatch):
    """Missing API key should raise a ValueError early."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    client = AnthropicClient()
    with pytest.raises(ValueError):
        await client.call_messages_api([])


@pytest.mark.asyncio
async def test_call_messages_api_success(monkeypatch):
    """Successful request should return JSON payload from httpx."""
    payload = {"id": "resp-1"}

    class StubResponse:
        def __init__(self):
            self.status_code = 200

        def json(self):
            return payload

        def raise_for_status(self):
            return None

    class StubClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json, headers):
            self.last_request = {"url": url, "json": json, "headers": headers}
            return StubResponse()

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    client = AnthropicClient()

    monkeypatch.setattr(
        "app.services.anthropic_client.httpx.AsyncClient",
        lambda timeout: StubClient(),
    )

    response = await client.call_messages_api(
        [{"role": "user", "content": "Hi"}],
        tools=[{"type": "function", "function": {"name": "do_it"}}],
    )

    assert response == payload

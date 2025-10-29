"""
Unit tests for Supabase auth helper.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.supabase_auth import fetch_user_with_access_token


class StubResponse:
    def __init__(self, status_code: int, payload: dict) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return self._payload


class StubAsyncClient:
    def __init__(self, response: StubResponse) -> None:
        self._response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url: str, headers: dict):
        self.last_request = {"url": url, "headers": headers}
        return self._response


@pytest.mark.asyncio
async def test_fetch_user_with_access_token_success(monkeypatch):
    """A 200 response should return a populated PublicUser."""
    payload = {
        "id": "user-1",
        "email": "test@example.com",
        "user_metadata": {"full_name": "Test User", "avatar_url": "https://avatar"},
    }
    stub_client = StubAsyncClient(StubResponse(200, payload))

    monkeypatch.setenv("SUPABASE_URL", "https://supabase.local")
    monkeypatch.setattr("app.services.supabase_auth.httpx.AsyncClient", lambda timeout: stub_client)

    user = await fetch_user_with_access_token("token-123")
    assert user is not None
    assert user.id == "user-1"
    assert user.email == "test@example.com"
    assert user.name == "Test User"
    assert user.avatar_url == "https://avatar"
    assert stub_client.last_request["headers"]["Authorization"] == "Bearer token-123"


@pytest.mark.asyncio
async def test_fetch_user_with_access_token_handles_missing_env(monkeypatch):
    """If SUPABASE_URL is not configured the helper should return None."""
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    result = await fetch_user_with_access_token("any-token")
    assert result is None


@pytest.mark.asyncio
async def test_fetch_user_with_access_token_handles_http_failure(monkeypatch):
    """Non-200 responses should return None."""
    stub_client = StubAsyncClient(StubResponse(401, {}))
    monkeypatch.setenv("SUPABASE_URL", "https://supabase.local")
    monkeypatch.setattr("app.services.supabase_auth.httpx.AsyncClient", lambda timeout: stub_client)

    assert await fetch_user_with_access_token("bad-token") is None

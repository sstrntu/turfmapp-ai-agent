"""Tests for OpenAI image generation helper."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services import image_generation


class _StubImages:
    def __init__(self, payload):
        self._payload = payload

    async def generate(self, **kwargs):  # pragma: no cover - executed in tests
        self.last_kwargs = kwargs
        return SimpleNamespace(data=[self._payload])


class _StubClient:
    def __init__(self, payload):
        self.images = _StubImages(payload)


@pytest.mark.asyncio
async def test_generate_image_returns_markdown(monkeypatch):
    payload = SimpleNamespace(b64_json="ZmFrZQ==")
    stub_client = _StubClient(payload)
    monkeypatch.setattr(image_generation, "_create_client", lambda: stub_client)

    result = await image_generation.generate_image(prompt="A sunset", output_format="png")

    assert result["success"] is True
    assert result["response"].startswith("Generated an image")
    assert result["image_base64"] == "ZmFrZQ=="


@pytest.mark.asyncio
async def test_generate_image_returns_url(monkeypatch):
    payload = SimpleNamespace(url="https://example.com/image.png", b64_json=None)
    stub_client = _StubClient(payload)
    monkeypatch.setattr(image_generation, "_create_client", lambda: stub_client)

    result = await image_generation.generate_image(prompt="A lake", output_format="jpeg")

    assert result["success"] is True
    assert result["response"].startswith("Generated an image")
    assert result["image_url"] == "https://example.com/image.png"


@pytest.mark.asyncio
async def test_generate_image_requires_prompt():
    result = await image_generation.generate_image(prompt="")
    assert result["success"] is False
    assert "requires a prompt" in result["error"]

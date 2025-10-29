"""Async helpers for generating images with OpenAI GPT-Image-1."""

from __future__ import annotations

import logging
import os
from typing import Optional

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


def _create_client() -> AsyncOpenAI:
    """Create an AsyncOpenAI client using the configured API key."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    return AsyncOpenAI(api_key=api_key)


async def generate_image(
    *,
    prompt: str,
    size: Optional[str] = None,
    quality: Optional[str] = None,
    background: Optional[str] = None,
    output_format: str = "png",
) -> dict:
    """Generate an image using the GPT-Image-1 model.

    Args:
        prompt: Natural language description of the desired image.
        size: Optional size string (e.g., "1024x1024", "512x512").
        quality: Optional quality flag ("standard" or "high").
        background: Optional background setting ("transparent", "white").
        output_format: Desired output format ("png" or "jpeg").

    Returns:
        Dict with success flag and either markdown response or error message.
    """

    prompt = (prompt or "").strip()
    if not prompt:
        return {"success": False, "error": "Image generation requires a prompt."}

    client = _create_client()

    request_kwargs = {
        "model": "gpt-image-1",
        "prompt": prompt,
    }

    if size and size != "auto":
        request_kwargs["size"] = size

    if quality and quality != "auto":
        # API expects "standard" or "high". Default to standard otherwise.
        request_kwargs["quality"] = "high" if quality == "high" else "standard"

    if background and background not in {"", "auto"}:
        normalized_background = background.lower()
        if normalized_background == "white":
            normalized_background = "opaque"
        if normalized_background in {"transparent", "opaque"}:
            request_kwargs["background"] = normalized_background

    try:
        response = await client.images.generate(**request_kwargs)
    except Exception as exc:  # pragma: no cover - passthrough for wrapped errors
        logger.error("Image generation failed: %s", exc)
        return {"success": False, "error": str(exc)}

    if not response.data:
        return {"success": False, "error": "Image API returned no data."}

    data = response.data[0]

    if getattr(data, "b64_json", None):
        image_b64 = data.b64_json
        return {
            "success": True,
            "response": "Generated an image using GPT-Image-1.",
            "image_base64": image_b64,
            "output_format": output_format,
        }

    if getattr(data, "url", None):
        image_url = data.url
        return {
            "success": True,
            "response": "Generated an image using GPT-Image-1.",
            "image_url": image_url,
            "output_format": output_format,
        }

    return {"success": False, "error": "Image API did not include image data."}

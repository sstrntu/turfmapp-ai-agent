"""
Anthropic API Client - Claude Messages Integration

Provides a thin wrapper around the Anthropic Messages API so the chat service
can route conversational requests to Claude models when requested.
"""

from __future__ import annotations

import os
import logging
from typing import List, Dict, Any, Optional

import httpx

logger = logging.getLogger(__name__)


class AnthropicClient:
    """Client for interacting with Anthropic's Claude Messages API."""

    def __init__(self) -> None:
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.api_version = os.getenv("ANTHROPIC_API_VERSION", "2023-06-01")
        self.beta_header = os.getenv("ANTHROPIC_BETA", "messages-2023-12-15")
        self.base_url = "https://api.anthropic.com/v1/messages"

        if not self.api_key:
            logger.warning("⚠️  ANTHROPIC_API_KEY not configured; Claude models disabled.")

    def _format_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert internal chat message format to Anthropic message schema."""
        formatted: List[Dict[str, Any]] = []

        for message in messages:
            role = message.get("role")
            content = message.get("content", "")

            if role not in {"user", "assistant"}:
                # Anthropic only accepts user/assistant roles
                continue

            formatted.append(
                {
                    "role": role,
                    "content": [
                        {
                            "type": "text",
                            "text": content or "",
                        }
                    ],
                }
            )

        return formatted

    def _convert_tools_to_anthropic_format(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert tools from OpenAI/custom format to Anthropic tool format."""
        anthropic_tools = []

        for tool in tools:
            tool_type = tool.get("type")

            # Handle web search tool
            if tool_type in {"web_search_preview", "web_search"}:
                search_tool: Dict[str, Any] = {
                    "type": "web_search_20250305",
                    "name": tool.get("name", "web_search"),
                }

                user_location = tool.get("user_location")
                if isinstance(user_location, dict):
                    location_payload: Dict[str, Any] = {}
                    location_type = user_location.get("type")
                    if location_type:
                        location_payload["type"] = location_type

                    for key in ("city", "region", "country", "country_code"):
                        value = user_location.get(key)
                        if value:
                            location_payload[key] = value

                    if len(location_payload) > (1 if "type" in location_payload else 0):
                        search_tool["user_location"] = location_payload

                anthropic_tools.append(search_tool)
            elif tool_type == "function":
                function_spec = tool.get("function", {})
                name = function_spec.get("name")
                if name:
                    anthropic_tools.append(
                        {
                            "type": "custom",
                            "name": name,
                            "description": function_spec.get("description", ""),
                            "input_schema": function_spec.get("parameters", {"type": "object"}),
                        }
                    )
            # Add other tool types as needed

        return anthropic_tools

    async def call_messages_api(
        self,
        messages: List[Dict[str, Any]],
        *,
        model: str = "claude-sonnet-4-5-20250929",
        system: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: Optional[float] = 0.7,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Invoke Claude via the Messages API and return the parsed JSON response."""
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is not configured")

        payload: Dict[str, Any] = {
            "model": model,
            "messages": self._format_messages(messages),
            "max_tokens": max_tokens,
        }

        if system:
            payload["system"] = system

        # Temperature is optional; omit if None to use Anthropic defaults
        if temperature is not None:
            payload["temperature"] = temperature

        # Add tools if provided (for web search, etc.)
        if tools:
            # Convert tools from OpenAI/custom format to Anthropic format
            anthropic_tools = self._convert_tools_to_anthropic_format(tools)
            if anthropic_tools:
                payload["tools"] = anthropic_tools
                logger.info(f"🔧 Added {len(anthropic_tools)} tools to Claude request")

        headers = {
            "x-api-key": self.api_key,
            "content-type": "application/json",
            "anthropic-version": self.api_version,
        }
        if self.beta_header:
            headers["anthropic-beta"] = self.beta_header

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
                response = await client.post(self.base_url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as error:
            logger.error(
                "❌ Claude API error: status=%s response=%s",
                error.response.status_code if error.response else "unknown",
                (error.response.text if error.response else "no response"),
            )
            raise
        except httpx.RequestError as error:
            logger.error("❌ Claude API request failed: %s", error)
            raise


# Global instance for convenience
anthropic_client = AnthropicClient()

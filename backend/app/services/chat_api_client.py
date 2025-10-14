"""
Chat API Client - OpenAI Responses API Integration

This module handles all interactions with the OpenAI Responses API, including:
- Request formatting and payload construction
- Tool configuration (function calling, web search, image generation)
- Response parsing and polling for async responses
- Error handling and timeout management

Architecture:
- Standalone client for API communication
- Supports multiple models (GPT-4O, O1, GPT-5-mini)
- Handles tool-calling in Responses API format
- Async polling for long-running requests
"""

from __future__ import annotations

import os
import asyncio
import logging
from typing import List, Dict, Any

import httpx

from .chat_instructions import build_system_instructions

# Configure logger
logger = logging.getLogger(__name__)


class ChatApiClient:
    """Client for OpenAI Responses API integration."""

    def __init__(self):
        self.responses_api_key = os.getenv("OPENAI_API_KEY", "")
        self.responses_base_url = "https://api.openai.com/v1/responses"

    async def call_responses_api(
        self,
        messages: List[Dict[str, Any]],
        model: str = "gpt-4o",
        include_reasoning: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Call the OpenAI Responses API with proper format."""
        logger.info(f"📡 call_responses_api called with {len(messages)} messages, model={model}")
        headers = {
            "Authorization": f"Bearer {self.responses_api_key}",
            "Content-Type": "application/json"
        }

        # Convert messages to conversation context string (Responses API format)
        conversation_context = ""

        # Add conversation history
        for i, msg in enumerate(messages[:-1]):  # All but the last message
            role = msg["role"].title()
            conversation_context += f"{role}: {msg['content']}\n\n"

        # Emphasize the current user question
        if messages:
            current_msg = messages[-1]
            if current_msg.get("role") == "user":
                conversation_context += f"CURRENT USER QUESTION: {current_msg['content']}\n\n"
            else:
                role = current_msg["role"].title()
                conversation_context += f"{role}: {current_msg['content']}\n\n"

        # Build payload for Responses API
        # GPT-5-mini needs more tokens for web search and reasoning
        default_tokens = 4000 if model == "gpt-5-mini" else 1500
        payload = {
            "model": model,
            "input": conversation_context.strip(),
            "max_output_tokens": kwargs.get("max_tokens", default_tokens),
        }

        # Add temperature for supported models
        if model not in ["gpt-5-mini"] and "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]
        elif model not in ["gpt-5-mini"]:
            payload["temperature"] = 0.7

        # Handle tools properly - Responses API format
        if "tools" in kwargs and kwargs["tools"]:
            tools = kwargs["tools"]
            logger.debug(f"🔧 Processing tools in API call: {tools}")
            # Filter out invalid string-based tools
            if isinstance(tools, list) and tools:
                if isinstance(tools[0], str):
                    logger.debug(f"⚠️ Removing invalid tools format: {tools}")
                else:
                    # Convert from Chat Completions format to Responses API format
                    responses_api_tools = []
                    for tool in tools[:5]:  # Limit to 5 tools
                        if tool.get("type") == "function":
                            func = tool.get("function", {})
                            responses_tool = {
                                "type": "function",
                                "name": func.get("name"),
                                "description": func.get("description"),
                                "parameters": func.get("parameters", {})
                            }
                            responses_api_tools.append(responses_tool)
                        elif tool.get("type") == "web_search_preview":
                            # Handle web search tools for Responses API
                            web_search_tool = {
                                "type": "web_search_preview",
                                "user_location": tool.get("user_location", {"type": "approximate"}),
                                "search_context_size": tool.get("search_context_size", "medium")
                            }
                            responses_api_tools.append(web_search_tool)
                            logger.debug(f"🌐 Added web search tool to Responses API payload")
                        elif tool.get("type") == "image_generation":
                            # Handle image generation tools for Responses API
                            image_gen_tool = {
                                "type": "image_generation",
                                "size": tool.get("size", "auto"),
                                "quality": tool.get("quality", "auto"),
                                "output_format": tool.get("output_format", "png"),
                                "background": tool.get("background", "auto"),
                                "moderation": tool.get("moderation", "auto"),
                                "partial_images": tool.get("partial_images", 3)
                            }
                            responses_api_tools.append(image_gen_tool)
                            logger.debug(f"🎨 Added image generation tool to Responses API payload")

                    payload["tools"] = responses_api_tools
                    payload["tool_choice"] = kwargs.get("tool_choice", "auto")
                    payload["parallel_tool_calls"] = True
                    logger.debug(f"🔧 Added tools to payload (Responses API format): {payload['tools']}")
        else:
            logger.debug(f"🔧 No tools provided in API call")

        instructions = build_system_instructions(
            tools=payload.get("tools"),
            developer_instructions=kwargs.get("developer_instructions"),
            assistant_context=kwargs.get("assistant_context"),
        )

        if instructions:
            payload["instructions"] = instructions

        # Add reasoning for o1 models
        if include_reasoning and model in ["o1", "o1-mini", "o1-preview"]:
            payload["reasoning"] = True

        try:
            api_timeout = 60.0 if payload.get("tools") else 30.0
            async with httpx.AsyncClient(timeout=httpx.Timeout(api_timeout, connect=15.0)) as client:
                response = await client.post(
                    self.responses_base_url,
                    headers=headers,
                    json=payload
                )

                if response.status_code != 200:
                    raise Exception(f"API request failed: {response.status_code} {response.text}")

                data = response.json()
                logger.debug(f"📡 API response data: {data}")

                # Handle async responses (poll for completion)
                status_val = data.get("status")
                response_id = data.get("id")

                if status_val in {"in_progress", "queued"} and response_id:
                    attempts_remaining = 8
                    while status_val in {"in_progress", "queued"} and attempts_remaining > 0:
                        await asyncio.sleep(0.25)
                        poll = await client.get(
                            f"https://api.openai.com/v1/responses/{response_id}",
                            headers=headers
                        )
                        if poll.status_code == 200:
                            data = poll.json()
                            status_val = data.get("status")
                        attempts_remaining -= 1

                return data

        except httpx.HTTPError as e:
            raise Exception(f"API request failed: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error: {e}")


# Global instance for convenience
chat_api_client = ChatApiClient()

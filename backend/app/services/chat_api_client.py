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

        # Add instructions for additional context
        instructions = []

        # Add critical tool usage rule at the top
        instructions.append("""
CRITICAL TOOL USAGE RULE:
- Gmail, Drive, and Calendar tools are ONLY for personal data (emails, files, calendar events)
- NEVER use these tools for general knowledge questions, sports scores, news, weather, or any non-personal data
- For general knowledge questions, use web search or answer from your training data
- Examples of what NOT to use Google tools for: "Who is the top scorer?", "What's the weather?", "Latest news"

CONVERSATION CONTEXT RULES:
1. The current user question is marked as "CURRENT USER QUESTION:" - THIS is what you must respond to
2. Use conversation history for context, but ALWAYS address the current question directly
3. Never return a previous answer when asked a new question, even if they seem similar
4. For time-sensitive data (sports scores, news, weather), always perform fresh searches regardless of history
5. If the current question asks about personal data (emails, calendar, files), use the appropriate tools even if similar questions were asked before
""")

        if "developer_instructions" in kwargs and kwargs["developer_instructions"]:
            instructions.append(kwargs["developer_instructions"])
        if "assistant_context" in kwargs and kwargs["assistant_context"]:
            instructions.append(kwargs["assistant_context"])

        # Add web search tool instructions if available
        web_search_available = any(tool.get("type") == "web_search_preview" for tool in payload.get("tools", []))
        if web_search_available:
            web_search_instructions = """
You have tools available. Use them when they would provide better, more current information than your training data. Use web search for current information: sports scores, news, weather, current season data, latest facts, or when users ask 'who is', 'what is the latest', 'this season', 'this year'."""
            instructions.append(web_search_instructions)

        # Add Google service tool instructions if available
        google_tools_available = any(tool.get("name", "").startswith(("gmail_", "drive_", "calendar_")) for tool in payload.get("tools", []))
        if google_tools_available:
            google_instructions = f"""
You have access to Google service tools (Gmail, Drive, Calendar) that can help users with their personal data.

CRITICAL RULE: These tools are ONLY for personal data (emails, files, calendar events). NEVER use these tools for general knowledge questions, sports scores, news, weather, or any non-personal data queries.

Gmail tools (ONLY for personal emails):
- gmail_recent: Get recent Gmail messages
- gmail_search: Search Gmail messages with query parameters
- gmail_get_message: Get full content of a specific Gmail message
- gmail_important: Get important/starred Gmail messages

Drive tools (ONLY for personal files):
- drive_list_files: List files in Google Drive
- drive_create_folder: Create folder structure in Google Drive
- drive_list_folder_files: List files in a specific Drive folder

Calendar tools (ONLY for personal schedule):
- calendar_list_events: List Google Calendar events
- calendar_upcoming_events: Get upcoming calendar events

Examples of when to use Google tools:
- "Show me my recent emails"
- "What files do I have in my Drive?"
- "What's on my calendar today?"
- "Find emails from John"

Examples of when NOT to use Google tools:
- "Who is the top scorer in J1?" (general knowledge - use web search instead)
- "Who is the top J2 scorer in 2025 season?" (general knowledge - use web search instead)
- "What is the capital of France?" (general knowledge)
- "Tell me about the latest news" (general knowledge - use web search instead)
- "What's the weather like?" (general knowledge - use web search instead)

For general knowledge questions, use web search or answer from your training data.
"""
            instructions.append(google_instructions)

        if instructions:
            payload["instructions"] = "\n\n".join(instructions)

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

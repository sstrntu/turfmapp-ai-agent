"""
Enhanced Chat Service - Core Business Logic for AI Chat Operations

This service provides the primary business logic for chat functionality, including:
- Multi-model AI integration (GPT-4O, O1, GPT-5-mini via OpenAI Responses API)  
- Conversation management with persistent storage
- Sources extraction and metadata enrichment
- Database fallback patterns for resilience
- Response parsing and error handling

Architecture:
- Service layer pattern separating business logic from API endpoints
- Database-first with in-memory fallback for development/testing
- Async operations for performance with external API calls
- Comprehensive error handling and graceful degradation

Recent improvements (August 2025):
- Fixed sources extraction and metadata preservation
- Enhanced GPT-5-mini support with 4000 token limit
- Improved incomplete response handling
- Auto-generated conversation titles from first message
"""

from __future__ import annotations

import asyncio
import logging
from typing import List, Dict, Any, Optional, Iterable
from datetime import datetime, timezone
import uuid
import json
import re
from collections import deque

from fastapi import HTTPException
from ..database import ConversationService
from ..utils.chat_utils import format_chat_history
from .mcp_client import google_mcp_client, get_all_google_tools
from .chat_api_client import chat_api_client
from .chat_tool_handler import ChatToolHandler
from .anthropic_client import anthropic_client
from .chat_instructions import build_system_instructions
from urllib.parse import urlparse

# Configure logger
logger = logging.getLogger(__name__)

_URL_PATTERN = re.compile(r"https?://[^\s\]\)\"'>]+")


def _build_source_entry(url: Optional[str], title: Optional[str] = None) -> Optional[Dict[str, str]]:
    """Build a normalized source entry from URL and title."""
    if not isinstance(url, str):
        return None

    url = url.strip()
    if not url:
        return None

    if url.startswith("//"):
        url = f"https:{url}"
    elif not url.lower().startswith(("http://", "https://")):
        url = f"https://{url}"

    try:
        parsed = urlparse(url)
    except ValueError:
        return None

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None

    site = parsed.netloc
    display_title = title.strip() if isinstance(title, str) and title.strip() else site

    return {
        "url": url,
        "title": display_title,
        "site": site,
        "favicon": f"https://www.google.com/s2/favicons?domain={site}&sz=64",
    }


def _dedupe_sources(sources: Iterable[Dict[str, str]]) -> List[Dict[str, str]]:
    """Deduplicate sources, preserving order and limiting count."""
    unique: List[Dict[str, str]] = []
    seen = set()

    for source in sources:
        url = source.get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        unique.append(source)
        if len(unique) >= 8:
            break

    return unique


def _extract_sources_from_text(text: str) -> List[Dict[str, str]]:
    """Extract HTTP(S) URLs from plain text and convert to sources."""
    if not isinstance(text, str):
        return []

    matches = _URL_PATTERN.findall(text)
    sources = []
    for match in matches:
        cleaned = match.rstrip(".,);]")
        source = _build_source_entry(cleaned)
        if source:
            sources.append(source)
    return sources


def _extract_sources_from_object(obj: Any) -> List[Dict[str, str]]:
    """Recursively extract source entries from nested data structures."""
    sources: List[Dict[str, str]] = []
    queue: deque[Any] = deque([obj])

    while queue:
        current = queue.popleft()

        if isinstance(current, dict):
            url = current.get("url") or current.get("link") or current.get("href")
            title = current.get("title") or current.get("name") or current.get("headline") or current.get("text")

            source = _build_source_entry(url, title)
            if source:
                sources.append(source)

            for value in current.values():
                if isinstance(value, (list, dict, str)):
                    queue.append(value)

        elif isinstance(current, list):
            for item in current:
                if isinstance(item, (list, dict, str)):
                    queue.append(item)

        elif isinstance(current, str):
            try:
                parsed = json.loads(current)
            except (TypeError, ValueError):
                sources.extend(_extract_sources_from_text(current))
            else:
                queue.append(parsed)

    return sources


def _extract_sources_from_tool_result(tool_result: Dict[str, Any]) -> List[Dict[str, str]]:
    """Extract sources from a tool result payload."""
    if not isinstance(tool_result, dict):
        return []

    candidate_values: List[Any] = []
    for key in ("output", "content", "outputs", "results", "data", "value"):
        value = tool_result.get(key)
        if value:
            candidate_values.append(value)

    tool_info = tool_result.get("tool")
    if isinstance(tool_info, dict):
        for key in ("output", "outputs", "results"):
            if tool_info.get(key):
                candidate_values.append(tool_info[key])

    sources: List[Dict[str, str]] = []
    for candidate in candidate_values:
        sources.extend(_extract_sources_from_object(candidate))

    return _dedupe_sources(sources)


def _extract_tool_payloads(tool_result: Dict[str, Any]) -> List[Any]:
    """Extract raw payloads from tool result for block rendering."""
    if not isinstance(tool_result, dict):
        return []

    payloads: List[Any] = []

    def _add_payload(value: Any) -> None:
        if value is None:
            return
        payloads.append(value)

    content_items = tool_result.get("content")
    if isinstance(content_items, list):
        for entry in content_items:
            if not isinstance(entry, dict):
                continue
            entry_type = entry.get("type")
            if entry_type in {"json", "json_object"} and entry.get("json") is not None:
                _add_payload(entry.get("json"))
            elif entry_type in {"text", "output_text"}:
                text = entry.get("text")
                if not text:
                    continue
                try:
                    _add_payload(json.loads(text))
                except (TypeError, ValueError):
                    _add_payload(text)

    for key in ("result", "output", "data", "value"):
        if key in tool_result and tool_result[key]:
            _add_payload(tool_result[key])

    return payloads


def _serialise_args(args: Any) -> Optional[str]:
    """Serialise tool arguments for display."""
    if args is None:
        return None
    if isinstance(args, str):
        return args
    try:
        return json.dumps(args, ensure_ascii=False, indent=2)
    except TypeError:
        return str(args)


def _build_blocks_from_tool_results(
    tool_results: Iterable[Dict[str, Any]],
    tool_call_inputs: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Convert tool results into structured blocks for frontend rendering."""
    blocks: List[Dict[str, Any]] = []

    if tool_call_inputs is None:
        tool_call_inputs = {}

    for index, tool_result in enumerate(tool_results):
        if not isinstance(tool_result, dict):
            continue

        call_id = (
            tool_result.get("tool_call_id")
            or tool_result.get("id")
            or tool_result.get("tool_use_id")
        )
        tool_name = (
            tool_result.get("name")
            or tool_result.get("tool_name")
            or tool_call_inputs.get(call_id, {}).get("name")
        )

        args_info = tool_call_inputs.get(call_id, {})
        args_payload = args_info.get("args")
        args_text = args_info.get("args_text") or _serialise_args(args_payload)

        payloads = _extract_tool_payloads(tool_result)

        block_id_prefix = (tool_name or "tool").replace(" ", "-").lower()
        base_common = {
            "toolName": tool_name,
            "args": args_payload,
            "argsText": args_text,
            "callId": call_id,
        }

        created_block = False
        for payload in payloads:
            if isinstance(payload, dict):
                results = None
                for key in ("results", "search_results", "items"):
                    candidate = payload.get(key)
                    if isinstance(candidate, list) and candidate:
                        results = candidate
                        break

                if results:
                    normalised_results = []
                    for item in results:
                        if isinstance(item, dict):
                            source = _build_source_entry(
                                item.get("url")
                                or item.get("link")
                                or item.get("source_url"),
                                item.get("title") or item.get("name"),
                            )
                            snippet = (
                                item.get("snippet")
                                or item.get("description")
                                or item.get("text")
                            )
                            entry = {
                                "title": source["title"] if source else (item.get("title") or item.get("name") or "Result"),
                                "url": source["url"] if source else item.get("url") or item.get("link"),
                                "snippet": snippet,
                                "site": source["site"] if source else item.get("site"),
                                "favicon": source["favicon"] if source else item.get("favicon"),
                            }
                            normalised_results.append(entry)
                        elif isinstance(item, str):
                            normalised_results.append(
                                {
                                    "title": item,
                                    "url": None,
                                    "snippet": None,
                                }
                            )

                    if normalised_results:
                        blocks.append(
                            {
                                "id": f"{block_id_prefix}-search-{index}",
                                "type": "search-results",
                                "title": payload.get("title")
                                or payload.get("query")
                                or payload.get("topic")
                                or (tool_name or "Search results"),
                                "results": normalised_results,
                                **base_common,
                            }
                        )
                        created_block = True
                        continue

                # Fallback to key-value representation for structured dicts
                pairs = []
                for key, value in payload.items():
                    if isinstance(value, (dict, list)):
                        value_repr = json.dumps(value, ensure_ascii=False, indent=2)
                    else:
                        value_repr = str(value)
                    pairs.append({"label": key, "value": value_repr})

                if pairs:
                    blocks.append(
                        {
                            "id": f"{block_id_prefix}-object-{index}",
                            "type": "key-value",
                            "title": payload.get("title") or (tool_name or "Tool output"),
                            "pairs": pairs,
                            **base_common,
                        }
                    )
                    created_block = True
                    continue

            elif isinstance(payload, str):
                text = payload.strip()
                if text:
                    blocks.append(
                        {
                            "id": f"{block_id_prefix}-markdown-{index}",
                            "type": "markdown",
                            "text": text,
                            **base_common,
                        }
                    )
                    created_block = True
                    continue

        if not created_block:
            fallback_payload = payloads[0] if payloads else tool_result
            blocks.append(
                {
                    "id": f"{block_id_prefix}-raw-{index}",
                    "type": "tool-call",
                    "title": tool_name or "Tool response",
                    "result": fallback_payload,
                    **base_common,
                }
            )

    return _dedupe_blocks(blocks)


def _dedupe_blocks(blocks: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate blocks while preserving order."""
    cleaned: List[Dict[str, Any]] = []
    seen: set = set()

    for block in blocks:
        if not isinstance(block, dict):
            continue
        block_id = block.get("id")
        if block_id:
            key = ("id", block_id)
        else:
            key = ("hash", block.get("type"), block.get("toolName"), block.get("title"))
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(block)
        if len(cleaned) >= 8:
            break

    return cleaned


def _extract_sources_from_claude_response(response: Dict[str, Any]) -> List[Dict[str, str]]:
    """Extract sources from Claude response payload."""
    sources: List[Dict[str, str]] = []

    content_blocks = response.get("content", [])
    if isinstance(content_blocks, list):
        for block in content_blocks:
            if not isinstance(block, dict):
                continue

            citations = block.get("citations") or block.get("metadata", {}).get("citations")
            if isinstance(citations, list):
                for citation in citations:
                    if isinstance(citation, dict):
                        source = _build_source_entry(
                            citation.get("url") or citation.get("source_url") or citation.get("source"),
                            citation.get("title") or citation.get("text"),
                        )
                        if source:
                            sources.append(source)

            if block.get("type") == "tool_result":
                sources.extend(_extract_sources_from_tool_result(block))

            sources.extend(_extract_sources_from_object(block.get("search_results")))

    top_level_citations = response.get("citations")
    if isinstance(top_level_citations, list):
        for citation in top_level_citations:
            if isinstance(citation, dict):
                source = _build_source_entry(
                    citation.get("url") or citation.get("source_url") or citation.get("source"),
                    citation.get("title") or citation.get("text"),
                )
                if source:
                    sources.append(source)

    return _dedupe_sources(sources)


class EnhancedChatService:
    """Enhanced chat service with comprehensive API integration."""

    def __init__(self):
        # Fallback storage for when database fails
        self.fallback_conversations: Dict[str, List[Dict[str, Any]]] = {}
        self.fallback_conversation_metadata: Dict[str, Dict[str, Any]] = {}

        # Initialize tool handler with API client
        self.tool_handler = ChatToolHandler(chat_api_client)
        # Mirror key attributes so legacy tests still validate environment handling
        self.responses_api_key = chat_api_client.responses_api_key
    
    async def use_database_fallback(self, func_name: str, *args, **kwargs):
        """Try database operation, fall back to in-memory storage if it fails."""
        try:
            # Get the static method from ConversationService
            method = getattr(ConversationService, func_name)
            if asyncio.iscoroutinefunction(method):
                return await method(*args, **kwargs)
            else:
                return method(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Database {func_name} failed: {e}, using fallback")
            return None
    
    async def get_conversation_history(self, conversation_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Retrieve conversation history with fallback support."""
        # Try database first
        db_result = await self.use_database_fallback(
            "get_conversation_messages", conversation_id
        )
        
        if db_result:
            return db_result
        
        # Use fallback storage
        return self.fallback_conversations.get(conversation_id, [])
    
    async def save_message_to_conversation(
        self, 
        conversation_id: str, 
        user_id: str, 
        role: str, 
        content: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Save message with fallback support."""
        try:
            # Try database first
            db_result = await self.use_database_fallback(
                "add_message", 
                conversation_id, 
                role, 
                content, 
                metadata
            )
            
            if db_result:
                return True
        except Exception as e:
            logger.error(f"Database save failed: {e}")
        
        # Use fallback storage
        if conversation_id not in self.fallback_conversations:
            self.fallback_conversations[conversation_id] = []
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {}
        }
        
        self.fallback_conversations[conversation_id].append(message)
        return True
    
    async def create_conversation(self, user_id: str, title: Optional[str] = None) -> str:
        """Create new conversation with fallback support."""
        conversation_id = str(uuid.uuid4())
        
        try:
            # Try database first
            db_result = await self.use_database_fallback(
                "create_conversation", user_id, title
            )
            
            if db_result:
                return str(db_result.get("id", conversation_id))
        except Exception as e:
            logger.debug(f"Database create conversation failed: {e}")
        
        # Use fallback storage
        self.fallback_conversation_metadata[conversation_id] = {
            "user_id": user_id,
            "title": title or "New Conversation",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        self.fallback_conversations[conversation_id] = []
        return conversation_id
    
    async def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user preferences for chat configuration from database."""
        try:
            # Try to get preferences from database first
            from ..database import execute_query_one
            query = """
                SELECT default_model, system_prompt, settings
                FROM turfmapp_agent.user_preferences
                WHERE user_id = $1
            """
            db_prefs = await execute_query_one(query, user_id)

            if db_prefs:
                return {
                    "model": db_prefs.get("default_model", "gpt-4o"),
                    "system_prompt": db_prefs.get("system_prompt"),
                    "include_reasoning": False,
                    "text_format": "text",
                    "text_verbosity": "medium",
                    "reasoning_effort": "medium"
                }
        except Exception as e:
            logger.warning(f"Failed to load user preferences from database: {e}")

        # Return default preferences if database query fails
        return {
            "model": "gpt-4o",
            "include_reasoning": False,
            "text_format": "text",
            "text_verbosity": "medium",
            "reasoning_effort": "medium"
        }
    
    async def _handle_google_mcp_request(
        self,
        user_message: str,
        conversation_history: List[Dict[str, Any]],
        user_id: str,
        enabled_tools: Dict[str, bool],
        **kwargs
    ) -> Dict[str, Any]:
        """Handle Google MCP request using AI-driven tool selection - delegates to ChatToolHandler."""
        return await self.tool_handler.handle_google_mcp_request(
            user_message, conversation_history, user_id, enabled_tools, **kwargs
        )

    def _extract_gmail_search_query(self, user_message: str) -> str:
        """Extract search query from user message for Gmail search - delegates to ChatToolHandler."""
        return self.tool_handler.extract_gmail_search_query(user_message)

    async def handle_tool_calls(self, user_id: str, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Handle tool calls from the AI assistant with MCP integration - delegates to ChatToolHandler."""
        return await self.tool_handler.handle_tool_calls(user_id, tool_calls)
    
    async def call_responses_api(
        self,
        messages: List[Dict[str, Any]],
        model: str = "gpt-4o",
        include_reasoning: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Call the OpenAI Responses API with proper format - delegates to ChatApiClient."""
        return await chat_api_client.call_responses_api(
            messages, model, include_reasoning, **kwargs
        )

    async def call_claude_api(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        include_reasoning: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Call Anthropic Claude via the shared client with optional tool support."""
        if not anthropic_client.api_key:
            raise HTTPException(
                status_code=500,
                detail="Anthropic API key not configured; Claude models unavailable."
            )

        claude_tools = kwargs.get("tools") or []
        # Build the same consolidated instructions we provide to other providers
        instructions = build_system_instructions(
            tools=claude_tools,
            developer_instructions=kwargs.get("developer_instructions"),
            assistant_context=kwargs.get("assistant_context"),
        )

        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 4096)

        try:
            response = await anthropic_client.call_messages_api(
                messages,
                model=model,
                system=instructions or None,
                max_tokens=max_tokens,
                temperature=temperature,
                tools=claude_tools or None,
            )
        except Exception as error:
            logger.error("❌ Claude API call failed: %s", error)
            raise HTTPException(
                status_code=500,
                detail="Claude API request failed"
            ) from error

        content_items = response.get("content", [])
        text_blocks: List[str] = []
        claude_tool_inputs: Dict[str, Dict[str, Any]] = {}
        claude_tool_results: List[Dict[str, Any]] = []

        for block in content_items:
            if not isinstance(block, dict):
                continue

            block_type = block.get("type")
            if block_type == "text":
                text = block.get("text", "")
                if text:
                    text_blocks.append(text)
            elif block_type == "tool_use":
                tool_id = block.get("id")
                if tool_id:
                    claude_tool_inputs[tool_id] = {
                        "name": block.get("name"),
                        "args": block.get("input"),
                        "args_text": _serialise_args(block.get("input")),
                    }
            elif block_type == "tool_result":
                claude_tool_results.append(block)

        sources = _extract_sources_from_claude_response(response)
        claude_blocks = _build_blocks_from_tool_results(claude_tool_results, claude_tool_inputs)

        output_text = "\n\n".join(block for block in text_blocks if block)

        return {
            "provider": "anthropic",
            "output_text": output_text,
            "output": [],
            "raw_response": response,
            "content": response.get("content"),
            "usage": response.get("usage"),
            "sources": sources,
            "blocks": claude_blocks,
        }
    
    async def process_chat_request(
        self, 
        user_id: str, 
        message: str, 
        conversation_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Process a complete chat request with history and context."""
        # Get or create conversation
        if not conversation_id:
            # Generate title from user's first message (truncate to 50 chars)
            title = message[:50] + "..." if len(message) > 50 else message
            conversation_id = await self.create_conversation(user_id, title)
        
        # Get conversation history
        history = await self.get_conversation_history(conversation_id, user_id)

        # Get user preferences from database
        preferences = await self.get_user_preferences(user_id)
        logger.info(f"🔍 DEBUG: User preferences from DB: {preferences}")

        # Merge preferences with request parameters
        model = kwargs.get("model", preferences.get("model", "gpt-4o"))
        include_reasoning = kwargs.get("include_reasoning", preferences.get("include_reasoning", False))
        logger.info(f"🔍 DEBUG: Model from kwargs: {kwargs.get('model')}")
        logger.info(f"🔍 DEBUG: Model from preferences: {preferences.get('model')}")
        logger.info(f"🔍 DEBUG: Final model to use: {model}")
        logger.info(f"🔍 DEBUG: User ID: {user_id}")
        
        # Format messages for API with smart context management
        formatted_history = format_chat_history(history, max_context=20)
        
        # Add current user message
        current_message = {"role": "user", "content": message}
        all_messages = formatted_history + [current_message]
        
        # Save user message first
        await self.save_message_to_conversation(
            conversation_id, user_id, "user", message
        )
        
        raw_tools = kwargs.get("tools") or []
        expanded_tools: List[Dict[str, Any]] = []
        is_claude_model = model.startswith("claude-")

        for tool in raw_tools:
            if isinstance(tool, dict) and tool.get("type") == "google_mcp":
                enabled = tool.get("enabled_tools") or {}
                expanded_tools.extend(self.tool_handler.build_google_function_tools(enabled))
            else:
                expanded_tools.append(tool)

        tools_to_include = expanded_tools

        logger.info(
            "🚀 🚀 🚀 ROUTING CHAT REQUEST via %s model: %s 🚀 🚀 🚀",
            "Claude" if is_claude_model else "OpenAI",
            model,
        )
        logger.info(f"🔍 DEBUG: is_claude_model = {is_claude_model}")
        logger.info(f"🔍 DEBUG: model value = '{model}'")
        logger.info(f"🔍 DEBUG: model.startswith('claude-') = {model.startswith('claude-')}")

        try:
            if is_claude_model:
                api_response = await self.call_claude_api(
                    messages=all_messages,
                    model=model,
                    include_reasoning=include_reasoning,
                    tools=tools_to_include,
                    **{k: v for k, v in kwargs.items() if k not in ["model", "include_reasoning", "tools"]}
                )
            else:
                api_response = await self.call_responses_api(
                    messages=all_messages,
                    model=model,
                    include_reasoning=include_reasoning,
                    tools=tools_to_include,
                    **{k: v for k, v in kwargs.items() if k not in ["model", "include_reasoning", "tools"]}
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ AI model error: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to call AI model: {str(e)}"
            ) from e

        try:
            # Extract assistant response from model output
            assistant_content = ""
            reasoning = None
            sources = list(api_response.get("sources", [])) if isinstance(api_response, dict) else []
            message_blocks: List[Dict[str, Any]] = []
            if isinstance(api_response, dict):
                initial_blocks = api_response.get("blocks")
                if isinstance(initial_blocks, list):
                    message_blocks.extend(initial_blocks)
            
            # Parse API output with debugging
            logger.warning("🔍 API Response for model %s: %s", model, api_response)

            # Check if there are any tool calls in the response
            if "tool_calls" in api_response:
                logger.warning("🔧 Tool calls found in response: %s", api_response["tool_calls"])
            else:
                logger.warning("🔧 No tool calls found in response")

            # Check the output structure for function calls (OpenAI format)
            output_items = api_response.get("output", [])
            logger.warning(f"🔧 Output items: {len(output_items) if output_items else 0}")

            # Also check content array for Claude's tool_use format
            content_items = api_response.get("content", [])
            logger.warning(f"🔧 Content items: {len(content_items) if content_items else 0}")

            # Handle function calls from the API response (OpenAI format)
            function_calls = []
            tool_results: List[Dict[str, Any]] = []
            tool_call_inputs: Dict[str, Dict[str, Any]] = {}
            openai_function_calls = []  # Track OpenAI function calls for summarization

            for i, item in enumerate(output_items):
                if isinstance(item, dict):
                    item_type = item.get("type")
                    logger.warning(f"🔧 Output item {i}: type={item_type}")
                    if item_type == "function_call":
                        logger.warning(f"🔧 Function call found: {item}")
                        function_calls.append(item)

                        # CRITICAL: Execute the tool if it's a completed function call
                        status = item.get("status")
                        logger.warning(f"🔧 Function call status: {status}")
                        if status == "completed":
                            tool_name = item.get("name")
                            arguments = item.get("arguments")
                            call_id = item.get("call_id")

                            logger.warning(f"🔧 Status is 'completed' - will execute tool: {tool_name} with args: {arguments}")

                            # Parse arguments if they're a string
                            if isinstance(arguments, str):
                                try:
                                    parsed_args = json.loads(arguments)
                                except (TypeError, ValueError):
                                    parsed_args = {}
                            else:
                                parsed_args = arguments or {}

                            # Execute the tool via handle_tool_calls to get actual data
                            try:
                                tool_call_format = [{
                                    "id": call_id,
                                    "type": "function",
                                    "function": {
                                        "name": tool_name,
                                        "arguments": json.dumps(parsed_args) if not isinstance(parsed_args, str) else parsed_args
                                    }
                                }]

                                executed_results = await self.handle_tool_calls(user_id, tool_call_format)
                                logger.warning(f"🔧 Tool execution results: {executed_results}")

                                # Track this for AI summarization
                                openai_function_calls.append({
                                    "tool_name": tool_name,
                                    "args": parsed_args,
                                    "call_id": call_id,
                                    "results": executed_results
                                })
                                logger.warning(f"🔧 Added to openai_function_calls, new count: {len(openai_function_calls)}")

                                # Add results to tool_results for processing
                                for result in executed_results:
                                    tool_results.append(result)

                                # Track tool call inputs
                                tool_call_inputs[call_id] = {
                                    "name": tool_name,
                                    "args": parsed_args,
                                    "args_text": _serialise_args(parsed_args),
                                }

                            except Exception as tool_error:
                                logger.error(f"❌ Tool execution failed: {tool_error}")
                                tool_results.append({
                                    "tool_call_id": call_id,
                                    "content": f"Error executing {tool_name}: {str(tool_error)}"
                                })
                    elif item_type == "tool_call":
                        logger.debug(f"🔧 Tool call found: {item}")
                        function_calls.append(item)
                        call_id = item.get("id") or item.get("tool_call_id") or item.get("call_id")
                        if call_id:
                            arguments = item.get("arguments") or item.get("input")
                            parsed_args = None
                            if isinstance(arguments, str):
                                try:
                                    parsed_args = json.loads(arguments)
                                except (TypeError, ValueError):
                                    parsed_args = None
                            tool_call_inputs[call_id] = {
                                "name": item.get("name"),
                                "args": parsed_args if parsed_args is not None else arguments,
                                "args_text": _serialise_args(parsed_args if parsed_args is not None else arguments),
                            }
                    elif item_type == "tool_result":
                        logger.debug(f"🔧 Tool result found: {item}")
                        tool_results.append(item)
                    elif item_type == "message":
                        content = item.get("content", [])
                        logger.debug(f"🔧 Message content: {content}")
                        
                        # Extract text from message content and collect annotations
                        if content and isinstance(content, list):
                            for content_item in content:
                                if isinstance(content_item, dict) and content_item.get("type") == "output_text":
                                    text = content_item.get("text", "")
                                    if text:
                                        assistant_content = text
                                        logger.debug(f"🔧 Extracted message text: {text[:100]}...")
                                        
                                        # Extract sources from annotations (URL citations)
                                        annotations = content_item.get("annotations", [])
                                        if annotations:
                                            logger.debug(f"🔧 Found {len(annotations)} annotations")
                                            for annotation in annotations:
                                                if annotation.get("type") == "url_citation":
                                                    source = _build_source_entry(
                                                        annotation.get("url", ""),
                                                        annotation.get("title"),
                                                    )
                                                    if source:
                                                        sources.append(source)
                                                        logger.debug(f"🔧 Added annotated source: {source['site']}")
                                        break

            # Process Claude's tool_use format from content array
            claude_tool_uses = []
            for i, item in enumerate(content_items):
                if isinstance(item, dict):
                    item_type = item.get("type")
                    logger.warning(f"🔧 Content item {i}: type={item_type}")

                    if item_type == "tool_use":
                        logger.warning(f"🔧 Claude tool_use found: {item}")
                        claude_tool_uses.append(item)

            # If Claude requested tools, execute them and let the selected model summarize
            if claude_tool_uses:
                logger.warning(f"🔧 Claude requested {len(claude_tool_uses)} tools - executing and using {model} for summarization")

                # Execute all tool requests and collect raw data
                collected_tool_data = []
                for tool_use in claude_tool_uses:
                    tool_name = tool_use.get("name")
                    tool_input = tool_use.get("input", {})
                    tool_id = tool_use.get("id")

                    logger.warning(f"🔧 Executing tool: {tool_name} with input: {tool_input}")

                    try:
                        # Convert to standard format
                        tool_call_format = [{
                            "id": tool_id,
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": json.dumps(tool_input) if isinstance(tool_input, dict) else str(tool_input)
                            }
                        }]

                        executed_results = await self.handle_tool_calls(user_id, tool_call_format)
                        logger.warning(f"🔧 Tool execution results: {executed_results}")

                        # Extract raw MCP data for AI summarization
                        for result in executed_results:
                            result_data = result.get("result", {})
                            # Get the raw response from MCP (this is pre-formatted by MCP)
                            raw_data = result_data.get("response") or result_data.get("content") or json.dumps(result_data)

                            service_type = "Gmail" if tool_name.startswith('gmail') else \
                                         "Calendar" if tool_name.startswith('calendar') else \
                                         "Drive" if tool_name.startswith('drive') else "Unknown"

                            collected_tool_data.append({
                                "service": service_type,
                                "tool": tool_name,
                                "data": raw_data
                            })

                            # Track for metadata
                            tool_call_inputs[tool_id] = {
                                "name": tool_name,
                                "args": tool_input,
                                "args_text": _serialise_args(tool_input),
                            }
                            tool_results.append(result)

                    except Exception as tool_error:
                        logger.error(f"❌ Tool execution failed: {tool_error}")
                        collected_tool_data.append({
                            "service": "Error",
                            "tool": tool_name,
                            "data": f"Error: {str(tool_error)}"
                        })

                # Use the selected model (Claude in this case) to analyze and summarize
                if collected_tool_data:
                    logger.warning(f"🔧 Using {model} to summarize {len(collected_tool_data)} tool results")

                    analysis_prompt = f"""User Question: {message}

Retrieved Data from Google Services:
{chr(10).join([f"{item['service']}: {item['data']}" for item in collected_tool_data])}

Please analyze the retrieved data and provide a helpful, concise answer to the user's question. Focus on:
1. Directly answering what the user asked
2. Summarizing key information rather than listing raw data
3. Being conversational and helpful
4. Highlighting important dates, names, or action items if relevant

CRITICAL: When URLs or links are provided in the data, you MUST include them EXACTLY as provided. NEVER truncate, shorten, or summarize URLs. Always show complete clickable links.

Respond as if you're having a natural conversation with the user."""

                    # Call the selected model for analysis (Claude in this path)
                    analysis_messages = [
                        {"role": "user", "content": f"{analysis_prompt}\n\nPlease analyze and summarize this information to answer the user's question."}
                    ]

                    try:
                        if is_claude_model:
                            analysis_result = await self.call_claude_api(
                                messages=analysis_messages,
                                model=model,
                                **{k: v for k, v in kwargs.items() if k not in ["model", "tools"]}
                            )
                        else:
                            analysis_result = await self.call_responses_api(
                                messages=analysis_messages,
                                model=model,
                                **{k: v for k, v in kwargs.items() if k not in ["model", "tools"]}
                            )

                        logger.warning(f"🔧 {model} analysis result: {analysis_result}")

                        # Extract the AI summary from the nested structure
                        assistant_content = analysis_result.get("output_text", "")

                        # If output_text is empty, extract from output array (message content)
                        if not assistant_content:
                            output_array = analysis_result.get("output", [])
                            for out_item in output_array:
                                if isinstance(out_item, dict) and out_item.get("type") == "message":
                                    content_list = out_item.get("content", [])
                                    for content_item in content_list:
                                        if isinstance(content_item, dict) and content_item.get("type") == "output_text":
                                            text = content_item.get("text", "")
                                            if text:
                                                assistant_content = text
                                                break
                                    if assistant_content:
                                        break

                        logger.warning(f"🔧 {model} final summary: {assistant_content[:200] if assistant_content else 'STILL EMPTY'}")

                    except Exception as e:
                        logger.error(f"❌ AI summarization failed: {e}")
                        # Fallback to raw tool results
                        assistant_content = "\n\n".join([
                            f"📧 **{item['service']}**: {item['data']}" for item in collected_tool_data
                        ])

            # Debug: Check OpenAI function calls status
            logger.warning(f"🔧 OpenAI function calls count: {len(openai_function_calls)}, is_claude_model: {is_claude_model}")

            # If OpenAI requested tools, apply same summarization logic
            if openai_function_calls and not is_claude_model:
                logger.warning(f"🔧 OpenAI executed {len(openai_function_calls)} tools - using {model} for summarization")

                # Collect raw data from OpenAI tool executions
                collected_tool_data = []
                for func_call in openai_function_calls:
                    tool_name = func_call["tool_name"]
                    for result in func_call["results"]:
                        result_data = result.get("result", {})
                        raw_data = result_data.get("response") or result_data.get("content") or json.dumps(result_data)

                        service_type = "Gmail" if tool_name.startswith('gmail') else \
                                     "Calendar" if tool_name.startswith('calendar') else \
                                     "Drive" if tool_name.startswith('drive') else "Unknown"

                        collected_tool_data.append({
                            "service": service_type,
                            "tool": tool_name,
                            "data": raw_data
                        })

                # Use OpenAI to summarize
                if collected_tool_data:
                    logger.warning(f"🔧 Using {model} to summarize {len(collected_tool_data)} tool results")

                    analysis_prompt = f"""User Question: {message}

Retrieved Data from Google Services:
{chr(10).join([f"{item['service']}: {item['data']}" for item in collected_tool_data])}

Please analyze the retrieved data and provide a helpful, concise answer to the user's question. Focus on:
1. Directly answering what the user asked
2. Summarizing key information rather than listing raw data
3. Being conversational and helpful
4. Highlighting important dates, names, or action items if relevant

CRITICAL: When URLs or links are provided in the data, you MUST include them EXACTLY as provided. NEVER truncate, shorten, or summarize URLs. Always show complete clickable links.

Respond as if you're having a natural conversation with the user."""

                    analysis_messages = [
                        {"role": "user", "content": f"{analysis_prompt}\n\nPlease analyze and summarize this information to answer the user's question."}
                    ]

                    try:
                        analysis_result = await self.call_responses_api(
                            messages=analysis_messages,
                            model=model,
                            **{k: v for k, v in kwargs.items() if k not in ["model", "tools"]}
                        )

                        logger.warning(f"🔧 {model} analysis result: {analysis_result}")

                        # Extract the AI summary from the nested structure
                        assistant_content = analysis_result.get("output_text", "")

                        # If output_text is empty, extract from output array (message content)
                        if not assistant_content:
                            output_array = analysis_result.get("output", [])
                            for out_item in output_array:
                                if isinstance(out_item, dict) and out_item.get("type") == "message":
                                    content_list = out_item.get("content", [])
                                    for content_item in content_list:
                                        if isinstance(content_item, dict) and content_item.get("type") == "output_text":
                                            text = content_item.get("text", "")
                                            if text:
                                                assistant_content = text
                                                break
                                    if assistant_content:
                                        break

                        logger.warning(f"🔧 {model} final summary: {assistant_content[:200] if assistant_content else 'STILL EMPTY'}")

                    except Exception as e:
                        logger.error(f"❌ AI summarization failed: {e}")
                        # Fallback to raw tool results
                        assistant_content = "\n\n".join([
                            f"📧 **{item['service']}**: {item['data']}" for item in collected_tool_data
                        ])

            # Flag to skip raw extraction if tools were already summarized by AI
            tools_already_summarized = bool((claude_tool_uses or openai_function_calls) and assistant_content)

            if tool_results:
                tool_blocks = _build_blocks_from_tool_results(tool_results, tool_call_inputs)
                if tool_blocks:
                    message_blocks.extend(tool_blocks)

                # Extract text content from tool results (skip if already summarized by AI)
                if not tools_already_summarized:
                    for tool_item in tool_results:
                        # Try to extract response text from tool result
                        if isinstance(tool_item, dict):
                            # Handle nested result structure from handle_tool_calls
                            result_data = tool_item.get("result")
                            if isinstance(result_data, dict):
                                # Extract from nested result.response or result.content
                                response_text = result_data.get("response") or result_data.get("content") or result_data.get("output")
                                if response_text and isinstance(response_text, str):
                                    assistant_content += ("\n\n" if assistant_content else "") + response_text
                                    logger.warning(f"🔧 Extracted text from nested result: {response_text[:200]}")
                                    continue

                            # Check various content fields at top level
                            content = tool_item.get("content") or tool_item.get("response") or tool_item.get("output")
                            if content:
                                if isinstance(content, str) and content:
                                    assistant_content += ("\n\n" if assistant_content else "") + content
                                    logger.warning(f"🔧 Extracted text from tool result: {content[:200]}")
                                elif isinstance(content, list):
                                    for item in content:
                                        if isinstance(item, dict) and item.get("type") == "text":
                                            text = item.get("text", "")
                                            if text:
                                                assistant_content += ("\n\n" if assistant_content else "") + text
                                                logger.warning(f"🔧 Extracted text from tool result list: {text[:200]}")

                # Always extract sources from tool results
                for tool_item in tool_results:
                    extracted_sources = _extract_sources_from_tool_result(tool_item)
                    if extracted_sources:
                        logger.debug(f"🔧 Extracted {len(extracted_sources)} sources from tool result")
                        sources.extend(extracted_sources)

            # Only get default response text if we haven't set assistant_content from function calls or tool results
            if not assistant_content:
                assistant_content = self.stringify_text(api_response.get("output_text") or "")
                logger.warning(f"🔍 Using output_text, got: {assistant_content[:200] if assistant_content else 'EMPTY'}")

            # Extract sources from URLs in text content (like original repo)
            if isinstance(assistant_content, str) and assistant_content and not sources:
                text_sources = _extract_sources_from_text(assistant_content)
                if text_sources:
                    logger.warning(f"🔍 Extracted {len(text_sources)} sources from assistant text")
                    sources.extend(text_sources)

            # Handle incomplete responses (like GPT-5-mini hitting token limit)
            status = api_response.get("status")
            if status == "incomplete":
                assistant_content += "\n\n*[Response was truncated due to length limits]*"

            # Extract reasoning if available
            if include_reasoning and "reasoning" in api_response:
                reasoning = api_response["reasoning"]

            if sources:
                sources = _dedupe_sources(sources)
            if message_blocks:
                message_blocks = _dedupe_blocks(message_blocks)

            logger.warning(f"🔍 Final assistant content length: {len(assistant_content) if assistant_content else 0}")
            
        except Exception as e:
            logger.error(f"❌ API call failed: {e}")
            assistant_content = f"I apologize, but I encountered an error while processing your request: {str(e)}"
            reasoning = None
            sources = []
            function_calls = []
            message_blocks = []
    
        # Save assistant message
        await self.save_message_to_conversation(
            conversation_id,
            user_id,
            "assistant",
            assistant_content,
            {
                "model": model,
                "provider": "anthropic" if is_claude_model else "openai",
                "include_reasoning": include_reasoning,
                "original_api_used": not is_claude_model,
                "sources": sources,
                "function_calls": function_calls,
                "tool_calls": function_calls,
                "blocks": message_blocks,
            },
        )
        
        # Create response messages
        user_message = {
            "id": str(uuid.uuid4()),
            "role": "user", 
            "content": message,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        assistant_message = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": assistant_content,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        return {
            "conversation_id": conversation_id,
            "user_message": user_message,
            "assistant_message": assistant_message,
            "reasoning": reasoning,
            "sources": sources,
            "blocks": message_blocks,
            "model": model,
            "provider": "anthropic" if is_claude_model else "openai"
        }
    
    def stringify_text(self, text) -> str:
        """Helper method to stringify text."""
        if isinstance(text, str):
            return text
        elif isinstance(text, list):
            return "".join(str(item) for item in text)
        return str(text)
    
    async def get_conversation_list(self, user_id: str) -> List[Dict[str, Any]]:
        """Get list of conversations for a user."""
        try:
            # Try database first
            db_result = await self.use_database_fallback(
                "get_user_conversations", user_id
            )
            
            if db_result:
                return db_result
        except Exception as e:
            logger.debug(f"Database get conversations failed: {e}")
        
        # Use fallback storage
        conversations = []
        for conv_id, metadata in self.fallback_conversation_metadata.items():
            if metadata.get("user_id") == user_id:
                conversations.append({
                    "conversation_id": conv_id,
                    "title": metadata.get("title", "Untitled"),
                    "created_at": metadata.get("created_at"),
                    "updated_at": metadata.get("updated_at"),
                    "message_count": len(self.fallback_conversations.get(conv_id, []))
                })
        
        return conversations
    
    async def delete_conversation(self, conversation_id: str, user_id: str) -> bool:
        """Delete a conversation."""
        try:
            # Try database first
            db_result = await self.use_database_fallback(
                "delete_conversation", conversation_id
            )
            
            if db_result:
                return True
        except Exception as e:
            logger.debug(f"Database delete conversation failed: {e}")
        
        # Use fallback storage
        if conversation_id in self.fallback_conversations:
            # Verify ownership
            metadata = self.fallback_conversation_metadata.get(conversation_id, {})
            if metadata.get("user_id") == user_id:
                del self.fallback_conversations[conversation_id]
                del self.fallback_conversation_metadata[conversation_id]
                return True
        
        return False

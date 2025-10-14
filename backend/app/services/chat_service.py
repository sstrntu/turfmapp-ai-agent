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

        sources = _extract_sources_from_claude_response(response)

        text_blocks = [
            block.get("text", "")
            for block in response.get("content", [])
            if isinstance(block, dict) and block.get("type") == "text"
        ]

        output_text = "\n\n".join(block for block in text_blocks if block)

        return {
            "provider": "anthropic",
            "output_text": output_text,
            "output": [],
            "raw_response": response,
            "content": response.get("content"),
            "usage": response.get("usage"),
            "sources": sources,
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

        for tool in raw_tools:
            if isinstance(tool, dict) and tool.get("type") == "google_mcp":
                enabled = tool.get("enabled_tools") or {}
                expanded_tools.extend(self.tool_handler.build_google_function_tools(enabled))
            else:
                expanded_tools.append(tool)

        tools_to_include = expanded_tools
        is_claude_model = model.startswith("claude-")

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
            
            # Parse API output with debugging
            logger.debug("🔍 API Response for model %s: %s", model, api_response)
            
            # Check if there are any tool calls in the response
            if "tool_calls" in api_response:
                logger.debug("🔧 Tool calls found in response: %s", api_response["tool_calls"])
            else:
                logger.debug("🔧 No tool calls found in response")
            
            # Check the output structure for function calls
            output_items = api_response.get("output", [])
            logger.debug(f"🔧 Output items: {len(output_items) if output_items else 0}")
            
            # Handle function calls from the API response (original repo logic)
            function_calls = []
            tool_results: List[Dict[str, Any]] = []
            for i, item in enumerate(output_items):
                if isinstance(item, dict):
                    item_type = item.get("type")
                    logger.debug(f"🔧 Output item {i}: type={item_type}")
                    if item_type == "function_call":
                        logger.debug(f"🔧 Function call found: {item}")
                        function_calls.append(item)
                    elif item_type == "tool_call":
                        logger.debug(f"🔧 Tool call found: {item}")
                        function_calls.append(item)
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

            for tool_item in tool_results:
                extracted_sources = _extract_sources_from_tool_result(tool_item)
                if extracted_sources:
                    logger.debug(f"🔧 Extracted {len(extracted_sources)} sources from tool result")
                    sources.extend(extracted_sources)
            
            # Only get default response text if we haven't set assistant_content from function calls
            if not assistant_content:
                assistant_content = self.stringify_text(api_response.get("output_text") or "")
            
            # Extract sources from URLs in text content (like original repo)
            if isinstance(assistant_content, str) and assistant_content and not sources:
                text_sources = _extract_sources_from_text(assistant_content)
                if text_sources:
                    logger.debug(f"🔍 Extracted {len(text_sources)} sources from assistant text")
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
            
            logger.debug(f"🔍 Final assistant content length: {len(assistant_content) if assistant_content else 0}")
            
        except Exception as e:
            logger.error(f"❌ API call failed: {e}")
            assistant_content = f"I apologize, but I encountered an error while processing your request: {str(e)}"
            reasoning = None
            sources = []
            function_calls = []
        
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

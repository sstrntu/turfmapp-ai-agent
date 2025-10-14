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

import os
import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid
import httpx

from ..database import ConversationService, UserService
from ..utils.chat_utils import stringify_text, extract_sources_from_response, format_chat_history
from ..api.v1.preferences import user_preferences
from .tool_manager import tool_manager
from .mcp_client import google_mcp_client, get_all_google_tools
from .chat_api_client import chat_api_client
from .chat_tool_handler import ChatToolHandler

# Configure logger
logger = logging.getLogger(__name__)


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
    
    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user preferences for chat configuration."""
        return user_preferences.get(user_id, {
            "model": "gpt-4o",
            "include_reasoning": False,
            "text_format": "text",
            "text_verbosity": "medium",
            "reasoning_effort": "medium"
        })
    
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
        
        # Get user preferences
        preferences = self.get_user_preferences(user_id)
        
        # Merge preferences with request parameters
        model = kwargs.get("model", preferences.get("model", "gpt-4o"))
        include_reasoning = kwargs.get("include_reasoning", preferences.get("include_reasoning", False))
        
        # Format messages for API with smart context management
        formatted_history = format_chat_history(history, max_context=20)
        
        # Add current user message
        current_message = {"role": "user", "content": message}
        all_messages = formatted_history + [current_message]
        
        # Save user message first
        await self.save_message_to_conversation(
            conversation_id, user_id, "user", message
        )
        
        # Check if Google MCP tools are explicitly requested
        google_mcp_tools = None
        logger.debug(f"🔍 kwargs keys: {list(kwargs.keys())}")
        logger.debug(f"🔍 tools in kwargs: {'tools' in kwargs}")
        if 'tools' in kwargs:
            logger.debug(f"🔍 tools content: {kwargs['tools']}")

        if 'tools' in kwargs and kwargs['tools']:
            for tool in kwargs['tools']:
                logger.debug(f"🔍 Processing tool: {tool}")
                if tool.get('type') == 'google_mcp':
                    google_mcp_tools = tool.get('enabled_tools', {})
                    logger.debug(f"🔍 Found Google MCP tools: {google_mcp_tools}")
                    break

        logger.debug(f"🔍 Final google_mcp_tools: {google_mcp_tools}")
        
        if google_mcp_tools and any(google_mcp_tools.values()):
            logger.debug(f"🔧 Google MCP tools explicitly requested: {google_mcp_tools}")
            
            # Handle Google MCP tools directly
            try:
                mcp_result = await self._handle_google_mcp_request(
                    user_message=message,
                    conversation_history=formatted_history,
                    user_id=user_id,
                    enabled_tools=google_mcp_tools,
                    **kwargs
                )
                
                if mcp_result.get("success"):
                    assistant_content = mcp_result.get("response", "")
                    
                    # Save assistant message
                    await self.save_message_to_conversation(
                        conversation_id, user_id, "assistant", assistant_content,
                        {
                            "google_mcp_used": True,
                            "enabled_tools": google_mcp_tools,
                            "tools_used": mcp_result.get("tools_used", []),
                            "model": model
                        }
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
                        "reasoning": None,
                        "sources": mcp_result.get("sources", [])
                    }
                else:
                    logger.warning("❌ Google MCP failed, falling back to original behavior")
            except Exception as e:
                logger.error(f"❌ Google MCP error: {e}, falling back to original behavior")

        # Use original behavior - direct API call like the original repo
        logger.info("🚀 Using original behavior - calling Responses API directly")
        
        # Prepare tools for API call (from original repo logic - use web search tools if requested)
        tools_to_include = kwargs.get("tools", [])
        
        # Call API directly (original repo behavior)
        try:
            api_response = await self.call_responses_api(
                messages=all_messages,
                model=model,
                include_reasoning=include_reasoning,
                tools=tools_to_include,
                **{k: v for k, v in kwargs.items() if k not in ["model", "include_reasoning", "tools"]}
            )
            
            # Extract assistant response from Responses API format (original repo logic)
            assistant_content = ""
            reasoning = None
            sources = []  # Initialize sources list
            
            # Parse Responses API output with debugging for GPT-5-mini
            logger.debug(f"🔍 API Response for model {model}:", api_response)
            
            # Check if there are any tool calls in the response
            if "tool_calls" in api_response:
                logger.debug(f"🔧 Tool calls found in response: {api_response['tool_calls']}")
            else:
                logger.debug(f"🔧 No tool calls found in response")
            
            # Check the output structure for function calls
            output_items = api_response.get("output", [])
            logger.debug(f"🔧 Output items: {len(output_items) if output_items else 0}")
            
            # Handle function calls from the API response (original repo logic)
            function_calls = []
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
                                                    url = annotation.get("url", "")
                                                    title = annotation.get("title", "")
                                                    if url:
                                                        # Extract domain for favicon
                                                        from urllib.parse import urlparse
                                                        try:
                                                            parsed = urlparse(url)
                                                            domain = parsed.netloc
                                                            
                                                            source = {
                                                                "url": url,
                                                                "title": title if title else domain,
                                                                "site": domain,
                                                                "favicon": f"https://www.google.com/s2/favicons?domain={domain}&sz=64"
                                                            }
                                                            sources.append(source)
                                                            logger.debug(f"🔧 Added source: {domain}")
                                                        except Exception as e:
                                                            logger.error(f"❌ Failed to parse URL {url}: {e}")
                                        break
            
            # Only get default response text if we haven't set assistant_content from function calls
            if not assistant_content:
                assistant_content = self.stringify_text(api_response.get("output_text") or "")
            
            # Extract sources from URLs in text content (like original repo)
            if isinstance(assistant_content, str) and assistant_content and not sources:
                import re
                from urllib.parse import urlparse
                
                # Find URLs in the response text
                raw_urls = re.findall(r"https?://[^\s)]+", assistant_content)
                logger.debug(f"🔍 Found {len(raw_urls)} URLs in response text")
                seen = set()
                for u in raw_urls:
                    cleaned = u.rstrip('.,);]')
                    if cleaned in seen:
                        continue
                    seen.add(cleaned)
                    try:
                        parsed = urlparse(cleaned)
                        if parsed.scheme in {"http", "https"} and parsed.netloc:
                            source = {
                                "url": cleaned,
                                "title": parsed.netloc,
                                "site": parsed.netloc,
                                "favicon": f"https://www.google.com/s2/favicons?domain={parsed.netloc}&sz=64"
                            }
                            sources.append(source)
                            logger.debug(f"🔧 Added URL source: {parsed.netloc}")
                    except Exception as e:
                        logger.error(f"❌ Failed to parse URL {cleaned}: {e}")
                        continue
                
                # Limit sources
                if sources:
                    sources = sources[:8]
                    logger.info(f"✅ Extracted {len(sources)} sources from URLs")
            
            # Handle incomplete responses (like GPT-5-mini hitting token limit)
            status = api_response.get("status")
            if status == "incomplete":
                assistant_content += "\n\n*[Response was truncated due to length limits]*"
            
            # Extract reasoning if available
            if include_reasoning and "reasoning" in api_response:
                reasoning = api_response["reasoning"]
            
            logger.debug(f"🔍 Final assistant content length: {len(assistant_content) if assistant_content else 0}")
            
        except Exception as e:
            logger.error(f"❌ API call failed: {e}")
            assistant_content = f"I apologize, but I encountered an error while processing your request: {str(e)}"
            reasoning = None
            sources = []
        
        # Save assistant message
        await self.save_message_to_conversation(
            conversation_id, user_id, "assistant", assistant_content,
            {
                "model": model,
                "include_reasoning": include_reasoning,
                "original_api_used": True,
                "sources": sources
            }
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
            "sources": sources
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

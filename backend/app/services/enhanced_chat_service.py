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
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import httpx

from ..database import ConversationService, UserService
from ..utils.chat_utils import stringify_text, extract_sources_from_response, format_chat_history
from ..api.v1.preferences import user_preferences


class EnhancedChatService:
    """Enhanced chat service with comprehensive API integration."""
    
    def __init__(self):
        self.responses_api_key = os.getenv("OPENAI_API_KEY", "")
        self.responses_base_url = "https://api.openai.com/v1/responses"
        
        # Fallback storage for when database fails
        self.fallback_conversations: Dict[str, List[Dict[str, Any]]] = {}
        self.fallback_conversation_metadata: Dict[str, Dict[str, Any]] = {}
    
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
            print(f"Database {func_name} failed: {e}, using fallback")
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
            print(f"Database save failed: {e}")
        
        # Use fallback storage
        if conversation_id not in self.fallback_conversations:
            self.fallback_conversations[conversation_id] = []
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
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
            print(f"Database create conversation failed: {e}")
        
        # Use fallback storage
        self.fallback_conversation_metadata[conversation_id] = {
            "user_id": user_id,
            "title": title or "New Conversation",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
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
    
    async def call_responses_api(
        self, 
        messages: List[Dict[str, Any]], 
        model: str = "gpt-4o",
        include_reasoning: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Call the OpenAI Responses API with proper format."""
        headers = {
            "Authorization": f"Bearer {self.responses_api_key}",
            "Content-Type": "application/json"
        }
        
        # Convert messages to conversation context string (Responses API format)
        conversation_context = ""
        for msg in messages:
            role = msg["role"].title()
            conversation_context += f"{role}: {msg['content']}\n\n"
        
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
        
        # Handle tools properly
        if "tools" in kwargs and kwargs["tools"]:
            tools = kwargs["tools"]
            # Filter out invalid string-based tools
            if isinstance(tools, list) and tools:
                if isinstance(tools[0], str):
                    print(f"⚠️ Removing invalid tools format: {tools}")
                else:
                    payload["tools"] = tools[:5]  # Limit to 5 tools
                    payload["tool_choice"] = kwargs.get("tool_choice", "auto")
                    payload["parallel_tool_calls"] = True
        
        # Add instructions for additional context
        instructions = []
        if "developer_instructions" in kwargs and kwargs["developer_instructions"]:
            instructions.append(kwargs["developer_instructions"])
        if "assistant_context" in kwargs and kwargs["assistant_context"]:
            instructions.append(kwargs["assistant_context"])
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
        
        # Format messages for API
        formatted_history = format_chat_history(history, max_context=10)
        
        # Add current user message
        current_message = {"role": "user", "content": message}
        all_messages = formatted_history + [current_message]
        
        # Save user message first
        await self.save_message_to_conversation(
            conversation_id, user_id, "user", message
        )
        
        # Call API
        try:
            api_response = await self.call_responses_api(
                messages=all_messages,
                model=model,
                include_reasoning=include_reasoning,
                **{k: v for k, v in kwargs.items() if k not in ["model", "include_reasoning"]}
            )
            
            # Extract assistant response from Responses API format
            assistant_content = ""
            reasoning = None
            
            # Parse Responses API output with debugging for GPT-5-mini
            print(f"🔍 API Response for model {model}:", api_response)
            
            assistant_content = stringify_text(api_response.get("output_text") or "")
            
            # Handle incomplete responses (like GPT-5-mini hitting token limit)
            status = api_response.get("status")
            if status == "incomplete":
                incomplete_reason = api_response.get("incomplete_details", {}).get("reason", "unknown")
                print(f"⚠️ Incomplete response for {model}: {incomplete_reason}")
                
                if incomplete_reason == "max_output_tokens":
                    # Try to extract partial content from the output array
                    output_items = api_response.get("output", [])
                    if isinstance(output_items, list):
                        # Look for any text content in the output items
                        text_parts = []
                        web_searches = []
                        
                        for item in output_items:
                            if not isinstance(item, dict):
                                continue
                            
                            item_type = item.get("type")
                            if item_type == "output_text":
                                text_parts.append(stringify_text(item.get("text", "")))
                            elif item_type == "web_search_call" and item.get("status") == "completed":
                                # Extract search query to show what was being researched
                                query = item.get("action", {}).get("query", "")
                                if query:
                                    web_searches.append(query)
                        
                        if text_parts:
                            assistant_content = "".join(text_parts)
                        elif web_searches:
                            # If no text but web searches were performed, create a helpful message
                            assistant_content = f"I was researching your question about: {', '.join(web_searches[:3])}... but my response was cut off due to length. Please try asking a more specific question."
            
            if not assistant_content:
                # Try alternative response formats for different models
                output_items = api_response.get("output", [])
                
                # GPT-5-mini might use different response format
                if model == "gpt-5-mini" and not output_items:
                    # Check for choices format (similar to chat completions)
                    choices = api_response.get("choices", [])
                    if choices and isinstance(choices, list):
                        first_choice = choices[0]
                        if isinstance(first_choice, dict):
                            # Try message.content format
                            message = first_choice.get("message", {})
                            if isinstance(message, dict):
                                assistant_content = stringify_text(message.get("content", ""))
                            # Try text format
                            if not assistant_content:
                                assistant_content = stringify_text(first_choice.get("text", ""))
                
                # Standard output parsing for other models
                if not assistant_content and isinstance(output_items, list):
                    parts = []
                    for item in output_items:
                        if not isinstance(item, dict):
                            continue
                        item_type = item.get("type")
                        if item_type == "output_text":
                            parts.append(stringify_text(item.get("text")))
                            continue
                        if item_type == "message":
                            for block in item.get("content", []) or []:
                                if not isinstance(block, dict):
                                    continue
                                block_type = block.get("type")
                                if block_type == "output_text":
                                    parts.append(stringify_text(block.get("text")))
                    assistant_content = "".join(parts)
            
            # Extract reasoning if available (from working version)
            if include_reasoning:
                reasoning_data = api_response.get("reasoning", {})
                if isinstance(reasoning_data, dict):
                    reasoning = reasoning_data.get("summary", "")
            
            # Ensure content is not empty
            if not assistant_content:
                assistant_content = "I received your message but couldn't generate a proper response. Please try again."
            else:
                assistant_content = stringify_text(assistant_content)
            
            # Extract sources from content (URLs) - restored from working version
            sources = []
            if isinstance(assistant_content, str) and assistant_content:
                import re
                from urllib.parse import urlparse
                
                raw_urls = re.findall(r"https?://[^\s)]+", assistant_content)
                print(f"🔍 Found {len(raw_urls)} URLs in content")
                seen = set()
                for u in raw_urls:
                    cleaned = u.rstrip('.,);]')
                    if cleaned in seen:
                        continue
                    seen.add(cleaned)
                    try:
                        parsed = urlparse(cleaned)
                        if parsed.scheme in {"http", "https"} and parsed.netloc:
                            # Try multiple favicon services for better reliability
                            favicon_urls = [
                                f"https://www.google.com/s2/favicons?domain={parsed.netloc}&sz=64",
                                f"https://favicon.io/favicon/{parsed.netloc}/64",
                                f"https://t1.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url={parsed.netloc}&size=64"
                            ]
                            
                            sources.append({
                                "url": cleaned,
                                "site": parsed.netloc,
                                "favicon": favicon_urls[0],  # Use first one as primary
                                "favicon_fallbacks": favicon_urls[1:],  # Store fallbacks
                            })
                    except Exception:
                        continue
                        
                if sources:
                    sources = sources[:8]
                    print(f"✅ Extracted {len(sources)} sources: {[s['site'] for s in sources]}")
                    
                    # Enrich sources with thumbnails (Open Graph images)
                    try:
                        async with httpx.AsyncClient(timeout=httpx.Timeout(2.0, connect=1.0)) as _client:
                            sem = asyncio.Semaphore(3)
                            async def enrich(s: dict) -> None:
                                try:
                                    async with sem:
                                        r = await _client.get(s["url"], follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
                                    if r.status_code >= 200 and r.status_code < 400:
                                        html = r.text[:120000]
                                        t = re.search(r"<title[^>]*>([\s\S]*?)</title>", html, re.IGNORECASE)
                                        if t:
                                            title_val = re.sub(r"\s+", " ", t.group(1).strip())
                                            s["title"] = title_val
                                        m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
                                        if not m:
                                            m = re.search(r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
                                        if m:
                                            img_url = m.group(1)
                                            if img_url:
                                                if img_url.startswith('//'):
                                                    img_url = f"https:{img_url}"
                                                elif img_url.startswith('/'):
                                                    from urllib.parse import urljoin
                                                    img_url = urljoin(s["url"], img_url)
                                                s["thumbnail"] = img_url
                                except Exception:
                                    return
                            await asyncio.gather(*(enrich(s) for s in sources[:3]))
                    except Exception:
                        pass
                else:
                    sources = []
                    print("ℹ️ No sources found in content")
            
            # Save assistant message
            await self.save_message_to_conversation(
                conversation_id, 
                user_id, 
                "assistant", 
                assistant_content,
                {
                    "sources": sources,
                    "model": model,
                    "api_response": api_response
                }
            )
            
            # Create response messages in working format
            user_message = {
                "id": str(uuid.uuid4()),
                "role": "user", 
                "content": message,
                "created_at": datetime.utcnow().isoformat()
            }
            
            assistant_message = {
                "id": str(uuid.uuid4()),
                "role": "assistant",
                "content": assistant_content,
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Debug logging for response
            print(f"🔍 Final response sources: {sources}")
            print(f"🔍 Sources type: {type(sources)}")
            print(f"🔍 Sources length: {len(sources) if sources else 'None'}")
            
            return {
                "conversation_id": conversation_id,
                "user_message": user_message,
                "assistant_message": assistant_message,
                "reasoning": reasoning,
                "sources": sources
            }
            
        except Exception as e:
            # Save error message for debugging
            error_message = f"I apologize, but I encountered an error processing your request: {str(e)}"
            await self.save_message_to_conversation(
                conversation_id, 
                user_id, 
                "assistant", 
                error_message,
                {"error": str(e)}
            )
            
            return {
                "conversation_id": conversation_id,
                "user_message": {"role": "user", "content": message},
                "assistant_message": {"role": "assistant", "content": error_message},
                "sources": [],
                "error": str(e)
            }
    
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
            print(f"Database get conversations failed: {e}")
        
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
            print(f"Database delete conversation failed: {e}")
        
        # Use fallback storage
        if conversation_id in self.fallback_conversations:
            # Verify ownership
            metadata = self.fallback_conversation_metadata.get(conversation_id, {})
            if metadata.get("user_id") == user_id:
                del self.fallback_conversations[conversation_id]
                del self.fallback_conversation_metadata[conversation_id]
                return True
        
        return False
from __future__ import annotations

import os
import asyncio
import json
import re
from typing import List, Literal, Optional, Annotated, Dict, Any
import uuid
from datetime import datetime
from urllib.parse import urlparse, urljoin

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ...core.simple_auth import get_current_user_from_token
from ...database import ConversationService, UserService

router = APIRouter()

# Fallback in-memory conversation storage for when Supabase fails
fallback_conversations: Dict[str, List[Dict[str, Any]]] = {}
fallback_conversation_metadata: Dict[str, Dict[str, Any]] = {}

# Import user preferences storage from preferences module
from .preferences import user_preferences


async def _use_database_fallback(func_name: str, *args, **kwargs):
    """Try database operation, fall back to in-memory storage if it fails"""
    try:
        method = getattr(ConversationService, func_name)
        return await method(*args, **kwargs)
    except Exception as e:
        print(f"Database {func_name} failed: {e}, using fallback")
        return None


def _stringify_text(value) -> str:
    """Best-effort conversion of Responses API text payloads to a plain string."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        # Common shapes: {"text": "..."} or {"text": {"value": "..."}} or {"value": "..."}
        text_field = value.get("text")
        if isinstance(text_field, str):
            return text_field
        if isinstance(text_field, dict):
            inner_val = text_field.get("value")
            if isinstance(inner_val, str):
                return inner_val
        value_field = value.get("value")
        if isinstance(value_field, str):
            return value_field
        # Fallthrough: serialize the dict
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        parts: List[str] = []
        for item in value:
            parts.append(_stringify_text(item))
        return "".join(parts)
    # Fallback: JSON-serialize
    return json.dumps(value, ensure_ascii=False)


Role = Literal["system", "user", "assistant"]


class ChatMessage(BaseModel):
    role: Role
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    """Enhanced chat request supporting conversation context and tools"""
    message: str
    conversation_id: Optional[str] = None
    model: Optional[str] = "gpt-4o-mini"
    attachments: Optional[List[dict]] = None
    include_reasoning: bool = False
    developer_instructions: Optional[str] = None
    assistant_context: Optional[str] = None
    text_format: Optional[str] = "text"
    text_verbosity: Optional[str] = "medium"
    reasoning_effort: Optional[str] = "medium"
    reasoning_summary: Optional[str] = "auto"
    tools: Optional[List[dict]] = None
    store: bool = True


class ChatResponse(BaseModel):
    """Enhanced chat response with sources and reasoning"""
    conversation_id: str
    user_message: dict
    assistant_message: dict
    reasoning: Optional[str] = None
    sources: Optional[List[dict]] = None


@router.post("/send", response_model=ChatResponse)
async def send_chat_message(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user_from_token)
):
    """Send a chat message with advanced features including web search, tools, and conversation context"""
    try:
        # Get user ID and preferences
        user_id = current_user["id"]
        user_prefs = user_preferences.get(user_id, {})
        system_prompt = user_prefs.get("system_prompt")
        
        # Handle conversation creation or retrieval with fallback
        conversation = None
        conversation_messages = []
        use_fallback = False
        
        if request.conversation_id:
            # Try to get existing conversation from database
            conversation = await _use_database_fallback("get_conversation", request.conversation_id)
            
            if conversation:
                # Successfully got from database
                # Clean and compare user IDs
                conv_user_id = str(conversation["user_id"]).strip()
                req_user_id = str(user_id).strip()
                
                if conv_user_id != req_user_id:
                    print(f"❌ Send access denied: conversation owner '{conv_user_id}' != requester '{req_user_id}'")
                    raise HTTPException(status_code=403, detail="Access denied to conversation")
                
                conversation_id = request.conversation_id
                # Get existing messages
                db_messages = await _use_database_fallback("get_conversation_messages", conversation_id)
                if db_messages:
                    conversation_messages = [{"role": msg["role"], "content": msg["content"]} for msg in db_messages]
                else:
                    # Fall back to in-memory if message retrieval fails
                    conversation_messages = fallback_conversations.get(conversation_id, [])
                    use_fallback = True
            else:
                # Fall back to in-memory storage
                conversation_id = request.conversation_id
                conversation_messages = fallback_conversations.get(conversation_id, [])
                use_fallback = True
                if not conversation_messages:
                    raise HTTPException(status_code=404, detail="Conversation not found")
        else:
            # New conversation - try database first, fall back to in-memory
            title = ConversationService.generate_conversation_title(request.message)
            conversation = await _use_database_fallback(
                "create_conversation",
                user_id=user_id,
                title=title,
                model=request.model or "gpt-4o-mini",
                system_prompt=system_prompt
            )
            
            if conversation:
                conversation_id = str(conversation["id"])
            else:
                # Fall back to in-memory storage
                conversation_id = str(uuid.uuid4())
                fallback_conversations[conversation_id] = []
                # Store conversation metadata
                fallback_conversation_metadata[conversation_id] = {
                    "id": conversation_id,
                    "user_id": user_id,
                    "title": title,
                    "model": request.model or "gpt-4o-mini",
                    "system_prompt": system_prompt,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
                use_fallback = True
            
            conversation_messages = []
        
        # Add current user message
        if use_fallback:
            # Add to in-memory storage
            user_message_data = {"role": "user", "content": request.message}
            if conversation_id not in fallback_conversations:
                fallback_conversations[conversation_id] = []
            fallback_conversations[conversation_id].append(user_message_data)
            conversation_messages.append(user_message_data)
        else:
            # Try to add to database
            success = await _use_database_fallback(
                "add_message",
                conversation_id=conversation_id,
                role="user",
                content=request.message,
                metadata={"attachments": request.attachments or []}
            )
            if not success:
                # Fall back to in-memory
                user_message_data = {"role": "user", "content": request.message}
                if conversation_id not in fallback_conversations:
                    fallback_conversations[conversation_id] = []
                fallback_conversations[conversation_id].append(user_message_data)
                use_fallback = True
            # Add user message to messages for API call
            conversation_messages.append({"role": "user", "content": request.message})
        
        # Build messages array for OpenAI API
        api_messages = []
        
        # Add system prompt if user has one (like ChatGPT Custom Instructions)
        if system_prompt and system_prompt.strip():
            api_messages.append({
                "role": "system",
                "content": system_prompt.strip()
            })
        
        # Add conversation history
        api_messages.extend(conversation_messages)
        
        # Prepare for advanced OpenAI API call
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")

        model = request.model or "gpt-4o-mini"
        
        # Check if web search is requested in tools
        has_web_search = request.tools and any(tool.get("type") == "web_search_preview" for tool in request.tools)
        
        # Debug logging
        print(f"Chat request - Model: {model}")
        print(f"Tools provided: {request.tools}")
        print(f"Has web search: {has_web_search}")
        
        # Use Responses API for advanced features or gpt-5 models
        use_responses_api = (
            model.lower().startswith("gpt-5") or 
            request.tools is not None or 
            request.developer_instructions or 
            request.assistant_context
        )
        
        print(f"Using Responses API: {use_responses_api}")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        content = ""
        reasoning: Optional[str] = None
        sources: Optional[List[dict]] = None

        if use_responses_api:
            # Use Responses API for advanced features
            # For conversation context, we need to pass the full conversation
            conversation_context = ""
            if use_fallback and conversation_id in fallback_conversations and len(fallback_conversations[conversation_id]) > 1:
                # Build conversation context from fallback storage (exclude the just-added user message)
                for msg in fallback_conversations[conversation_id][:-1]:
                    role = msg["role"].capitalize()
                    conversation_context += f"{role}: {msg['content']}\n"
                conversation_context += f"User: {request.message}"
            elif not use_fallback and len(conversation_messages) > 1:
                # Build conversation context from database messages (exclude the just-added user message)
                for msg in conversation_messages[:-1]:
                    role = msg["role"].capitalize()
                    conversation_context += f"{role}: {msg['content']}\n"
                conversation_context += f"User: {request.message}"
            else:
                conversation_context = request.message
            
            payload = {
                "model": model,
                "input": conversation_context,
            }
            
            # Add tools if provided
            if request.tools:
                payload["tools"] = request.tools
                payload["tool_choice"] = "auto"
                print(f"Added tools to Responses API payload: {request.tools}")

            # Add system instructions combining user system prompt with other instructions
            system_instructions = ""
            if system_prompt and system_prompt.strip():
                system_instructions += system_prompt.strip()
            if request.developer_instructions:
                if system_instructions:
                    system_instructions += "\n\n"
                system_instructions += request.developer_instructions
            if request.assistant_context:
                if system_instructions:
                    system_instructions += "\n\n"
                system_instructions += request.assistant_context
            if system_instructions:
                payload["instructions"] = system_instructions
                
            url = "https://api.openai.com/v1/responses"
        else:
            # Use Chat Completions API
            if request.include_reasoning:
                system_prefix = (
                    "Respond in compact JSON with keys 'answer' and 'reason'. "
                    "Keep 'reason' to 1-3 short bullet points or sentences; "
                    "do not include internal chain-of-thought."
                )
                api_messages = (
                    [{"role": "system", "content": system_prefix}] + api_messages
                )

            payload = {
                "model": model,
                "messages": api_messages,
                "temperature": 0.7,
            }
            url = "https://api.openai.com/v1/chat/completions"

        async with httpx.AsyncClient(timeout=httpx.Timeout(90.0, connect=15.0)) as client:
            # Make API request with fallback logic
            try:
                resp = await client.post(url, json=payload, headers=headers)
            except (httpx.ReadTimeout, httpx.TimeoutException):
                # Fall back to Chat Completions if Responses API timed out
                if use_responses_api and url.endswith("/responses"):
                    fallback_payload = {
                        "model": model,
                        "messages": api_messages,
                        "temperature": 0.7,
                    }
                    resp = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        json=fallback_payload,
                        headers=headers,
                    )
                else:
                    raise HTTPException(status_code=504, detail="Upstream timeout from OpenAI")

            # Handle API response
            if resp.status_code != 200:
                # Try fallback to Chat Completions if Responses API fails
                if use_responses_api and url.endswith("/responses"):
                    fallback_payload = {
                        "model": model,
                        "messages": api_messages,
                        "temperature": 0.7,
                    }
                    resp = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        json=fallback_payload,
                        headers=headers
                    )
                    if resp.status_code != 200:
                        raise HTTPException(status_code=resp.status_code, detail=resp.text)
                else:
                    raise HTTPException(status_code=resp.status_code, detail=resp.text)

            data = resp.json()

            if use_responses_api and url.endswith("/responses"):
                # Handle Responses API response
                status_val = data.get("status")
                response_id = data.get("id")
                try:
                    attempts_remaining = 12
                    while status_val in {"in_progress", "queued"} and attempts_remaining > 0 and response_id:
                        await asyncio.sleep(0.4)
                        poll = await client.get(f"https://api.openai.com/v1/responses/{response_id}", headers=headers)
                        if poll.status_code != 200:
                            break
                        data = poll.json()
                        status_val = data.get("status")
                        attempts_remaining -= 1
                except Exception:
                    pass

                # Parse Responses API output
                content = _stringify_text(data.get("output_text") or "")
                if not content:
                    output_items = data.get("output", [])
                    if isinstance(output_items, list):
                        parts: List[str] = []
                        for item in output_items:
                            if not isinstance(item, dict):
                                continue
                            item_type = item.get("type")
                            if item_type == "output_text":
                                parts.append(_stringify_text(item.get("text")))
                                continue
                            if item_type == "message":
                                for block in item.get("content", []) or []:
                                    if not isinstance(block, dict):
                                        continue
                                    block_type = block.get("type")
                                    if block_type == "output_text":
                                        parts.append(_stringify_text(block.get("text")))
                        content = "".join(parts)

                # Extract reasoning if available
                if request.include_reasoning or request.reasoning_summary != "never":
                    reasoning_data = data.get("reasoning", {})
                    if isinstance(reasoning_data, dict):
                        reasoning = reasoning_data.get("summary", "")

                if not content:
                    content = "I received your message but couldn't generate a proper response. Please try again."
                else:
                    content = _stringify_text(content)
            else:
                # Handle Chat Completions API response
                content = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                ) or ""
                if request.include_reasoning:
                    try:
                        parsed = json.loads(content)
                        if isinstance(parsed, dict):
                            maybe = str(parsed.get("reason", ""))
                            if maybe:
                                reasoning = maybe
                            content = str(parsed.get("answer", content))
                    except Exception:
                        pass

            # Extract sources from content (URLs)
            try:
                sources = []
                if isinstance(content, str) and content:
                    raw_urls = re.findall(r"https?://[^\s)]+", content)
                    seen = set()
                    for u in raw_urls:
                        cleaned = u.rstrip('.,);]')
                        if cleaned in seen:
                            continue
                        seen.add(cleaned)
                        try:
                            parsed = urlparse(cleaned)
                            if parsed.scheme in {"http", "https"} and parsed.netloc:
                                sources.append({
                                    "url": cleaned,
                                    "site": parsed.netloc,
                                    "favicon": f"https://www.google.com/s2/favicons?domain={parsed.netloc}&sz=64",
                                })
                        except Exception:
                            continue
                    if sources:
                        sources = sources[:8]
                    else:
                        sources = None
            except Exception:
                sources = None

            # Enrich sources with thumbnails (Open Graph images)
            if sources:
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
                                                img_url = urljoin(s["url"], img_url)
                                            s["thumbnail"] = img_url
                            except Exception:
                                return
                        await asyncio.gather(*(enrich(s) for s in sources[:3]))
                except Exception:
                    pass

        # Add assistant response to storage
        if use_fallback:
            # Add to in-memory storage
            assistant_message_data = {"role": "assistant", "content": content}
            fallback_conversations[conversation_id].append(assistant_message_data)
        else:
            # Try to add to database
            success = await _use_database_fallback(
                "add_message",
                conversation_id=conversation_id,
                role="assistant",
                content=content,
                metadata={
                    "reasoning": reasoning,
                    "sources": sources,
                    "model": model
                }
            )
            if not success:
                # Fall back to in-memory
                assistant_message_data = {"role": "assistant", "content": content}
                if conversation_id not in fallback_conversations:
                    fallback_conversations[conversation_id] = []
                fallback_conversations[conversation_id].append(assistant_message_data)
        
        # Create response messages
        user_message = {
            "id": str(uuid.uuid4()),
            "role": "user", 
            "content": request.message,
            "created_at": datetime.now().isoformat()
        }
        
        assistant_message = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": content,
            "created_at": datetime.now().isoformat()
        }
        
        return ChatResponse(
            conversation_id=conversation_id,
            user_message=user_message,
            assistant_message=assistant_message,
            reasoning=reasoning,
            sources=sources
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat error: {str(e)}"
        )


@router.get("/conversations")
async def get_user_conversations(
    current_user: dict = Depends(get_current_user_from_token)
):
    """Get user's conversation history"""
    try:
        user_id = current_user["id"]
        print(f"🔍 Loading conversations for user ID: {user_id}")
        conversations = await ConversationService.get_user_conversations(user_id)
        print(f"📋 Found {len(conversations)} conversations for user {user_id}")
        
        return {
            "conversations": [
                {
                    "id": conv["id"],
                    "title": conv["title"],
                    "created_at": conv["created_at"],
                    "updated_at": conv["updated_at"],
                    "model": conv["model"]
                }
                for conv in conversations
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get conversations: {str(e)}"
        )


@router.get("/conversations/{conversation_id}")
async def get_conversation_details(
    conversation_id: str,
    current_user: dict = Depends(get_current_user_from_token)
):
    """Get conversation with messages"""
    try:
        user_id = current_user["id"]
        
        # Get conversation
        conversation = await ConversationService.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Clean and compare user IDs
        conv_user_id = str(conversation["user_id"]).strip()
        req_user_id = str(user_id).strip()
        
        print(f"🔍 Conversation {conversation_id}: owner='{conv_user_id}' ({len(conv_user_id)}), requester='{req_user_id}' ({len(req_user_id)})")
        if conv_user_id != req_user_id:
            print(f"❌ Access denied: conversation owner '{conv_user_id}' != requester '{req_user_id}'")
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get messages
        messages = await ConversationService.get_conversation_messages(conversation_id)
        
        return {
            "conversation": {
                "id": conversation["id"],
                "title": conversation["title"],
                "created_at": conversation["created_at"],
                "updated_at": conversation["updated_at"],
                "model": conversation["model"],
                "system_prompt": conversation["system_prompt"]
            },
            "messages": [
                {
                    "id": msg["id"],
                    "role": msg["role"],
                    "content": msg["content"],
                    "created_at": msg["created_at"],
                    "metadata": msg["metadata"]
                }
                for msg in messages
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get conversation: {str(e)}"
        )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user_from_token)
):
    """Delete a conversation and all its messages"""
    try:
        user_id = current_user["id"]
        
        # Verify conversation belongs to user before deleting
        conversation = await ConversationService.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Clean and compare user IDs
        conv_user_id = str(conversation["user_id"]).strip()
        req_user_id = str(user_id).strip()
        
        if conv_user_id != req_user_id:
            print(f"❌ Delete access denied: conversation owner '{conv_user_id}' != requester '{req_user_id}'")
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Delete the conversation
        success = await ConversationService.delete_conversation(conversation_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete conversation")
        
        return {"message": "Conversation deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete conversation: {str(e)}"
        )


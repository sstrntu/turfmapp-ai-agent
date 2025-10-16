"""
Chat API Endpoints - RESTful Interface for AI Chat Functionality

This module provides HTTP endpoints for chat operations following REST principles:

Endpoints:
- POST /send: Send message to AI assistant with multi-model support
- GET /conversations: List user's conversations with metadata
- GET /conversations/{id}: Retrieve conversation history with sources preserved
- DELETE /conversations/{id}: Delete conversation and messages
- POST /conversations/{id}/messages: Add message to existing conversation
- GET /health: Service health check
- GET /models: Available AI models list

Architecture:
- API layer pattern with business logic delegated to service layer
- Pydantic models for request/response validation
- JWT authentication with user context
- Comprehensive error handling with HTTP status codes
- OpenAPI documentation auto-generation

Recent fixes (August 2025):
- Fixed UUID import error causing conversation loading failures
- Removed conflicting Pydantic response model constraints
- Enhanced conversation response format to preserve message metadata
- Added support for auto-generated conversation titles
"""

from __future__ import annotations

import logging

from typing import List, Literal, Optional, Dict, Any
from datetime import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ...core.jwt_auth import get_current_user_from_token
from ...services.chat_service import EnhancedChatService
from ...services.tool_manager import tool_manager
from ...database import ConversationService

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter()
chat_service = EnhancedChatService()

# Type definitions
Role = Literal["system", "user", "assistant"]


class ChatMessage(BaseModel):
    role: Role
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    """Enhanced chat request supporting conversation context and tools"""

    message: str
    conversation_id: Optional[str] = None
    model: Optional[str] = (
        None  # Changed: No default, so database preference takes precedence
    )
    attachments: Optional[List[dict]] = None
    include_reasoning: bool = False
    developer_instructions: Optional[str] = None
    assistant_context: Optional[str] = None
    text_format: Optional[str] = "text"
    text_verbosity: Optional[str] = "medium"
    reasoning_effort: Optional[str] = "medium"
    reasoning_summary: Optional[str] = "auto"
    tools: Optional[List[dict]] = None
    tool_choice: Optional[str] = "auto"
    store: bool = True


class ChatResponse(BaseModel):
    """Enhanced chat response with sources and reasoning"""

    conversation_id: str
    user_message: dict
    assistant_message: dict
    reasoning: Optional[str] = None
    sources: Optional[List[dict]] = None
    model: Optional[str] = None
    provider: Optional[str] = None


class ConversationListResponse(BaseModel):
    """Response model for conversation list"""

    conversations: List[dict]


class ConversationResponse(BaseModel):
    """Response model for individual conversation"""

    conversation_id: str
    title: str
    messages: List[ChatMessage]


@router.post("/send", response_model=ChatResponse)
async def send_chat_message(
    request: ChatRequest, current_user: dict = Depends(get_current_user_from_token)
):
    """Send a chat message with advanced features including conversation context"""
    try:
        user_id = current_user["id"]

        # Get user preferences from database to determine model if not specified
        user_prefs = await chat_service.get_user_preferences(user_id)

        # Use model from request if provided, otherwise use user's default from database
        model_to_use = (
            request.model if request.model else user_prefs.get("model", "gpt-4o")
        )

        result = await chat_service.process_chat_request(
            user_id=user_id,
            message=request.message,
            conversation_id=request.conversation_id,
            model=model_to_use,
            include_reasoning=request.include_reasoning,
            attachments=request.attachments,
            developer_instructions=request.developer_instructions,
            assistant_context=request.assistant_context,
            text_format=request.text_format,
            text_verbosity=request.text_verbosity,
            reasoning_effort=request.reasoning_effort,
            tools=request.tools,
            tool_choice=request.tool_choice,
        )

        return ChatResponse(
            conversation_id=result["conversation_id"],
            user_message=result["user_message"],
            assistant_message=result["assistant_message"],
            reasoning=result.get("reasoning"),
            sources=result.get("sources", []),
            model=result.get("model"),
            provider=result.get("provider"),
        )

    except Exception as e:
        logger.error(f"❌ Chat error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to process chat message: {str(e)}"
        )


@router.get("/conversations", response_model=ConversationListResponse)
async def get_conversations(current_user: dict = Depends(get_current_user_from_token)):
    """Get list of conversations for the current user"""
    try:
        user_id = current_user["id"]
        conversations = await chat_service.get_conversation_list(user_id)

        return ConversationListResponse(conversations=conversations)

    except Exception as e:
        logger.error(f"❌ Get conversations error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve conversations: {str(e)}"
        )


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str, current_user: dict = Depends(get_current_user_from_token)
):
    """Get specific conversation with messages"""
    try:
        user_id = current_user["id"]

        # Get conversation history
        messages = await chat_service.get_conversation_history(conversation_id, user_id)

        if not messages:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Get conversation metadata (title)
        conversations = await chat_service.get_conversation_list(user_id)
        conversation_data = next(
            (conv for conv in conversations if conv["id"] == conversation_id),
            {"title": "Untitled Conversation"},
        )

        # Return messages in the format expected by frontend (with full metadata)
        return {
            "conversation": {
                "id": conversation_id,
                "title": conversation_data.get("title", "Untitled Conversation"),
            },
            "messages": [
                {
                    "id": msg.get("id", str(uuid.uuid4())),
                    "role": msg["role"],
                    "content": msg["content"],
                    "created_at": msg.get("created_at", datetime.now().isoformat()),
                    "metadata": msg.get("metadata", {}),
                }
                for msg in messages
                if isinstance(msg, dict) and "role" in msg and "content" in msg
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get conversation error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve conversation: {str(e)}"
        )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str, current_user: dict = Depends(get_current_user_from_token)
):
    """Delete a conversation"""
    try:
        user_id = current_user["id"]

        success = await chat_service.delete_conversation(conversation_id, user_id)

        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return {"message": "Conversation deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Delete conversation error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to delete conversation: {str(e)}"
        )


@router.post("/conversations/{conversation_id}/messages")
async def add_message_to_conversation(
    conversation_id: str,
    message: ChatMessage,
    current_user: dict = Depends(get_current_user_from_token),
):
    """Add a message to an existing conversation"""
    try:
        user_id = current_user["id"]

        success = await chat_service.save_message_to_conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            role=message.role,
            content=message.content,
        )

        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return {"message": "Message added successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Add message error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add message: {str(e)}")


@router.get("/health")
async def chat_health_check():
    """Health check endpoint for chat service"""
    return {"status": "healthy", "service": "chat", "timestamp": "2025-08-30T12:00:00Z"}


@router.get("/models")
async def get_available_models():
    """Get list of available chat models"""
    return {
        "models": [
            {"id": "gpt-4o", "name": "GPT-4O", "description": "Most capable model"},
            {
                "id": "gpt-4o-mini",
                "name": "GPT-4O Mini",
                "description": "Fast and efficient",
            },
            {"id": "o1", "name": "O1", "description": "Advanced reasoning"},
            {"id": "o1-mini", "name": "O1 Mini", "description": "Reasoning optimized"},
            {
                "id": "o1-preview",
                "name": "O1 Preview",
                "description": "Latest reasoning model",
            },
            {
                "id": "claude-3-haiku-20240307",
                "name": "Claude 3 Haiku",
                "description": "Anthropic Claude – fastest option",
            },
            {
                "id": "claude-sonnet-4-20250514",
                "name": "Claude Sonnet 4",
                "description": "Anthropic Claude – balanced",
            },
            {
                "id": "claude-sonnet-4-5-20250929",
                "name": "Claude Sonnet 4.5",
                "description": "Anthropic Claude – enhanced reasoning",
            },
            {
                "id": "claude-opus-4-1-20250805",
                "name": "Claude Opus 4.1",
                "description": "Anthropic Claude – most capable",
            },
        ]
    }


@router.get("/tools")
async def get_available_tools():
    """Get list of available tools for the chatbot"""
    try:
        # Get traditional tools from tool manager
        traditional_tools = tool_manager.get_available_tools()
        traditional_descriptions = tool_manager.get_tool_descriptions()

        # Get MCP tools for Google services
        from ...services.mcp_client import get_all_google_tools

        mcp_tools = await get_all_google_tools()

        # Convert MCP tools to the expected format
        mcp_descriptions = {}
        mcp_tool_list = []

        for mcp_tool in mcp_tools:
            tool_name = mcp_tool.get("name")
            tool_desc = mcp_tool.get("description")

            # Convert to OpenAI function format
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool_desc,
                    "parameters": mcp_tool.get("inputSchema"),
                },
            }

            mcp_tool_list.append(openai_tool)
            mcp_descriptions[tool_name] = tool_desc

        # Combine both tool sets
        all_tools = traditional_tools + mcp_tool_list
        all_descriptions = {**traditional_descriptions, **mcp_descriptions}

        return {
            "tools": all_tools,
            "descriptions": all_descriptions,
            "mcp_tools_count": len(mcp_tools),
            "traditional_tools_count": len(traditional_tools),
        }

    except Exception as e:
        # Fallback to traditional tools only
        logger.error(f"❌ Failed to get MCP tools: {e}")
        return {
            "tools": tool_manager.get_available_tools(),
            "descriptions": tool_manager.get_tool_descriptions(),
            "mcp_tools_count": 0,
            "traditional_tools_count": len(tool_manager.get_available_tools()),
            "error": f"MCP tools unavailable: {str(e)}",
        }

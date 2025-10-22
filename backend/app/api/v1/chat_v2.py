"""
Chat API V2 - LlamaIndex Integration

This module provides the next-generation chat API using LlamaIndex for:
- Multi-model LLM support via LLM Factory
- Conversation memory with auto-summarization
- Token tracking and cost estimation
- Better error handling

Differences from V1:
- Uses LlamaIndex instead of direct OpenAI calls
- Intelligent memory management with auto-summarization
- Task-based model selection
- PostgreSQL persistence for conversations

New endpoints:
- POST /v2/send: Send message with LlamaIndex (drop-in replacement for /send)
- GET /v2/models: Get available models with capabilities
- GET /v2/conversations/{id}/summary: Get AI-generated conversation summary
- GET /v2/conversations/{id}/entities: Get extracted entities from conversation
"""

from __future__ import annotations

import logging
from typing import List, Literal, Optional, Dict, Any
from datetime import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ...core.jwt_auth import get_current_user_from_token
from ...llamaindex.services.llm_factory import llm_factory, TaskType
from ...llamaindex.memory.conversation_memory import MemoryManager
from ...llamaindex.memory.user_memory import UserMemory
from llama_index.core.llms import ChatMessage, MessageRole
from ...database import get_db_pool, ConversationService

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2", tags=["chat-v2"])

# Global memory manager (initialized on first request)
memory_manager: Optional[MemoryManager] = None

# Type definitions
Role = Literal["system", "user", "assistant"]


class ChatRequest(BaseModel):
    """Chat request for V2 endpoint"""
    message: str
    conversation_id: Optional[str] = None
    model: Optional[str] = None  # If not specified, uses task-based selection
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: Optional[int] = None
    include_memory: bool = True  # Whether to use conversation memory
    system_prompt: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat response for V2 endpoint"""
    conversation_id: str
    user_message: Dict[str, Any]
    assistant_message: Dict[str, Any]
    model_used: str
    provider: str
    tokens_used: Optional[Dict[str, int]] = None
    memory_summary: Optional[str] = None


class ModelInfo(BaseModel):
    """Model information"""
    id: str
    name: str
    provider: str
    capabilities: List[str]
    cost_per_1k_input: float
    cost_per_1k_output: float
    context_window: int
    recommended_for: List[str]


async def get_memory_manager() -> MemoryManager:
    """Get or create global memory manager"""
    global memory_manager
    if memory_manager is None:
        db_pool = await get_db_pool()
        memory_manager = MemoryManager(db_pool=db_pool)
    return memory_manager


@router.post("/send")
async def send_chat_message_v2(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Send a chat message using LlamaIndex.

    Features:
    - Multi-model support (OpenAI + Anthropic)
    - Automatic conversation memory
    - Auto-summarization after 30 messages
    - Entity extraction
    - Token tracking

    Example:
    ```
    POST /v2/send
    {
        "message": "What is machine learning?",
        "conversation_id": "optional-conv-id",
        "model": "gpt-4o",  # optional
        "temperature": 0.7,
        "include_memory": true
    }
    ```
    """
    try:
        user_id = current_user["id"]

        # Generate conversation ID if not provided
        conversation_id = request.conversation_id or str(uuid.uuid4())

        # Ensure conversation exists in database
        existing_conv = await ConversationService.get_conversation(conversation_id)
        if not existing_conv:
            # Create new conversation with specific ID
            title = request.message[:50] + ("..." if len(request.message) > 50 else "")
            db_pool = await get_db_pool()
            async with db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO turfmapp_agent.conversations
                    (id, user_id, title, model, system_prompt, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
                    """,
                    conversation_id,
                    user_id,
                    title,
                    request.model or llm_factory.recommend_model_for_task(TaskType.CHAT),
                    request.system_prompt
                )
            logger.info(f"Created new conversation: {conversation_id}")

        # Get memory manager
        mem_mgr = await get_memory_manager()
        memory = None

        # Load user-level memory (account-wide facts)
        db_pool = await get_db_pool()
        user_memory = UserMemory(user_id=user_id, db_pool=db_pool)
        await user_memory.load_from_database()

        if request.include_memory:
            memory = mem_mgr.get_memory(
                user_id=user_id,
                conversation_id=conversation_id
            )
            await memory.load_from_database()

        # Get model to use
        if request.model:
            model_id = request.model
        else:
            # Use task-based selection
            model_id = llm_factory.recommend_model_for_task(TaskType.CHAT)
            logger.info(f"Auto-selected model: {model_id}")

        # Create LLM instance
        llm = llm_factory.create_llm(
            model_id=model_id,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )

        # Build messages
        messages = []

        # Build system prompt with user memory context
        system_content_parts = []

        # Add user memory context
        user_context = user_memory.get_context_string()
        if user_context:
            system_content_parts.append(user_context)

        # Add custom system prompt if provided
        if request.system_prompt:
            system_content_parts.append(request.system_prompt)

        # Add combined system message
        if system_content_parts:
            messages.append(ChatMessage(
                role=MessageRole.SYSTEM,
                content="\n\n".join(system_content_parts)
            ))

        # Add conversation history from memory
        if memory:
            history = await memory.get_messages(limit=10)
            for msg in history:
                messages.append(ChatMessage(
                    role=MessageRole(msg["role"]),
                    content=msg["content"]
                ))

        # Add current user message
        messages.append(ChatMessage(
            role=MessageRole.USER,
            content=request.message
        ))

        # Query RAG for relevant document context
        rag_context = None
        try:
            from ...llamaindex.rag import RAGQueryService, PgVectorStore
            from ...llamaindex.services.llm_factory import TaskType as LLMTaskType

            vector_store = PgVectorStore(db_pool=db_pool)
            rag_llm = llm_factory.create_llm(
                model_id=llm_factory.recommend_model_for_task(LLMTaskType.CHAT),
                temperature=0.3
            )
            rag_service = RAGQueryService(
                vector_store=vector_store,
                llm=rag_llm,
                top_k=3,
                similarity_threshold=0.3  # Lower threshold to catch more results
            )

            rag_result = await rag_service.query(
                question=request.message,
                user_id=user_id,
                include_sources=True,
                include_organization_docs=True
            )

            # If relevant chunks found, add to context
            if rag_result['chunks_found'] > 0:
                rag_context = f"""
**Relevant Information from Your Documents:**
{rag_result['answer']}

Sources: {', '.join([s['filename'] for s in rag_result.get('sources', [])])}
"""
                logger.info(f"RAG found {rag_result['chunks_found']} relevant chunks")

                # Add RAG context to messages
                messages.insert(-1, ChatMessage(
                    role=MessageRole.SYSTEM,
                    content=f"""You have access to the user's uploaded documents. Here is relevant information that may help answer their question:

{rag_result['answer']}

Use this information when relevant, but you can also use your general knowledge. If the user's question is specifically about their documents, prioritize the document information above."""
                ))
        except Exception as e:
            logger.warning(f"RAG query failed (continuing without RAG): {e}")

        # Get LLM response
        logger.info(f"Sending {len(messages)} messages to {model_id}")
        response = await llm.achat(messages)
        assistant_content = response.message.content

        # Save to memory
        if memory:
            await memory.add_message(
                role="user",
                content=request.message,
                metadata={"model": model_id}
            )
            await memory.add_message(
                role="assistant",
                content=assistant_content,
                metadata={"model": model_id}
            )

            # Extract user facts from conversation for account-level memory
            recent_messages = await memory.get_messages(limit=10)
            if len(recent_messages) >= 2:  # Need at least a conversation
                await user_memory.extract_facts_from_conversation(
                    messages=recent_messages,
                    conversation_id=conversation_id,
                    llm=llm
                )

        # Get model config for response
        model_config = llm_factory.get_model_config(model_id)

        # Build response
        user_msg = {
            "id": str(uuid.uuid4()),
            "role": "user",
            "content": request.message,
            "created_at": datetime.now().isoformat(),
            "metadata": {"model": model_id}
        }

        assistant_msg = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": assistant_content,
            "created_at": datetime.now().isoformat(),
            "metadata": {"model": model_id}
        }

        return ChatResponse(
            conversation_id=conversation_id,
            user_message=user_msg,
            assistant_message=assistant_msg,
            model_used=model_id,
            provider=model_config.provider,
            memory_summary=memory.summary if memory else None
        )

    except Exception as e:
        logger.error(f"❌ Chat V2 error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process chat message: {str(e)}"
        )


@router.get("/models")
async def get_available_models_v2():
    """
    Get list of available models with detailed information.

    Includes:
    - Model capabilities
    - Cost per 1k tokens
    - Context window size
    - Recommended use cases

    Example response:
    ```json
    {
        "models": [
            {
                "id": "gpt-4o",
                "name": "GPT-4o",
                "provider": "openai",
                "capabilities": ["chat", "function_calling", "streaming"],
                "cost_per_1k_input": 0.005,
                "cost_per_1k_output": 0.015,
                "context_window": 128000,
                "recommended_for": ["chat", "tool_use", "analysis"]
            }
        ]
    }
    ```
    """
    try:
        models = llm_factory.list_available_models()

        model_list = []
        for model in models:
            model_list.append(ModelInfo(
                id=model.model_id,
                name=model.display_name,
                provider=model.provider,
                capabilities=[cap.value for cap in model.capabilities],
                cost_per_1k_input=model.cost_per_1k_input,
                cost_per_1k_output=model.cost_per_1k_output,
                context_window=model.context_window,
                recommended_for=[task.value for task in model.recommended_for]
            ))

        return {
            "models": [m.dict() for m in model_list],
            "total": len(model_list),
            "providers": list(set(m.provider for m in model_list))
        }

    except Exception as e:
        logger.error(f"❌ Get models V2 error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get models: {str(e)}"
        )


@router.get("/conversations/{conversation_id}/summary")
async def get_conversation_summary(
    conversation_id: str,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Get AI-generated summary of a conversation.

    The summary is automatically generated when the conversation
    reaches 30 messages and includes:
    - Main topics discussed
    - Key decisions or conclusions
    - Important context to remember

    Example:
    ```
    GET /v2/conversations/abc-123/summary
    ```
    """
    try:
        user_id = current_user["id"]

        # Get memory
        mem_mgr = await get_memory_manager()
        memory = mem_mgr.get_memory(user_id, conversation_id)
        await memory.load_from_database()

        if memory.message_count == 0:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Get or generate summary
        if memory.summary:
            summary = memory.summary
        elif memory.message_count >= 5:
            # Generate summary if we have enough messages
            summary = await memory.summarize_conversation()
        else:
            summary = "Conversation too short to summarize (need at least 5 messages)"

        return {
            "conversation_id": conversation_id,
            "summary": summary,
            "message_count": memory.message_count,
            "auto_summarized": memory.summary is not None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get summary error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get conversation summary: {str(e)}"
        )


@router.get("/conversations/{conversation_id}/entities")
async def get_conversation_entities(
    conversation_id: str,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Get entities extracted from a conversation.

    Entities include:
    - People (names, roles)
    - Places (locations, addresses)
    - Organizations (companies, institutions)
    - Dates and times
    - Key topics or subjects

    Example response:
    ```json
    {
        "entities": {
            "people": ["Alice", "Bob"],
            "places": ["San Francisco", "New York"],
            "topics": ["Machine Learning", "Python"]
        }
    }
    ```
    """
    try:
        user_id = current_user["id"]

        # Get memory
        mem_mgr = await get_memory_manager()
        memory = mem_mgr.get_memory(user_id, conversation_id)
        await memory.load_from_database()

        if memory.message_count == 0:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Get or extract entities
        if memory.entities:
            entities = memory.entities
        elif memory.message_count >= 5:
            # Extract entities if we have enough messages
            entities = await memory.extract_entities()
        else:
            entities = {}

        return {
            "conversation_id": conversation_id,
            "entities": entities,
            "message_count": memory.message_count
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get entities error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get conversation entities: {str(e)}"
        )


@router.get("/health")
async def chat_v2_health_check():
    """Health check endpoint for chat V2 service"""
    try:
        # Check if LLM factory is working
        models = llm_factory.list_available_models()

        return {
            "status": "healthy",
            "service": "chat-v2",
            "version": "2.0.0",
            "llamaindex_enabled": True,
            "models_available": len(models),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "degraded",
            "service": "chat-v2",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

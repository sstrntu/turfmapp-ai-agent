"""
Chat API V2 - Unified Workflow with Intelligent Tool Selection

This module provides the next-generation chat API using LlamaIndex with:
- Intelligent tool selection (RAG, Gmail, Drive, Calendar)
- Multi-model LLM support via LLM Factory
- Conversation and user memory integration
- ReActAgent for autonomous tool use
- Reasoning transparency

Features:
- Agent decides which tools to use based on query
- Multi-tool orchestration for complex tasks
- Memory persists across conversations
- Transparent reasoning (see which tools were used)

Endpoints:
- POST /api/v2/chat/send: Send message with unified workflow
- GET /api/v2/chat/models: Get available models with capabilities
- GET /api/v2/chat/conversations/{id}/summary: Get conversation summary
- GET /api/v2/chat/conversations/{id}/entities: Get extracted entities
"""

from __future__ import annotations

import logging
from typing import List, Literal, Optional, Dict, Any
from datetime import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import json
import asyncio

from ...core.jwt_auth import get_current_user_from_token
from ...llamaindex.services.llm_factory import llm_factory, TaskType
from ...llamaindex.memory.conversation_memory import MemoryManager
from ...llamaindex.memory.user_memory import UserMemory
from llama_index.core.llms import ChatMessage, MessageRole
from ...database import get_db_pool, ConversationService
from ...services.conversation_manager import ConversationManager

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat-v2"])

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
    tools: Optional[List[dict]] = None  # OpenAI tools (web_search_preview, etc.)
    tool_choice: Optional[str] = "auto"
    attachments: Optional[List[dict]] = None
    assistant_context: Optional[str] = None


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
    Send a chat message using Unified Workflow with intelligent tool selection.

    The system intelligently decides which tools to use based on your query:
    - **RAG** for document queries ("What does my PDF say?")
    - **Gmail** for email tasks ("Find emails from John") [requires Google auth]
    - **Drive** for file management ("List my Drive files") [requires Google auth]
    - **Calendar** for scheduling ("What meetings tomorrow?") [requires Google auth]
    - **Direct answer** for general questions ("What is ML?")

    Features:
    - Automatic tool selection (agent decides what's needed)
    - Multi-model support (OpenAI + Anthropic)
    - Conversation and user memory integration
    - Transparent reasoning (see which tools were used)
    - Multi-step tasks (can use multiple tools in one query)

    Example:
    ```
    POST /api/v2/chat/send
    {
        "message": "What does my uploaded PDF say about machine learning?",
        "conversation_id": "optional-conv-id",
        "model": "gpt-4o",  # optional
        "temperature": 0.7,
        "include_memory": true
    }
    ```

    Response includes:
    - Assistant's answer
    - Tools used (e.g., ["search_documents"])
    - Reasoning steps
    - Model used
    """
    try:
        user_id = current_user["id"]
        conversation_id = request.conversation_id or str(uuid.uuid4())

        logger.info(f"🧠 Chat request (unified): user={user_id}, conversation={conversation_id}")

        # Ensure conversation exists in database
        try:
            # Check if conversation exists
            existing = await ConversationService.get_conversation(conversation_id)
            if not existing:
                # Create new conversation with the specified ID
                db_pool = await get_db_pool()
                async with db_pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO turfmapp_agent.conversations (id, user_id, title, created_at, updated_at)
                        VALUES ($1, $2, $3, NOW(), NOW())
                        ON CONFLICT (id) DO NOTHING
                        """,
                        conversation_id, user_id, "New Conversation"
                    )
                logger.info(f"📝 Created new conversation: {conversation_id}")
        except Exception as e:
            logger.warning(f"Could not ensure conversation exists: {e}")

        # Get Google credentials if available
        google_credentials = None
        try:
            from .google_api import get_user_google_credentials
            google_credentials = await get_user_google_credentials(user_id)
            logger.info("✅ Google credentials available - enabling Gmail/Drive/Calendar tools")
        except Exception as e:
            logger.debug(f"No Google credentials available: {e}")

        # Initialize unified workflow
        from ...llamaindex.workflows.unified_workflow import (
            UnifiedWorkflow,
            UnifiedWorkflowInput,
        )

        db_pool = await get_db_pool()
        mem_mgr = await get_memory_manager()

        workflow = UnifiedWorkflow(
            db_pool=db_pool,
            memory_manager=mem_mgr,
            verbose=False,  # Set to True for debugging
        )

        # Create workflow input
        workflow_input = UnifiedWorkflowInput(
            user_id=user_id,
            conversation_id=conversation_id,
            message=request.message,
            model_id=request.model,
            temperature=request.temperature,
            include_memory=request.include_memory,
            google_credentials=google_credentials,
        )

        # Execute workflow
        logger.info(f"🚀 Executing unified workflow...")
        result = await workflow.run(input=workflow_input)

        # Extract output
        output = result
        if hasattr(result, 'result'):
            output = result.result

        logger.info(
            f"✅ Workflow complete: tools_used={output.tools_used}, "
            f"model={output.model_used}"
        )

        # Create response messages
        user_msg = {
            "id": str(uuid.uuid4()),
            "role": "user",
            "content": request.message,
            "created_at": datetime.now().isoformat(),
        }

        assistant_msg = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": output.response,
            "created_at": datetime.now().isoformat(),
            "metadata": {
                "model": output.model_used,
                "tools_used": output.tools_used,
                "reasoning_steps": output.reasoning_steps,
                "conversation_id": conversation_id,
            },
        }

        if output.metadata:
            assistant_msg["metadata"].setdefault("custom", output.metadata)

        # Get provider from model config
        model_config = llm_factory.get_model_config(output.model_used)

        return ChatResponse(
            conversation_id=conversation_id,
            user_message=user_msg,
            assistant_message=assistant_msg,
            model_used=output.model_used,
            provider=model_config.provider,
            tokens_used=None,  # TODO: Extract from workflow
            memory_summary=None,  # Available in conversation memory
        )

    except Exception as e:
        logger.error(f"❌ Chat V2 error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process chat message: {str(e)}"
        )


@router.post("/stream")
async def stream_chat_message_v2(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Stream a chat message with real-time agent thought process.

    Returns Server-Sent Events (SSE) with the following event types:
    - `thought`: Agent's reasoning step
    - `tool_call`: Tool being executed
    - `tool_result`: Result from tool execution
    - `content`: Partial response content
    - `done`: Final response with complete data
    - `error`: Error occurred

    Example events:
    ```
    data: {"type": "thought", "content": "Analyzing user query..."}
    data: {"type": "tool_call", "tool": "search_documents", "input": {"query": "machine learning"}}
    data: {"type": "tool_result", "tool": "search_documents", "result": "Found 3 documents..."}
    data: {"type": "content", "delta": "Based on your documents, "}
    data: {"type": "done", "conversation_id": "...", "model_used": "gpt-4o", ...}
    ```
    """

    async def event_generator():
        """Generate SSE events from workflow execution"""
        try:
            user_id = current_user["id"]
            conversation_id = request.conversation_id or str(uuid.uuid4())

            # Send initial event
            yield f"data: {json.dumps({'type': 'start', 'conversation_id': conversation_id})}\n\n"

            logger.info(f"🧠 Streaming chat request: user={user_id}, conversation={conversation_id}")

            # Ensure conversation exists
            try:
                existing = await ConversationService.get_conversation(conversation_id)
                if not existing:
                    db_pool = await get_db_pool()
                    async with db_pool.acquire() as conn:
                        await conn.execute(
                            """
                            INSERT INTO turfmapp_agent.conversations (id, user_id, title, created_at, updated_at)
                            VALUES ($1, $2, $3, NOW(), NOW())
                            ON CONFLICT (id) DO NOTHING
                            """,
                            conversation_id, user_id, "New Conversation"
                        )
            except Exception as e:
                logger.warning(f"Could not ensure conversation exists: {e}")

            # Get Google credentials
            google_credentials = None
            try:
                from .google_api import get_user_google_credentials
                google_credentials = await get_user_google_credentials(user_id)
                yield f"data: {json.dumps({'type': 'thought', 'content': '✅ Google services available'})}\n\n"
            except Exception:
                pass

            # Initialize workflow
            from ...llamaindex.workflows.unified_workflow import (
                UnifiedWorkflow,
                UnifiedWorkflowInput,
            )

            db_pool = await get_db_pool()
            mem_mgr = await get_memory_manager()

            workflow = UnifiedWorkflow(
                db_pool=db_pool,
                memory_manager=mem_mgr,
                verbose=True,  # Enable for detailed logging
            )

            # Create event queue for real-time streaming
            event_queue = asyncio.Queue()
            workflow_task = None
            workflow_result = None

            async def emit_event(event: Dict[str, Any]):
                """Callback to emit events from workflow"""
                await event_queue.put(event)

            workflow_input = UnifiedWorkflowInput(
                user_id=user_id,
                conversation_id=conversation_id,
                message=request.message,
                model_id=request.model,
                temperature=request.temperature,
                include_memory=request.include_memory,
                google_credentials=google_credentials,
                event_emitter=emit_event,  # Pass event emitter
            )

            # Start workflow execution in background
            async def run_workflow():
                nonlocal workflow_result
                result = await workflow.run(input=workflow_input)
                workflow_result = result.result if hasattr(result, 'result') else result
                # Signal completion by putting None in queue
                await event_queue.put(None)

            workflow_task = asyncio.create_task(run_workflow())

            # Stream events as they arrive from workflow
            while True:
                try:
                    # Wait for next event with timeout
                    event = await asyncio.wait_for(event_queue.get(), timeout=60.0)

                    # None signals workflow completion
                    if event is None:
                        break

                    # Yield event to client
                    yield f"data: {json.dumps(event)}\n\n"

                except asyncio.TimeoutError:
                    # Check if workflow is still running
                    if workflow_task.done():
                        break
                    # Send keepalive
                    yield f"data: {json.dumps({'type': 'keepalive'})}\n\n"

            # Wait for workflow to complete
            await workflow_task

            # Ensure we have the result
            if workflow_result is None:
                raise Exception("Workflow did not produce a result")

            output = workflow_result

            # Create final response
            user_msg = {
                "id": str(uuid.uuid4()),
                "role": "user",
                "content": request.message,
                "created_at": datetime.now().isoformat(),
            }

            assistant_msg = {
                "id": str(uuid.uuid4()),
                "role": "assistant",
                "content": output.response,
                "created_at": datetime.now().isoformat(),
                "metadata": {
                    "model": output.model_used,
                    "tools_used": output.tools_used,
                    "reasoning_steps": output.reasoning_steps,
                },
            }

            model_config = llm_factory.get_model_config(output.model_used)

            # Send completion event
            completion_data = {
                "type": "done",
                "conversation_id": conversation_id,
                "user_message": user_msg,
                "assistant_message": assistant_msg,
                "metadata": output.metadata,  # Include all metadata (includes memory_request)
                "memory_request": output.memory_request,  # Explicit field for HITL consent prompt
                "model_used": output.model_used,
                "provider": model_config.provider,
                "tools_used": output.tools_used,
                "sources": output.sources,  # Web search sources for popup
            }

            yield f"data: {json.dumps(completion_data)}\n\n"

        except Exception as e:
            logger.error(f"❌ Streaming error: {e}", exc_info=True)
            error_data = {
                "type": "error",
                "error": str(e)
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
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
    GET /api/v2/chat/conversations/abc-123/summary
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

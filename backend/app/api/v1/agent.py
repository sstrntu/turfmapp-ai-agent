"""
Agent API Endpoints - AI Agent with Tool Execution

This module provides endpoints for AI agent operations using LlamaIndex ReActAgent
to execute tools like Gmail, Drive, and Calendar operations.

Endpoints:
- POST /execute: Execute agent task with tool access
- GET /health: Agent service health check
- GET /available-tools: List available tools for current user

Architecture:
- Integrates Google OAuth credentials with LlamaIndex tools
- Uses ReActAgent for multi-step reasoning and tool execution
- Supports Gmail, Drive, and Calendar operations
- Automatic tool selection based on user query
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ...core.jwt_auth import get_current_user_from_token
from ...api.v1.google_api import get_user_google_credentials
from ...llamaindex.services.llm_factory import llm_factory, TaskType
from ...llamaindex.tools.gmail_tools import create_gmail_tools
from ...llamaindex.tools.drive_tools import create_drive_tools
from ...llamaindex.tools.calendar_tools import create_calendar_tools

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])


class AgentRequest(BaseModel):
    """Request model for agent execution"""
    task: str = Field(..., description="Natural language task description for the agent")
    model: Optional[str] = Field(None, description="LLM model to use (default: auto-select)")
    temperature: float = Field(0.7, ge=0, le=2, description="LLM temperature")
    max_iterations: int = Field(10, ge=1, le=20, description="Max agent iterations")
    verbose: bool = Field(False, description="Enable verbose logging")
    account_email: Optional[str] = Field(None, description="Specific Google account to use")


class AgentResponse(BaseModel):
    """Response model for agent execution"""
    success: bool
    result: str
    reasoning_steps: Optional[List[Dict[str, Any]]] = None
    tools_used: List[str]
    model_used: str
    execution_time_ms: float


@router.post("/execute", response_model=AgentResponse)
async def execute_agent_task(
    request: AgentRequest,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Execute an AI agent task with access to Google tools.

    The agent can:
    - Search and read Gmail messages
    - List and manage Google Drive files
    - View Google Calendar events
    - Perform multi-step reasoning to accomplish complex tasks

    Example tasks:
    - "Find unread emails from john@example.com and summarize them"
    - "Search my Drive for PDF files modified this week"
    - "What meetings do I have tomorrow?"
    - "Find the email about the project deadline and tell me the date"

    Example:
    ```json
    {
        "task": "Find unread emails from my boss and summarize them",
        "model": "gpt-4o",
        "verbose": true
    }
    ```
    """
    import time
    start_time = time.time()

    try:
        user_id = str(current_user["id"])
        logger.info(f"Executing agent task for user {user_id}: {request.task}")

        # Get Google credentials for the user
        try:
            credentials = await get_user_google_credentials(
                user_id,
                account_email=request.account_email
            )
        except HTTPException as e:
            raise HTTPException(
                status_code=401,
                detail=f"Google authentication required. Please connect your Google account in Settings. ({e.detail})"
            )

        # Create tools with user's credentials
        tools = []
        tools_names = []

        try:
            gmail_tools = create_gmail_tools(credentials)
            tools.extend(gmail_tools)
            tools_names.extend([t.metadata.name for t in gmail_tools])
            logger.info(f"✅ Loaded {len(gmail_tools)} Gmail tools")
        except Exception as e:
            logger.warning(f"⚠️  Failed to load Gmail tools: {e}")

        try:
            drive_tools = create_drive_tools(credentials)
            tools.extend(drive_tools)
            tools_names.extend([t.metadata.name for t in drive_tools])
            logger.info(f"✅ Loaded {len(drive_tools)} Drive tools")
        except Exception as e:
            logger.warning(f"⚠️  Failed to load Drive tools: {e}")

        try:
            calendar_tools = create_calendar_tools(credentials)
            tools.extend(calendar_tools)
            tools_names.extend([t.metadata.name for t in calendar_tools])
            logger.info(f"✅ Loaded {len(calendar_tools)} Calendar tools")
        except Exception as e:
            logger.warning(f"⚠️  Failed to load Calendar tools: {e}")

        if not tools:
            raise HTTPException(
                status_code=500,
                detail="No tools available. Please check Google API configuration."
            )

        logger.info(f"Total tools loaded: {len(tools)}")

        # Get LLM for agent
        model_id = request.model or llm_factory.recommend_model_for_task(TaskType.TOOL_USE)
        llm = llm_factory.create_llm(
            model_id=model_id,
            temperature=request.temperature
        )

        # Create ReActAgent
        from llama_index.core.agent import ReActAgent

        agent = ReActAgent.from_tools(
            tools=tools,
            llm=llm,
            verbose=request.verbose,
            max_iterations=request.max_iterations
        )

        logger.info(f"🤖 Agent created with {len(tools)} tools, using model {model_id}")

        # Execute agent task
        logger.info(f"▶️  Executing task: {request.task}")
        response = await agent.achat(request.task)

        # Extract reasoning steps if available
        reasoning_steps = []
        if hasattr(response, 'source_nodes'):
            for node in response.source_nodes:
                reasoning_steps.append({
                    "step": node.metadata.get("step", ""),
                    "action": node.metadata.get("action", ""),
                    "observation": node.metadata.get("observation", "")
                })

        # Calculate execution time
        execution_time = (time.time() - start_time) * 1000

        result_text = str(response)

        logger.info(f"✅ Agent task completed in {execution_time:.2f}ms")

        return AgentResponse(
            success=True,
            result=result_text,
            reasoning_steps=reasoning_steps if reasoning_steps else None,
            tools_used=tools_names,
            model_used=model_id,
            execution_time_ms=round(execution_time, 2)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Agent execution error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Agent execution failed: {str(e)}"
        )


@router.get("/available-tools")
async def get_available_tools(
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Get list of available tools for the current user.

    Returns tool names and descriptions based on connected Google accounts.
    """
    try:
        user_id = str(current_user["id"])

        # Check if user has Google credentials
        try:
            credentials = await get_user_google_credentials(user_id)
            has_google_auth = True
        except:
            has_google_auth = False

        tools_info = []

        if has_google_auth:
            # Gmail tools
            tools_info.extend([
                {
                    "name": "search_gmail_messages",
                    "description": "Search Gmail messages using Gmail search operators",
                    "category": "gmail",
                    "enabled": True
                },
                {
                    "name": "get_gmail_message",
                    "description": "Get detailed information about a specific Gmail message",
                    "category": "gmail",
                    "enabled": True
                }
            ])

            # Drive tools
            tools_info.extend([
                {
                    "name": "search_drive_files",
                    "description": "Search Google Drive files and folders",
                    "category": "drive",
                    "enabled": True
                },
                {
                    "name": "get_drive_file",
                    "description": "Get detailed information about a specific Drive file",
                    "category": "drive",
                    "enabled": True
                }
            ])

            # Calendar tools
            tools_info.extend([
                {
                    "name": "list_calendar_events",
                    "description": "List upcoming calendar events",
                    "category": "calendar",
                    "enabled": True
                },
                {
                    "name": "get_calendar_event",
                    "description": "Get detailed information about a specific calendar event",
                    "category": "calendar",
                    "enabled": True
                }
            ])

        return {
            "google_authenticated": has_google_auth,
            "total_tools": len(tools_info),
            "tools": tools_info,
            "categories": list(set(t["category"] for t in tools_info))
        }

    except Exception as e:
        logger.error(f"❌ Get tools error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get available tools: {str(e)}"
        )


@router.get("/health")
async def agent_health_check():
    """Health check endpoint for agent service"""
    try:
        # Check if agent can be created
        from llama_index.core.agent import ReActAgent

        return {
            "status": "healthy",
            "service": "agent",
            "version": "1.0.0",
            "llamaindex_enabled": True,
            "react_agent_available": True,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "degraded",
            "service": "agent",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

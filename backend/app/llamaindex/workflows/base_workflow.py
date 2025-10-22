"""
Base Workflow for LlamaIndex Integration

Provides the foundation for all workflow types including chat, tool, and RAG workflows.
Uses LlamaIndex's Workflow abstraction for orchestrating multi-step operations.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, AsyncIterator
from enum import Enum
from datetime import datetime, timezone

from llama_index.core.workflow import (
    Workflow,
    StartEvent,
    StopEvent,
    step,
    Context,
)
from llama_index.core.llms import ChatMessage, MessageRole

logger = logging.getLogger(__name__)


class WorkflowType(str, Enum):
    """Types of workflows supported."""
    CHAT = "chat"
    TOOL = "tool"
    RAG = "rag"
    HYBRID = "hybrid"  # Combines multiple workflow types


class WorkflowState(str, Enum):
    """Workflow execution states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowEvent:
    """Base event for workflow operations."""

    def __init__(
        self,
        event_type: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.event_type = event_type
        self.data = data
        self.metadata = metadata or {}
        self.timestamp = datetime.now(timezone.utc)


class WorkflowContext:
    """
    Context for workflow execution.

    Stores state, conversation history, and execution metadata
    across workflow steps.
    """

    def __init__(
        self,
        user_id: str,
        conversation_id: str,
        workflow_type: WorkflowType,
    ):
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.workflow_type = workflow_type
        self.state = WorkflowState.PENDING
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = self.created_at

        # Workflow data
        self.messages: List[ChatMessage] = []
        self.events: List[WorkflowEvent] = []
        self.metadata: Dict[str, Any] = {}
        self.errors: List[str] = []

    def add_message(
        self,
        role: MessageRole,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a message to the conversation history."""
        message = ChatMessage(
            role=role,
            content=content,
            additional_kwargs=metadata or {},
        )
        self.messages.append(message)
        self.updated_at = datetime.now(timezone.utc)

    def add_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add an event to the workflow history."""
        event = WorkflowEvent(event_type, data, metadata)
        self.events.append(event)
        self.updated_at = datetime.now(timezone.utc)

    def add_error(self, error: str) -> None:
        """Add an error to the workflow context."""
        self.errors.append(error)
        self.state = WorkflowState.FAILED
        self.updated_at = datetime.now(timezone.utc)

    def set_state(self, state: WorkflowState) -> None:
        """Update workflow state."""
        self.state = state
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for serialization."""
        return {
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "workflow_type": self.workflow_type.value,
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "messages": [
                {
                    "role": msg.role.value,
                    "content": msg.content,
                    "metadata": msg.additional_kwargs,
                }
                for msg in self.messages
            ],
            "events": [
                {
                    "event_type": event.event_type,
                    "data": event.data,
                    "metadata": event.metadata,
                    "timestamp": event.timestamp.isoformat(),
                }
                for event in self.events
            ],
            "metadata": self.metadata,
            "errors": self.errors,
        }


class BaseWorkflowInput:
    """Base input for all workflows."""

    def __init__(
        self,
        user_id: str,
        conversation_id: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.message = message
        self.metadata = metadata or {}


class BaseWorkflowOutput:
    """Base output for all workflows."""

    def __init__(
        self,
        response: str,
        context: WorkflowContext,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.response = response
        self.context = context
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert output to dictionary."""
        return {
            "response": self.response,
            "context": self.context.to_dict(),
            "metadata": self.metadata,
        }


class BaseAgentWorkflow(Workflow):
    """
    Base workflow class for all agent workflows.

    Provides common functionality for chat, tool, and RAG workflows
    including state management, error handling, and event tracking.
    """

    def __init__(
        self,
        workflow_type: WorkflowType,
        timeout: float = 300.0,  # 5 minutes default
        verbose: bool = False,
    ):
        super().__init__(timeout=timeout, verbose=verbose)
        self.workflow_type = workflow_type

    async def create_context(
        self,
        user_id: str,
        conversation_id: str,
    ) -> WorkflowContext:
        """Create a new workflow context."""
        context = WorkflowContext(
            user_id=user_id,
            conversation_id=conversation_id,
            workflow_type=self.workflow_type,
        )
        context.set_state(WorkflowState.RUNNING)
        return context

    async def handle_error(
        self,
        context: WorkflowContext,
        error: Exception,
        step_name: str,
    ) -> None:
        """Handle errors during workflow execution."""
        error_msg = f"Error in {step_name}: {str(error)}"
        logger.error(error_msg, exc_info=True)
        context.add_error(error_msg)
        context.set_state(WorkflowState.FAILED)

    async def log_step(
        self,
        context: WorkflowContext,
        step_name: str,
        data: Dict[str, Any],
    ) -> None:
        """Log a workflow step for debugging and auditing."""
        logger.debug(
            f"Workflow step: {step_name}, "
            f"conversation={context.conversation_id}, "
            f"data={data}"
        )
        context.add_event(
            event_type=f"step_{step_name}",
            data=data,
        )


class WorkflowExecutionResult:
    """Result of workflow execution."""

    def __init__(
        self,
        success: bool,
        output: Optional[BaseWorkflowOutput] = None,
        error: Optional[str] = None,
        execution_time: Optional[float] = None,
    ):
        self.success = success
        self.output = output
        self.error = error
        self.execution_time = execution_time

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        result = {
            "success": self.success,
            "execution_time": self.execution_time,
        }

        if self.output:
            result["output"] = self.output.to_dict()

        if self.error:
            result["error"] = self.error

        return result

"""
Chat Workflow for LlamaIndex Integration

Handles conversational interactions with LLM, including context management,
memory integration, and streaming responses.
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, Any

from llama_index.core.workflow import StartEvent, StopEvent, step, Context
from llama_index.core.llms import ChatMessage, MessageRole

from .base_workflow import (
    BaseAgentWorkflow,
    WorkflowType,
    WorkflowContext,
    BaseWorkflowInput,
    BaseWorkflowOutput,
)
from ..services.llm_factory import llm_factory, TaskType
from ..memory.conversation_memory import ConversationMemory

logger = logging.getLogger(__name__)


# Custom events for workflow steps (defined early for forward references)
class PrepareContextEvent:
    """Event triggered after context preparation."""
    pass


class BuildMessagesEvent:
    """Event triggered after building messages."""
    pass


class GenerateResponseEvent:
    """Event triggered after generating response."""
    pass


class ChatWorkflowInput(BaseWorkflowInput):
    """Input for chat workflow."""

    def __init__(
        self,
        user_id: str,
        conversation_id: str,
        message: str,
        system_prompt: Optional[str] = None,
        model_id: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        include_memory: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(user_id, conversation_id, message, metadata)
        self.system_prompt = system_prompt
        self.model_id = model_id
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.include_memory = include_memory


class ChatWorkflowOutput(BaseWorkflowOutput):
    """Output for chat workflow."""

    def __init__(
        self,
        response: str,
        context: WorkflowContext,
        model_used: str,
        tokens_used: Optional[Dict[str, int]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(response, context, metadata)
        self.model_used = model_used
        self.tokens_used = tokens_used or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert output to dictionary."""
        result = super().to_dict()
        result.update({
            "model_used": self.model_used,
            "tokens_used": self.tokens_used,
        })
        return result


class ChatWorkflow(BaseAgentWorkflow):
    """
    Workflow for handling conversational interactions.

    Features:
    - LLM integration with multiple model support
    - Conversation memory management
    - Context-aware responses
    - Token tracking
    """

    def __init__(
        self,
        memory_manager: Optional[Any] = None,
        default_system_prompt: Optional[str] = None,
        timeout: float = 300.0,
        verbose: bool = False,
    ):
        super().__init__(
            workflow_type=WorkflowType.CHAT,
            timeout=timeout,
            verbose=verbose,
        )
        self.memory_manager = memory_manager
        self.default_system_prompt = default_system_prompt or (
            "You are a helpful AI assistant. "
            "Provide clear, accurate, and concise responses."
        )

    @step
    async def prepare_context(
        self,
        ctx: Context,
        ev: StartEvent,
    ) -> "PrepareContextEvent":
        """
        Step 1: Prepare workflow context and load conversation memory.
        """
        workflow_input: ChatWorkflowInput = ev.input

        # Create workflow context
        workflow_context = await self.create_context(
            user_id=workflow_input.user_id,
            conversation_id=workflow_input.conversation_id,
        )

        # Store input in context
        await ctx.set("workflow_input", workflow_input)
        await ctx.set("workflow_context", workflow_context)

        await self.log_step(
            workflow_context,
            "prepare_context",
            {
                "user_id": workflow_input.user_id,
                "conversation_id": workflow_input.conversation_id,
                "include_memory": workflow_input.include_memory,
            },
        )

        # Load conversation memory if enabled
        memory: Optional[ConversationMemory] = None
        if workflow_input.include_memory and self.memory_manager:
            memory = self.memory_manager.get_memory(
                user_id=workflow_input.user_id,
                conversation_id=workflow_input.conversation_id,
            )
            await memory.load_from_database()

        await ctx.set("memory", memory)

        return PrepareContextEvent()

    @step
    async def build_messages(
        self,
        ctx: Context,
        ev: "PrepareContextEvent",
    ) -> "BuildMessagesEvent":
        """
        Step 2: Build message list for LLM including system prompt and history.
        """
        workflow_input: ChatWorkflowInput = await ctx.get("workflow_input")
        workflow_context: WorkflowContext = await ctx.get("workflow_context")
        memory: Optional[ConversationMemory] = await ctx.get("memory")

        messages: list[ChatMessage] = []

        # Add system prompt
        system_prompt = workflow_input.system_prompt or self.default_system_prompt
        messages.append(
            ChatMessage(role=MessageRole.SYSTEM, content=system_prompt)
        )

        # Add conversation history from memory
        if memory:
            history_messages = await memory.get_messages()
            for msg in history_messages:
                role = MessageRole(msg["role"])
                messages.append(
                    ChatMessage(
                        role=role,
                        content=msg["content"],
                        additional_kwargs=msg.get("metadata", {}),
                    )
                )

        # Add current user message
        messages.append(
            ChatMessage(role=MessageRole.USER, content=workflow_input.message)
        )

        # Store in workflow context
        workflow_context.messages = messages

        await self.log_step(
            workflow_context,
            "build_messages",
            {
                "message_count": len(messages),
                "has_history": bool(memory),
            },
        )

        await ctx.set("messages", messages)

        return BuildMessagesEvent()

    @step
    async def generate_response(
        self,
        ctx: Context,
        ev: "BuildMessagesEvent",
    ) -> "GenerateResponseEvent":
        """
        Step 3: Generate LLM response.
        """
        workflow_input: ChatWorkflowInput = await ctx.get("workflow_input")
        workflow_context: WorkflowContext = await ctx.get("workflow_context")
        messages: list[ChatMessage] = await ctx.get("messages")

        try:
            # Get model
            model_id = workflow_input.model_id or llm_factory.recommend_model_for_task(
                TaskType.CHAT
            )

            # Create LLM instance
            llm = llm_factory.create_llm(
                model_id=model_id,
                temperature=workflow_input.temperature,
                max_tokens=workflow_input.max_tokens,
            )

            await self.log_step(
                workflow_context,
                "generate_response",
                {
                    "model": model_id,
                    "temperature": workflow_input.temperature,
                    "max_tokens": workflow_input.max_tokens,
                },
            )

            # Generate response
            chat_response = await llm.achat(messages)
            response_text = chat_response.message.content

            # Store response
            await ctx.set("response_text", response_text)
            await ctx.set("model_used", model_id)

            # Add assistant response to context
            workflow_context.add_message(
                role=MessageRole.ASSISTANT,
                content=response_text,
            )

            return GenerateResponseEvent()

        except Exception as e:
            await self.handle_error(workflow_context, e, "generate_response")
            raise

    @step
    async def save_to_memory(
        self,
        ctx: Context,
        ev: "GenerateResponseEvent",
    ) -> StopEvent:
        """
        Step 4: Save conversation to memory and return result.
        """
        workflow_input: ChatWorkflowInput = await ctx.get("workflow_input")
        workflow_context: WorkflowContext = await ctx.get("workflow_context")
        memory: Optional[ConversationMemory] = await ctx.get("memory")
        response_text: str = await ctx.get("response_text")
        model_used: str = await ctx.get("model_used")

        try:
            # Save to memory if enabled
            if memory:
                # Save user message
                await memory.add_message(
                    role="user",
                    content=workflow_input.message,
                    metadata=workflow_input.metadata,
                )

                # Save assistant response
                await memory.add_message(
                    role="assistant",
                    content=response_text,
                    metadata={"model": model_used},
                )

            await self.log_step(
                workflow_context,
                "save_to_memory",
                {"saved": bool(memory)},
            )

            # Create output
            output = ChatWorkflowOutput(
                response=response_text,
                context=workflow_context,
                model_used=model_used,
                metadata=workflow_input.metadata,
            )

            return StopEvent(result=output)

        except Exception as e:
            await self.handle_error(workflow_context, e, "save_to_memory")
            raise

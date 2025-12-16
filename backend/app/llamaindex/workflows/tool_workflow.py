"""
Tool Workflow for LlamaIndex Integration

Handles tool-based operations using LlamaIndex agents with function calling.
Integrates Google services (Gmail, Drive, Calendar) as tools for the agent.
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List

from llama_index.core.workflow import StartEvent, StopEvent, step, Context, Event
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import BaseTool

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
class PrepareAgentEvent(Event):
    """Event triggered after agent preparation."""
    pass


class BuildContextEvent(Event):
    """Event triggered after building context."""
    pass


class ExecuteAgentEvent(Event):
    """Event triggered after agent execution."""
    pass


class ToolWorkflowInput(BaseWorkflowInput):
    """Input for tool workflow."""

    def __init__(
        self,
        user_id: str,
        conversation_id: str,
        message: str,
        tools: List[BaseTool],
        model_id: Optional[str] = None,
        max_iterations: int = 10,
        include_memory: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(user_id, conversation_id, message, metadata)
        self.tools = tools
        self.model_id = model_id
        self.max_iterations = max_iterations
        self.include_memory = include_memory


class ToolWorkflowOutput(BaseWorkflowOutput):
    """Output for tool workflow."""

    def __init__(
        self,
        response: str,
        context: WorkflowContext,
        model_used: str,
        tools_used: List[str],
        iterations: int,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(response, context, metadata)
        self.model_used = model_used
        self.tools_used = tools_used
        self.iterations = iterations

    def to_dict(self) -> Dict[str, Any]:
        """Convert output to dictionary."""
        result = super().to_dict()
        result.update({
            "model_used": self.model_used,
            "tools_used": self.tools_used,
            "iterations": self.iterations,
        })
        return result


class ToolWorkflow(BaseAgentWorkflow):
    """
    Workflow for handling tool-based operations using ReAct agent.

    Features:
    - Multi-tool function calling
    - ReAct (Reasoning + Acting) pattern
    - Tool execution tracking
    - Iterative problem solving
    """

    def __init__(
        self,
        memory_manager: Optional[Any] = None,
        default_system_prompt: Optional[str] = None,
        timeout: float = 600.0,  # 10 minutes for tool operations
        verbose: bool = False,
    ):
        super().__init__(
            workflow_type=WorkflowType.TOOL,
            timeout=timeout,
            verbose=verbose,
        )
        self.memory_manager = memory_manager
        self.verbose = verbose
        self.default_system_prompt = default_system_prompt or (
            "You are a helpful AI assistant with access to various tools. "
            "Use the available tools to help answer questions and complete tasks. "
            "Think step by step about which tools to use and in what order."
        )

    @step
    async def prepare_agent(
        self,
        ctx: Context,
        ev: StartEvent,
    ) -> "PrepareAgentEvent":
        """
        Step 1: Prepare workflow context and create ReAct agent.
        """
        workflow_input: ToolWorkflowInput = ev.input

        # Create workflow context
        workflow_context = await self.create_context(
            user_id=workflow_input.user_id,
            conversation_id=workflow_input.conversation_id,
        )

        # Store input in context
        await ctx.store.set("workflow_input", workflow_input)
        await ctx.store.set("workflow_context", workflow_context)

        await self.log_step(
            workflow_context,
            "prepare_agent",
            {
                "user_id": workflow_input.user_id,
                "conversation_id": workflow_input.conversation_id,
                "tool_count": len(workflow_input.tools),
                "max_iterations": workflow_input.max_iterations,
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

        await ctx.store.set("memory", memory)

        # Get model for tool use
        model_id = workflow_input.model_id or llm_factory.recommend_model_for_task(
            TaskType.TOOL_USE
        )

        # Create LLM instance
        llm = llm_factory.create_llm(
            model_id=model_id,
            temperature=0.1,  # Lower temperature for more deterministic tool use
        )

        await ctx.store.set("model_used", model_id)

        # Get system prompt from input or use default
        system_prompt = (
            workflow_input.system_prompt
            if hasattr(workflow_input, "system_prompt") and workflow_input.system_prompt
            else self.default_system_prompt
        )

        # Create ReAct agent
        agent = ReActAgent(
            name="Tool Agent",
            description="An AI assistant that can use various tools to help answer questions",
            system_prompt=system_prompt,
            tools=workflow_input.tools,
            llm=llm,
            verbose=self.verbose,
        )

        await ctx.store.set("agent", agent)
        await ctx.store.set("max_iterations", workflow_input.max_iterations)

        return PrepareAgentEvent()

    @step
    async def build_context(
        self,
        ctx: Context,
        ev: "PrepareAgentEvent",
    ) -> "BuildContextEvent":
        """
        Step 2: Build context from conversation history.
        """
        workflow_input: ToolWorkflowInput = await ctx.store.get("workflow_input")
        workflow_context: WorkflowContext = await ctx.store.get("workflow_context")
        memory: Optional[ConversationMemory] = await ctx.store.get("memory")

        # Build context string from memory
        context_parts = []

        if memory and memory.message_count > 0:
            # Get recent conversation history
            history_messages = await memory.get_messages(limit=5)
            if history_messages:
                context_parts.append("Recent conversation:")
                for msg in history_messages:
                    context_parts.append(f"{msg['role']}: {msg['content']}")

            # Add summary if available
            if memory.summary:
                context_parts.append(f"\nConversation summary: {memory.summary}")

        context_str = "\n".join(context_parts) if context_parts else None

        await self.log_step(
            workflow_context,
            "build_context",
            {
                "has_context": bool(context_str),
                "context_length": len(context_str) if context_str else 0,
            },
        )

        await ctx.store.set("context_str", context_str)

        return BuildContextEvent()

    @step
    async def execute_agent(
        self,
        ctx: Context,
        ev: "BuildContextEvent",
    ) -> "ExecuteAgentEvent":
        """
        Step 3: Execute agent with tools to answer query.
        """
        workflow_input: ToolWorkflowInput = await ctx.store.get("workflow_input")
        workflow_context: WorkflowContext = await ctx.store.get("workflow_context")
        agent: ReActAgent = await ctx.store.get("agent")
        context_str: Optional[str] = await ctx.store.get("context_str")
        max_iterations: int = await ctx.store.get("max_iterations")

        try:
            # Build query with context
            query = workflow_input.message
            if context_str:
                query = f"{context_str}\n\nUser query: {query}"

            await self.log_step(
                workflow_context,
                "execute_agent",
                {"query_length": len(query)},
            )

            # Execute agent
            handler = agent.run(
                user_msg=query,
                max_iterations=max_iterations,
            )
            result = await handler

            # Extract tool usage information
            tools_used = []
            if hasattr(result, "tool_calls") and result.tool_calls:
                for tool_call in result.tool_calls:
                    if hasattr(tool_call, "tool_name"):
                        tools_used.append(tool_call.tool_name)
                    elif hasattr(tool_call, "name"):
                        tools_used.append(tool_call.name)

            # Get response text
            if hasattr(result, "response"):
                # result.response is a ChatMessage, extract content
                response_text = result.response.content if hasattr(result.response, "content") else str(result.response)
            else:
                response_text = str(result)

            # Count iterations (approximate from messages if available)
            iterations = 0
            if hasattr(result, "raw") and result.raw and hasattr(result.raw, "messages"):
                iterations = len(result.raw.messages) // 2  # Approximate

            await ctx.store.set("response_text", response_text)
            await ctx.store.set("tools_used", tools_used)
            await ctx.store.set("iterations", iterations)

            # Add messages to context
            workflow_context.add_message(
                role=MessageRole.USER,
                content=workflow_input.message,
            )
            workflow_context.add_message(
                role=MessageRole.ASSISTANT,
                content=response_text,
                metadata={"tools_used": tools_used},
            )

            return ExecuteAgentEvent()

        except Exception as e:
            await self.handle_error(workflow_context, e, "execute_agent")
            raise

    @step
    async def save_to_memory(
        self,
        ctx: Context,
        ev: "ExecuteAgentEvent",
    ) -> StopEvent:
        """
        Step 4: Save conversation to memory and return result.
        """
        workflow_input: ToolWorkflowInput = await ctx.store.get("workflow_input")
        workflow_context: WorkflowContext = await ctx.store.get("workflow_context")
        memory: Optional[ConversationMemory] = await ctx.store.get("memory")
        response_text: str = await ctx.store.get("response_text")
        model_used: str = await ctx.store.get("model_used")
        tools_used: List[str] = await ctx.store.get("tools_used")
        iterations: int = await ctx.store.get("iterations")

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
                    metadata={
                        "model": model_used,
                        "tools_used": tools_used,
                        "iterations": iterations,
                    },
                )

            await self.log_step(
                workflow_context,
                "save_to_memory",
                {
                    "saved": bool(memory),
                    "tools_used": tools_used,
                },
            )

            # Create output
            output = ToolWorkflowOutput(
                response=response_text,
                context=workflow_context,
                model_used=model_used,
                tools_used=tools_used,
                iterations=iterations,
                metadata=workflow_input.metadata,
            )

            return StopEvent(result=output)

        except Exception as e:
            await self.handle_error(workflow_context, e, "save_to_memory")
            raise

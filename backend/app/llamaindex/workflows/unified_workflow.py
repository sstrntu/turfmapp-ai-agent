"""
Unified Workflow - Intelligent Tool Selection and Routing

This workflow combines RAG, Gmail, Drive, and Calendar tools into a single
intelligent agent that decides which tools to use based on the user's query.

Uses LlamaIndex's ReActAgent for autonomous tool selection.
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
    WorkflowState,
    WorkflowContext,
    BaseWorkflowInput,
    BaseWorkflowOutput,
)
from ..services.llm_factory import llm_factory, TaskType
from ..memory.conversation_memory import ConversationMemory
from ..memory.user_memory import UserMemory

logger = logging.getLogger(__name__)


# Custom events
class LoadMemoryEvent(Event):
    """Event triggered after loading memory."""
    pass


class PrepareToolsEvent(Event):
    """Event triggered after preparing tools."""
    pass


class ExecuteAgentEvent(Event):
    """Event triggered after agent execution."""
    pass


class UnifiedWorkflowInput(BaseWorkflowInput):
    """Input for unified workflow."""

    def __init__(
        self,
        user_id: str,
        conversation_id: str,
        message: str,
        model_id: Optional[str] = None,
        temperature: float = 0.7,
        max_iterations: int = 10,
        include_memory: bool = True,
        google_credentials: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(user_id, conversation_id, message, metadata)
        self.model_id = model_id
        self.temperature = temperature
        self.max_iterations = max_iterations
        self.include_memory = include_memory
        self.google_credentials = google_credentials


class UnifiedWorkflowOutput(BaseWorkflowOutput):
    """Output for unified workflow."""

    def __init__(
        self,
        response: str,
        context: WorkflowContext,
        model_used: str,
        tools_used: List[str],
        reasoning_steps: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(response, context, metadata)
        self.model_used = model_used
        self.tools_used = tools_used
        self.reasoning_steps = reasoning_steps

    def to_dict(self) -> Dict[str, Any]:
        """Convert output to dictionary."""
        result = super().to_dict()
        result.update({
            "model_used": self.model_used,
            "tools_used": self.tools_used,
            "reasoning_steps": self.reasoning_steps,
        })
        return result


class UnifiedWorkflow(BaseAgentWorkflow):
    """
    Unified workflow that intelligently routes to tools.

    Features:
    - Automatic tool selection based on query
    - RAG for document queries
    - Gmail tools for email tasks
    - Drive tools for file management
    - Calendar tools for scheduling
    - Conversation memory integration
    - User memory integration
    """

    def __init__(
        self,
        db_pool,
        memory_manager: Optional[Any] = None,
        timeout: float = 600.0,
        verbose: bool = False,
    ):
        super().__init__(
            workflow_type=WorkflowType.HYBRID,
            timeout=timeout,
            verbose=verbose,
        )
        self.db_pool = db_pool
        self.memory_manager = memory_manager
        self.verbose = verbose

    @step
    async def load_memory(
        self,
        ctx: Context,
        ev: StartEvent,
    ) -> LoadMemoryEvent:
        """
        Step 1: Load user and conversation memory.
        """
        workflow_input: UnifiedWorkflowInput = ev.input

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
            "load_memory",
            {"user_id": workflow_input.user_id},
        )

        # Load user-level memory (cross-conversation facts)
        user_memory = UserMemory(
            user_id=workflow_input.user_id,
            db_pool=self.db_pool,
        )
        await user_memory.load_from_database()
        await ctx.store.set("user_memory", user_memory)

        # Load conversation memory
        conversation_memory: Optional[ConversationMemory] = None
        if workflow_input.include_memory and self.memory_manager:
            conversation_memory = self.memory_manager.get_memory(
                user_id=workflow_input.user_id,
                conversation_id=workflow_input.conversation_id,
            )
            await conversation_memory.load_from_database()

        await ctx.store.set("conversation_memory", conversation_memory)

        return LoadMemoryEvent()

    @step
    async def prepare_tools(
        self,
        ctx: Context,
        ev: LoadMemoryEvent,
    ) -> PrepareToolsEvent:
        """
        Step 2: Prepare all available tools (RAG, Gmail, Drive, Calendar).
        """
        workflow_input: UnifiedWorkflowInput = await ctx.store.get("workflow_input")
        workflow_context: WorkflowContext = await ctx.store.get("workflow_context")

        tools: List[BaseTool] = []

        # 1. Add RAG tools (always available if user has documents)
        try:
            from ..rag import PgVectorStore
            from ..tools.rag_tools import create_rag_tools

            # Create RAG LLM (cheaper model for RAG)
            rag_llm = llm_factory.create_llm(
                model_id="gpt-4o-mini",
                temperature=0.3,
            )

            vector_store = PgVectorStore(db_pool=self.db_pool)
            rag_tools = create_rag_tools(
                user_id=workflow_input.user_id,
                db_pool=self.db_pool,
                vector_store=vector_store,
                llm=rag_llm,
            )
            tools.extend(rag_tools)
            logger.info(f"Added {len(rag_tools)} RAG tools")
        except Exception as e:
            logger.warning(f"Failed to add RAG tools: {e}")

        # 2. Add Google tools (if credentials available)
        if workflow_input.google_credentials:
            try:
                from ..tools import (
                    create_gmail_tools,
                    create_drive_tools,
                    create_calendar_tools,
                )

                gmail_tools = create_gmail_tools(workflow_input.google_credentials)
                drive_tools = create_drive_tools(workflow_input.google_credentials)
                calendar_tools = create_calendar_tools(workflow_input.google_credentials)

                tools.extend(gmail_tools)
                tools.extend(drive_tools)
                tools.extend(calendar_tools)

                logger.info(
                    f"Added Google tools: {len(gmail_tools)} Gmail, "
                    f"{len(drive_tools)} Drive, {len(calendar_tools)} Calendar"
                )
            except Exception as e:
                logger.warning(f"Failed to add Google tools: {e}")

        await ctx.store.set("tools", tools)

        # Log available tools
        tool_names = [tool.metadata.name if hasattr(tool, 'metadata') else str(tool) for tool in tools]
        logger.info(f"📦 Available tools ({len(tools)}): {tool_names}")

        await self.log_step(
            workflow_context,
            "prepare_tools",
            {"tool_count": len(tools), "tools": tool_names},
        )

        return PrepareToolsEvent()

    @step
    async def execute_agent(
        self,
        ctx: Context,
        ev: PrepareToolsEvent,
    ) -> ExecuteAgentEvent:
        """
        Step 3: Execute ReActAgent with all tools.

        The agent will:
        1. Analyze the user's query
        2. Decide which tools (if any) to use
        3. Execute tools in appropriate order
        4. Generate final response
        """
        workflow_input: UnifiedWorkflowInput = await ctx.store.get("workflow_input")
        workflow_context: WorkflowContext = await ctx.store.get("workflow_context")
        user_memory: UserMemory = await ctx.store.get("user_memory")
        conversation_memory: Optional[ConversationMemory] = await ctx.store.get("conversation_memory")
        tools: List[BaseTool] = await ctx.store.get("tools")

        try:
            # Get model for reasoning and tool use
            model_id = workflow_input.model_id or llm_factory.recommend_model_for_task(
                TaskType.TOOL_USE
            )

            # Create LLM
            llm = llm_factory.create_llm(
                model_id=model_id,
                temperature=workflow_input.temperature,
            )

            await ctx.store.set("model_used", model_id)

            # Build system prompt with memory context
            system_prompt_parts = []

            # Add user memory context
            user_context = user_memory.get_context_string()
            logger.info(f"🧠 User memory facts: {user_memory.facts}")
            logger.info(f"🧠 User context string (length={len(user_context)}): {user_context}")
            if user_context:
                system_prompt_parts.append(user_context)

            # Add conversation context
            if conversation_memory and conversation_memory.message_count > 0:
                recent_messages = await conversation_memory.get_messages(limit=5)
                if recent_messages:
                    system_prompt_parts.append("\n**Recent Conversation:**")
                    for msg in recent_messages[-3:]:  # Last 3 messages
                        system_prompt_parts.append(f"{msg['role']}: {msg['content']}")

            # Add agent instructions
            system_prompt_parts.append(
                "\n**Your Role:**\n"
                "You are a helpful AI assistant with access to various tools.\n\n"
                "**Decision Process:**\n"
                "1. First, check if you can answer using the User Information or Recent Conversation above\n"
                "2. If the answer is already available in that context, respond directly (no tools needed)\n"
                "3. If you need additional information not in the context, select the most appropriate tool(s)\n"
                "4. Use tools thoughtfully - only when they add value to your response\n\n"
                "**Available Tools:**\n"
                "Each tool has a specific purpose. Read tool descriptions carefully to choose the right one.\n\n"
                "Remember: The most efficient answer uses available context when possible, and tools when necessary."
            )

            system_prompt = "\n\n".join(system_prompt_parts)
            logger.info(f"🤖 Final system prompt:\n{system_prompt}\n{'='*80}")

            # Smart routing: Check if we can answer from context first (without tools)
            # This prevents the agent from being "tool-happy" for simple questions
            if user_context or (conversation_memory and conversation_memory.message_count > 0):
                logger.info("🧠 Checking if query can be answered from context alone...")

                # Use a lightweight LLM to check if context has the answer
                router_llm = llm_factory.create_llm(
                    model_id="gpt-4o-mini",
                    temperature=0.1,
                )

                router_prompt = f"""Given the following context about the user, can you answer this question: "{workflow_input.message}"?

{system_prompt}

Instructions:
- If the context above contains enough information to answer the question, respond with: YES: [your answer]
- If you need to search documents or use tools for more information, respond with: NO

Your response:"""

                router_response = await router_llm.achat([
                    ChatMessage(role=MessageRole.USER, content=router_prompt)
                ])
                router_text = router_response.message.content.strip()

                logger.info(f"🧠 Router decision: {router_text[:100]}...")

                # If router can answer from context, use that directly
                if router_text.startswith("YES:"):
                    response_text = router_text[4:].strip()
                    tools_used = []
                    reasoning_steps = [{
                        "role": "router",
                        "content": "Answered from user memory/context without tools"
                    }]

                    logger.info("✅ Answered from context without using tools")

                    await ctx.store.set("response_text", response_text)
                    await ctx.store.set("tools_used", tools_used)
                    await ctx.store.set("reasoning_steps", reasoning_steps)

                    return ExecuteAgentEvent()

            # If we get here, we need tools - create the agent
            if tools:
                # Use ReActAgent with tools
                agent = ReActAgent(
                    name="Unified Agent",
                    description="An AI assistant with access to various tools including RAG, Gmail, Drive, and Calendar",
                    system_prompt=system_prompt,
                    tools=tools,
                    llm=llm,
                    verbose=self.verbose,
                )

                await self.log_step(
                    workflow_context,
                    "execute_agent",
                    {"mode": "tool_agent", "tool_count": len(tools)},
                )

                # Execute agent
                handler = agent.run(
                    user_msg=workflow_input.message,
                    max_iterations=workflow_input.max_iterations,
                )
                result = await handler

                # Extract response text
                if hasattr(result, "response"):
                    # result.response is a ChatMessage, extract content
                    response_text = result.response.content if hasattr(result.response, "content") else str(result.response)
                else:
                    response_text = str(result)

                # Extract tool usage
                tools_used = []
                if hasattr(result, "tool_calls") and result.tool_calls:
                    for tool_call in result.tool_calls:
                        if hasattr(tool_call, "tool_name"):
                            tools_used.append(tool_call.tool_name)
                        elif hasattr(tool_call, "name"):
                            tools_used.append(tool_call.name)

                # Extract reasoning steps from raw messages
                reasoning_steps = []
                if hasattr(result, "raw") and result.raw:
                    if hasattr(result.raw, "messages"):
                        for msg in result.raw.messages[-5:]:  # Last 5 messages
                            reasoning_steps.append({
                                "role": str(msg.role) if hasattr(msg, "role") else "unknown",
                                "content": str(msg.content)[:200] if hasattr(msg, "content") else "",  # Truncate
                            })

            else:
                # No tools available, use direct LLM
                await self.log_step(
                    workflow_context,
                    "execute_agent",
                    {"mode": "direct_llm"},
                )

                messages = [
                    ChatMessage(role=MessageRole.SYSTEM, content=system_prompt),
                    ChatMessage(role=MessageRole.USER, content=workflow_input.message),
                ]

                response = await llm.achat(messages)
                response_text = response.message.content
                tools_used = []
                reasoning_steps = []

            await ctx.store.set("response_text", response_text)
            await ctx.store.set("tools_used", tools_used)
            await ctx.store.set("reasoning_steps", reasoning_steps)

            return ExecuteAgentEvent()

        except Exception as e:
            await self.handle_error(workflow_context, e, "execute_agent")
            raise

    @step
    async def save_and_respond(
        self,
        ctx: Context,
        ev: ExecuteAgentEvent,
    ) -> StopEvent:
        """
        Step 4: Save to memory and return response.
        """
        workflow_input: UnifiedWorkflowInput = await ctx.store.get("workflow_input")
        workflow_context: WorkflowContext = await ctx.store.get("workflow_context")
        conversation_memory: Optional[ConversationMemory] = await ctx.store.get("conversation_memory")
        user_memory: UserMemory = await ctx.store.get("user_memory")
        response_text: str = await ctx.store.get("response_text")
        model_used: str = await ctx.store.get("model_used")
        tools_used: List[str] = await ctx.store.get("tools_used")
        reasoning_steps: List[Dict[str, Any]] = await ctx.store.get("reasoning_steps")

        try:
            # Save to conversation memory
            if conversation_memory:
                await conversation_memory.add_message(
                    role="user",
                    content=workflow_input.message,
                    metadata=workflow_input.metadata,
                )

                await conversation_memory.add_message(
                    role="assistant",
                    content=response_text,
                    metadata={
                        "model": model_used,
                        "tools_used": tools_used,
                    },
                )

            # Extract user facts for user memory (background task)
            try:
                # Get LLM for fact extraction
                fact_llm = llm_factory.create_llm(
                    model_id="gpt-4o-mini",
                    temperature=0.3,
                )

                # Extract facts from recent conversation
                if conversation_memory:
                    messages_for_facts = await conversation_memory.get_messages(limit=10)
                    await user_memory.extract_facts_from_conversation(
                        messages=messages_for_facts,
                        conversation_id=workflow_input.conversation_id,
                        llm=fact_llm,
                    )
            except Exception as e:
                logger.warning(f"Failed to extract user facts: {e}")

            await self.log_step(
                workflow_context,
                "save_and_respond",
                {
                    "saved_to_memory": bool(conversation_memory),
                    "tools_used": tools_used,
                },
            )

            # Create output
            workflow_context.set_state(WorkflowState.COMPLETED)
            output = UnifiedWorkflowOutput(
                response=response_text,
                context=workflow_context,
                model_used=model_used,
                tools_used=tools_used,
                reasoning_steps=reasoning_steps,
                metadata=workflow_input.metadata,
            )

            return StopEvent(result=output)

        except Exception as e:
            await self.handle_error(workflow_context, e, "save_and_respond")
            raise

"""
Unified Workflow - Intelligent Tool Selection and Routing

This workflow combines RAG, Gmail, Drive, and Calendar tools into a single
intelligent agent that decides which tools to use based on the user's query.

Uses LlamaIndex's ReActAgent for autonomous tool selection.
"""

from __future__ import annotations

import logging
import asyncio
from typing import Optional, Dict, Any, List, Callable, Awaitable

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

# Type for event emitter callback
EventEmitter = Callable[[Dict[str, Any]], Awaitable[None]]


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
        event_emitter: Optional[EventEmitter] = None,
    ):
        super().__init__(user_id, conversation_id, message, metadata)
        self.model_id = model_id
        self.temperature = temperature
        self.max_iterations = max_iterations
        self.include_memory = include_memory
        self.google_credentials = google_credentials
        self.event_emitter = event_emitter


class UnifiedWorkflowOutput(BaseWorkflowOutput):
    """Output for unified workflow."""

    def __init__(
        self,
        response: str,
        context: WorkflowContext,
        model_used: str,
        tools_used: List[str],
        reasoning_steps: List[Dict[str, Any]],
        sources: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(response, context, metadata)
        self.model_used = model_used
        self.tools_used = tools_used
        self.reasoning_steps = reasoning_steps
        self.sources = sources or []

    def to_dict(self) -> Dict[str, Any]:
        """Convert output to dictionary."""
        result = super().to_dict()
        result.update({
            "model_used": self.model_used,
            "tools_used": self.tools_used,
            "reasoning_steps": self.reasoning_steps,
            "sources": self.sources,
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

    async def _emit_event(self, ctx: Context, event: Dict[str, Any]):
        """Emit a streaming event if emitter is available."""
        try:
            workflow_input: UnifiedWorkflowInput = await ctx.store.get("workflow_input")
            if workflow_input.event_emitter:
                await workflow_input.event_emitter(event)
        except Exception as e:
            logger.warning(f"Failed to emit event: {e}")

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

        # Emit event: Starting to load memory
        await self._emit_event(ctx, {
            'type': 'thought',
            'content': '🧠 Loading memory and context...'
        })

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

        # Emit event: Preparing tools
        await self._emit_event(ctx, {
            'type': 'thought',
            'content': '🔧 Preparing tools...'
        })

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

        # 2. Add Web Search tool (OpenAI or Claude)
        try:
            from llama_index.core.tools import FunctionTool
            from openai import AsyncOpenAI
            from anthropic import AsyncAnthropic
            import os

            # Get model to determine which search API to use
            model_id = workflow_input.model_id or "gpt-4o"
            is_claude = model_id.startswith("claude")

            # Storage for sources (accessed by workflow)
            web_search_sources = []

            async def web_search(query: str) -> str:
                """
                Search the web for current information, news, weather, sports scores, and real-time data.

                Use this tool when:
                - User asks about current events, news, or recent information
                - Questions about weather, sports scores, or time-sensitive data
                - Looking up facts that may have changed since your training data
                - User explicitly asks to "search the web" or "look up"

                Args:
                    query: Search query to find information on the web

                Returns:
                    Web search results with relevant information and sources
                """
                nonlocal web_search_sources

                # Emit event: Starting web search
                await self._emit_event(ctx, {
                    'type': 'tool_call',
                    'tool': 'web_search',
                    'input': query
                })

                try:
                    if is_claude:
                        # Use Claude's native web search
                        client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

                        response = await client.messages.create(
                            model=model_id,
                            max_tokens=2000,
                            tools=[{
                                "type": "web_search_20250305",
                                "name": "web_search",
                                "max_uses": 5
                            }],
                            messages=[{
                                "role": "user",
                                "content": f"Use web search to find the most current factual information for: {query}"
                            }]
                        )

                        # Extract text and sources from response
                        text_parts = []
                        for block in response.content:
                            if hasattr(block, 'text'):
                                text_parts.append(block.text)

                        result_text = "\n".join(text_parts) if text_parts else f"No results found for: {query}"

                        # Extract citations from Claude's response
                        # Claude embeds citations as markdown links in the text
                        import re

                        # Pattern to match markdown links: [text](url)
                        citation_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
                        matches = re.findall(citation_pattern, result_text)

                        seen_urls = set()
                        for title, url in matches:
                            # Only add if it's a web URL and not a duplicate
                            if url.startswith('http') and url not in seen_urls:
                                web_search_sources.append({
                                    'title': title,
                                    'url': url,
                                    'snippet': '',
                                })
                                seen_urls.add(url)
                                logger.info(f"🔍 Extracted Claude citation: {title} - {url}")

                        logger.info(f"🔍 Extracted {len(web_search_sources)} sources from Claude web search")

                        # Store sources in context
                        await ctx.store.set("web_search_sources", web_search_sources)

                        # Emit event: Web search completed
                        await self._emit_event(ctx, {
                            'type': 'tool_result',
                            'tool': 'web_search',
                            'sources_count': len(web_search_sources)
                        })

                        return result_text

                    else:
                        # Use OpenAI's native web search (Responses API)
                        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

                        response = await client.responses.create(
                            model="gpt-4o-mini",
                            input=f"Use the web tool to find the most current factual information for: {query}",
                            tools=[{"type": "web_search"}],
                            tool_choice={"type": "web_search"},
                        )

                        # Extract text and sources from response
                        # The output contains: [ResponseFunctionWebSearch, ResponseOutputMessage]
                        text = ""
                        if response.output:
                            try:
                                # Find the ResponseOutputMessage (it has type='message')
                                message = None
                                for item in response.output:
                                    if hasattr(item, 'type') and item.type == 'message':
                                        message = item
                                        break

                                if message and message.content:
                                    # Extract text from content
                                    content_block = message.content[0]
                                    text = content_block.text

                                    # Extract citations from annotations
                                    if hasattr(content_block, 'annotations') and content_block.annotations:
                                        logger.info(f"🔍 Found {len(content_block.annotations)} URL citations")
                                        for annotation in content_block.annotations:
                                            # Each annotation is an AnnotationURLCitation
                                            if annotation.type == 'url_citation':
                                                web_search_sources.append({
                                                    'title': annotation.title,
                                                    'url': annotation.url,
                                                    'snippet': '',  # OpenAI doesn't provide snippets in annotations
                                                })
                                                logger.info(f"🔍 Added source: {annotation.title} - {annotation.url}")

                            except Exception as e:
                                logger.error(f"Failed to extract sources: {e}", exc_info=True)
                                text = str(response.output) if response.output else ""

                        if not text:
                            text = f"No web search results found for: {query}"

                        # Store sources in context for later retrieval
                        logger.info(f"🔍 Extracted {len(web_search_sources)} sources from OpenAI web search")
                        await ctx.store.set("web_search_sources", web_search_sources)

                        # Emit event: Web search completed
                        await self._emit_event(ctx, {
                            'type': 'tool_result',
                            'tool': 'web_search',
                            'sources_count': len(web_search_sources)
                        })

                        return text.strip()

                except Exception as e:
                    logger.error(f"Web search failed for {model_id}: {e}")

                    # Emit error event
                    await self._emit_event(ctx, {
                        'type': 'tool_error',
                        'tool': 'web_search',
                        'error': str(e)
                    })

                    return f"Web search error: {str(e)}"

            web_search_tool = FunctionTool.from_defaults(
                async_fn=web_search,
                name="web_search",
                description="Search the web for current information. Automatically uses OpenAI or Claude web search based on the model.",
            )
            tools.append(web_search_tool)
            logger.info(f"Added web search tool (using {'Claude' if is_claude else 'OpenAI'} search)")
        except Exception as e:
            logger.warning(f"Failed to add web search tool: {e}")

        # 3. Add Google tools (if credentials available)
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

            # Emit event: Analyzing query
            await self._emit_event(ctx, {
                'type': 'thought',
                'content': '🔍 Analyzing query...'
            })

            # Smart routing: Check if we can answer from context first (without tools)
            # This prevents the agent from being "tool-happy" for simple questions
            if user_context or (conversation_memory and conversation_memory.message_count > 0):
                logger.info("🧠 Checking if query can be answered from context alone...")

                # Emit event: Checking context
                await self._emit_event(ctx, {
                    'type': 'thought',
                    'content': '💭 Checking if I can answer from memory...'
                })

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

                    # Emit event: Answered from context
                    await self._emit_event(ctx, {
                        'type': 'thought',
                        'content': '✅ Found answer in context, no tools needed'
                    })

                    # Start streaming the response
                    words = response_text.split(' ')
                    chunk_size = 5
                    for i in range(0, len(words), chunk_size):
                        chunk = ' '.join(words[i:i+chunk_size])
                        if i + chunk_size < len(words):
                            chunk += ' '
                        await self._emit_event(ctx, {
                            'type': 'content',
                            'delta': chunk
                        })
                        await asyncio.sleep(0.03)  # Small delay for smooth streaming

                    await ctx.store.set("response_text", response_text)
                    await ctx.store.set("tools_used", tools_used)
                    await ctx.store.set("reasoning_steps", reasoning_steps)

                    return ExecuteAgentEvent()

            # If we get here, we need tools - create the agent
            if tools:
                # Emit event: Starting agent with tools
                await self._emit_event(ctx, {
                    'type': 'thought',
                    'content': f'🤖 Starting agent with {len(tools)} tools available...'
                })

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

                # Emit event: Running agent
                await self._emit_event(ctx, {
                    'type': 'thought',
                    'content': '🧠 Agent is thinking...'
                })

                # Execute agent
                handler = agent.run(
                    user_msg=workflow_input.message,
                    max_iterations=workflow_input.max_iterations,
                )
                result = await handler

                # Emit event: Agent completed
                await self._emit_event(ctx, {
                    'type': 'thought',
                    'content': '✅ Agent completed reasoning'
                })

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
                        tool_name = None
                        if hasattr(tool_call, "tool_name"):
                            tool_name = tool_call.tool_name
                        elif hasattr(tool_call, "name"):
                            tool_name = tool_call.name

                        if tool_name:
                            tools_used.append(tool_name)
                            # Emit event for each tool used (if not already emitted by tool itself)
                            if tool_name != 'web_search':  # web_search emits its own events
                                await self._emit_event(ctx, {
                                    'type': 'tool_call',
                                    'tool': tool_name
                                })

                # Extract reasoning steps from raw messages
                reasoning_steps = []
                if hasattr(result, "raw") and result.raw:
                    if hasattr(result.raw, "messages"):
                        for msg in result.raw.messages[-5:]:  # Last 5 messages
                            reasoning_steps.append({
                                "role": str(msg.role) if hasattr(msg, "role") else "unknown",
                                "content": str(msg.content)[:200] if hasattr(msg, "content") else "",  # Truncate
                            })

                # Stream the response content
                words = response_text.split(' ')
                chunk_size = 5
                for i in range(0, len(words), chunk_size):
                    chunk = ' '.join(words[i:i+chunk_size])
                    if i + chunk_size < len(words):
                        chunk += ' '
                    await self._emit_event(ctx, {
                        'type': 'content',
                        'delta': chunk
                    })
                    await asyncio.sleep(0.03)  # Small delay for smooth streaming

            else:
                # No tools available, use direct LLM
                await self._emit_event(ctx, {
                    'type': 'thought',
                    'content': '💬 Generating response (no tools needed)...'
                })

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

                # Stream the response content
                words = response_text.split(' ')
                chunk_size = 5
                for i in range(0, len(words), chunk_size):
                    chunk = ' '.join(words[i:i+chunk_size])
                    if i + chunk_size < len(words):
                        chunk += ' '
                    await self._emit_event(ctx, {
                        'type': 'content',
                        'delta': chunk
                    })
                    await asyncio.sleep(0.03)  # Small delay for smooth streaming

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

        # Get web search sources if available
        try:
            web_search_sources = await ctx.store.get("web_search_sources")
        except (ValueError, AttributeError):
            # Key doesn't exist if web search wasn't used
            web_search_sources = []

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
                sources=web_search_sources,
                metadata=workflow_input.metadata,
            )

            return StopEvent(result=output)

        except Exception as e:
            await self.handle_error(workflow_context, e, "save_and_respond")
            raise

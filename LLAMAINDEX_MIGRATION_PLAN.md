# LlamaIndex Migration Plan - Complete Rewrite

**Project**: TurfMapp AI Agent
**Date**: January 2025
**Version**: 1.0
**Status**: Planning Phase

---

## Executive Summary

### Feasibility: ✅ HIGHLY FEASIBLE

This document outlines a comprehensive plan to migrate TurfMapp AI Agent to the LlamaIndex framework with:

- ✅ **Workflow-based agent orchestration** - Multi-step reasoning with state management
- ✅ **Advanced memory management** - Semantic memory, auto-summarization, entity extraction
- ✅ **RAG capabilities** - Document retrieval, embedding search, citation tracking
- ✅ **Complete tool system rewrite** - Native LlamaIndex tools replacing custom MCP implementation
- ✅ **Unified multi-model interface** - Simplified switching between OpenAI, Anthropic, and future providers
- ✅ **Database schema evolution** - PostgreSQL + pgvector with migration scripts
- ✅ **Comprehensive test suite** - 25+ new test files covering all components

### Migration Strategy

Based on stakeholder input:
- **Approach**: Complete rewrite (not incremental)
- **Tool Migration**: Full rewrite using LlamaIndex patterns
- **Data Preservation**: Modify schema with migration scripts
- **Timeline**: 8 weeks with 1-2 senior engineers

---

## Table of Contents

1. [Current Architecture Analysis](#current-architecture-analysis)
2. [What is LlamaIndex?](#what-is-llamaindex)
3. [Migration Benefits](#migration-benefits)
4. [Phase 1: Foundation & Dependencies](#phase-1-foundation--dependencies-week-1)
5. [Phase 2: Core LlamaIndex Integration](#phase-2-core-llamaindex-integration-week-2-3)
6. [Phase 3: Workflow Engine](#phase-3-workflow-engine-week-3-4)
7. [Phase 4: RAG Implementation](#phase-4-rag-implementation-week-4-5)
8. [Phase 5: New Chat Service](#phase-5-new-chat-service-week-5-6)
9. [Phase 6: API Layer Adaptation](#phase-6-api-layer-adaptation-week-6)
10. [Phase 7: Comprehensive Test Suite](#phase-7-comprehensive-test-suite-week-7-8)
11. [Phase 8: Deployment & Monitoring](#phase-8-deployment--monitoring-week-8)
12. [Risk Mitigation](#risk-mitigation)
13. [Success Metrics](#success-metrics)

---

## Current Architecture Analysis

### Technology Stack

**Backend Framework**:
- FastAPI 0.111.0
- Uvicorn (async ASGI server)
- Python 3.13+

**Database**:
- Supabase PostgreSQL
- asyncpg for async operations
- pgvector for embeddings (currently unused)

**AI Providers**:
- OpenAI (gpt-4o, gpt-4o-mini, o1 models)
- Anthropic Claude (claude-3-haiku, claude-sonnet-4, claude-opus-4)

**Current Dependencies**:
```
openai==1.55.3
supabase==2.7.4
asyncpg==0.30.0
pgvector==0.3.6
google-auth==2.28.1
google-api-python-client==2.122.0
```

### Current Chat Flow

1. User sends message via `POST /api/v1/chat/send`
2. `EnhancedChatService.process_chat_request()` orchestrates:
   - Retrieves conversation history from PostgreSQL
   - Gets user preferences (model, temperature, etc.)
   - Formats message history (max 20 messages)
   - Routes to OpenAI or Anthropic based on model name
   - Handles tool calling (Google MCP integration)
   - Parses responses and extracts sources
   - Saves messages to database

### Current Limitations

1. **No Vector Database Usage**: pgvector dependency exists but unused
2. **No RAG System**: All context comes from conversation history only
3. **No Document Indexing**: No chunking or embedding pipeline
4. **Manual Tool Management**: Tools defined as JSON schemas, not framework patterns
5. **No Structured Memory**: Simple message history, no semantic routing
6. **Custom Response Parsing**: Provider-specific parsing logic
7. **Simplified MCP**: Not full MCP protocol, custom Google integration
8. **Minimal Agent Framework**: Only basic routing logic exists

---

## What is LlamaIndex?

### Overview

LlamaIndex is a data framework for LLM applications that provides:

1. **Data Ingestion**: Connect to various data sources (files, APIs, databases)
2. **Data Indexing**: Chunk and embed documents for efficient retrieval
3. **Query Interface**: Natural language queries over indexed data
4. **Agent Framework**: Multi-step reasoning with tools and workflows
5. **Memory Management**: Conversation memory, entity extraction, summarization
6. **Multi-Model Support**: Unified interface for OpenAI, Anthropic, Gemini, etc.

### Key Concepts

#### 1. Unified Multi-Model Interface

**Current Approach** (separate implementations):
```python
# Different code for each provider
if model.startswith("claude-"):
    response = await anthropic_client.call_messages_api(...)
else:
    response = await chat_api_client.call_responses_api(...)
```

**LlamaIndex Approach** (unified interface):
```python
from llama_index.llms import OpenAI, Anthropic

# Same interface for all providers
llm = OpenAI(model="gpt-4o")  # or Anthropic(model="claude-sonnet-4")
response = await llm.achat(messages)
```

**Benefits**:
- ✅ Single codebase for all AI providers
- ✅ Easy model switching (change one line)
- ✅ Consistent token counting, streaming, error handling
- ✅ Simplified testing (mock once, test everywhere)
- ✅ Future-proof (add new providers easily)

#### 2. Workflows

Event-driven orchestration for multi-step tasks:

```python
from llama_index.core.workflow import Workflow, step, Context

class ChatWorkflow(Workflow):
    @step
    async def load_context(self, ctx: Context, message: str):
        # Load conversation memory
        # Retrieve RAG context
        # Get user preferences

    @step
    async def execute_tools(self, ctx: Context):
        # Run tools in parallel
        # Aggregate results

    @step
    async def generate_response(self, ctx: Context):
        # LLM generation with full context
```

**Benefits**:
- ✅ State management between steps
- ✅ Parallel execution where possible
- ✅ Error handling and retries
- ✅ Execution tracking and debugging

#### 3. RAG (Retrieval-Augmented Generation)

```python
from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.postgres import PGVectorStore

# Index documents
index = VectorStoreIndex.from_documents(documents)

# Query with retrieval
query_engine = index.as_query_engine(similarity_top_k=5)
response = query_engine.query("What is the remote work policy?")
```

**Benefits**:
- ✅ Semantic search over documents
- ✅ Source citation tracking
- ✅ Relevance scoring
- ✅ Hybrid search (semantic + keyword)

#### 4. Memory Management

```python
from llama_index.memory import ChatMemoryBuffer

memory = ChatMemoryBuffer.from_defaults(token_limit=2000)
memory.put(ChatMessage(role="user", content="My name is Alice"))
memory.put(ChatMessage(role="assistant", content="Nice to meet you!"))

# Automatic summarization when limit reached
messages = memory.get()  # Smart context window management
```

#### 5. Tools

```python
from llama_index.core.tools import FunctionTool

async def search_gmail(query: str, max_results: int = 10) -> str:
    """Search Gmail messages.

    Args:
        query: Gmail search query
        max_results: Maximum number of results
    """
    # Implementation
    return results

# Auto-generates schema for LLM
gmail_tool = FunctionTool.from_defaults(fn=search_gmail)
```

---

## Migration Benefits

### Technical Benefits

1. **Reduced Code Complexity**
   - Current: ~2,755 lines in services/
   - Estimated: ~1,500 lines with LlamaIndex
   - Elimination of custom parsing logic

2. **Better Abstractions**
   - Unified LLM interface
   - Native async/await throughout
   - Built-in error handling and retries

3. **Enhanced Capabilities**
   - RAG for document-based Q&A
   - Semantic memory vs simple history
   - Advanced workflow orchestration

4. **Improved Testing**
   - Mock LLMs for deterministic tests
   - Workflow step-by-step testing
   - Better test isolation

5. **Future-Proofing**
   - Easy to add new AI providers
   - Industry-standard patterns
   - Active community and updates

### Business Benefits

1. **Enhanced User Experience**
   - Document upload and Q&A
   - Better context understanding
   - More reliable tool execution

2. **Scalability**
   - Parallel workflow execution
   - Efficient vector search
   - Better resource management

3. **Maintainability**
   - Standard patterns, easier onboarding
   - Less custom code to maintain
   - Better documentation

4. **Cost Optimization**
   - Smart context window management
   - Efficient token usage
   - Reduced redundant API calls

---

## Phase 1: Foundation & Dependencies (Week 1)

### 1.1 Add LlamaIndex Dependencies

Update `requirements.txt`:

```txt
# LlamaIndex Core
llama-index==0.12.0
llama-index-core==0.12.0

# LLM Integrations
llama-index-llms-openai==0.3.0
llama-index-llms-anthropic==0.5.0

# Embeddings
llama-index-embeddings-openai==0.3.0

# Vector Stores
llama-index-vector-stores-postgres==0.3.0

# Agents & Tools
llama-index-agent-openai==0.4.0
llama-index-tools-google==0.3.0

# Memory & Workflows
llama-index-memory==0.3.0
llama-index-workflows==0.2.0

# Testing additions
faker==24.0.0
freezegun==1.4.0
```

### 1.2 Database Schema Enhancements

Create `migrations/001_llamaindex_tables.sql`:

```sql
-- Document nodes for RAG
CREATE TABLE IF NOT EXISTS turfmapp_agent.document_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES turfmapp_agent.users(id) ON DELETE CASCADE,
    document_id UUID NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Embeddings storage (with pgvector)
CREATE TABLE IF NOT EXISTS turfmapp_agent.embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id UUID NOT NULL REFERENCES turfmapp_agent.document_nodes(id) ON DELETE CASCADE,
    embedding vector(1536) NOT NULL,  -- OpenAI ada-002 dimension
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create vector similarity index
CREATE INDEX IF NOT EXISTS embeddings_vector_idx
ON turfmapp_agent.embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Memory states for conversation memory
CREATE TABLE IF NOT EXISTS turfmapp_agent.memory_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES turfmapp_agent.users(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES turfmapp_agent.conversations(id) ON DELETE CASCADE,
    memory_type VARCHAR(50) NOT NULL,  -- 'buffer', 'summary', 'entity'
    content JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Workflow execution tracking
CREATE TABLE IF NOT EXISTS turfmapp_agent.workflow_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES turfmapp_agent.users(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES turfmapp_agent.conversations(id),
    workflow_type VARCHAR(100) NOT NULL,
    state JSONB NOT NULL,
    status VARCHAR(50) NOT NULL,  -- 'running', 'completed', 'failed'
    error_message TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Enhance conversations table
ALTER TABLE turfmapp_agent.conversations
ADD COLUMN IF NOT EXISTS memory_snapshot JSONB,
ADD COLUMN IF NOT EXISTS rag_context_ids UUID[],
ADD COLUMN IF NOT EXISTS workflow_state JSONB;

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_document_nodes_user ON turfmapp_agent.document_nodes(user_id);
CREATE INDEX IF NOT EXISTS idx_document_nodes_doc ON turfmapp_agent.document_nodes(document_id);
CREATE INDEX IF NOT EXISTS idx_memory_states_user ON turfmapp_agent.memory_states(user_id);
CREATE INDEX IF NOT EXISTS idx_memory_states_conv ON turfmapp_agent.memory_states(conversation_id);
CREATE INDEX IF NOT EXISTS idx_workflow_executions_user ON turfmapp_agent.workflow_executions(user_id);
```

### 1.3 New Directory Structure

Create new directory structure:

```
app/
├── llamaindex/
│   ├── __init__.py
│   ├── agents/              # LlamaIndex agents
│   │   ├── __init__.py
│   │   ├── chat_agent.py
│   │   └── rag_agent.py
│   ├── workflows/           # Workflow definitions
│   │   ├── __init__.py
│   │   ├── chat_workflow.py
│   │   ├── tool_workflow.py
│   │   └── rag_workflow.py
│   ├── tools/              # LlamaIndex tool implementations
│   │   ├── __init__.py
│   │   ├── gmail_tools.py
│   │   ├── drive_tools.py
│   │   ├── calendar_tools.py
│   │   └── web_tools.py
│   ├── memory/             # Memory managers
│   │   ├── __init__.py
│   │   ├── conversation_memory.py
│   │   ├── user_memory.py
│   │   └── buffer_memory.py
│   ├── rag/                # RAG components
│   │   ├── __init__.py
│   │   ├── document_store.py
│   │   ├── retriever.py
│   │   └── ingestion.py
│   └── services/           # New LlamaIndex-powered services
│       ├── __init__.py
│       ├── chat_service_v2.py
│       ├── context_manager.py
│       └── llm_factory.py

tests/
├── llamaindex/             # NEW: LlamaIndex-specific tests
│   ├── __init__.py
│   ├── conftest.py         # LlamaIndex test fixtures
│   ├── test_agents.py
│   ├── test_workflows.py
│   ├── test_tools/
│   │   ├── __init__.py
│   │   ├── test_gmail_tools.py
│   │   ├── test_drive_tools.py
│   │   └── test_calendar_tools.py
│   ├── test_memory/
│   │   ├── __init__.py
│   │   ├── test_conversation_memory.py
│   │   ├── test_user_memory.py
│   │   └── test_buffer_memory.py
│   ├── test_rag/
│   │   ├── __init__.py
│   │   ├── test_document_store.py
│   │   ├── test_retriever.py
│   │   └── test_ingestion.py
│   └── test_services/
│       ├── __init__.py
│       ├── test_chat_service_v2.py
│       └── test_context_manager.py
├── integration/            # NEW: Integration tests
│   ├── __init__.py
│   ├── test_end_to_end_chat.py
│   ├── test_rag_pipeline.py
│   └── test_tool_execution_flow.py
├── regression/             # NEW: Updated regression tests
│   ├── __init__.py
│   ├── test_critical_flows_v2.py
│   └── test_backward_compatibility.py
└── performance/            # NEW: Performance tests
    ├── __init__.py
    ├── test_workflow_latency.py
    ├── test_memory_usage.py
    └── test_rag_retrieval_speed.py
```

### 1.4 Deliverables

- [ ] Updated `requirements.txt` with all LlamaIndex dependencies
- [ ] Database migration script `001_llamaindex_tables.sql`
- [ ] New directory structure created
- [ ] Dependencies installed and verified
- [ ] Database migration executed on dev environment

---

## Phase 2: Core LlamaIndex Integration (Week 2-3)

### 2.1 LLM Factory & Multi-Model Support

Create `app/llamaindex/services/llm_factory.py`:

```python
"""
LLM Factory for unified multi-model interface.
Provides consistent interface across OpenAI, Anthropic, and future providers.
"""

from typing import Optional
from llama_index.llms.openai import OpenAI
from llama_index.llms.anthropic import Anthropic
from llama_index.core.llms import LLM
import logging

logger = logging.getLogger(__name__)

# Model registry
OPENAI_MODELS = ["gpt-4o", "gpt-4o-mini", "o1", "o1-mini", "o1-preview", "gpt-5-mini"]
ANTHROPIC_MODELS = [
    "claude-3-haiku-20240307",
    "claude-sonnet-4-20250514",
    "claude-sonnet-4-5-20250929",
    "claude-opus-4-1-20250805",
]

class LLMFactory:
    """Factory for creating LLM instances with unified interface."""

    @staticmethod
    def create_llm(
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLM:
        """
        Create an LLM instance based on model name.

        Args:
            model: Model identifier (e.g., "gpt-4o", "claude-sonnet-4")
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            **kwargs: Additional provider-specific parameters

        Returns:
            LLM instance with unified interface
        """
        if model in OPENAI_MODELS or model.startswith("gpt"):
            logger.info(f"Creating OpenAI LLM: {model}")
            return OpenAI(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

        elif model in ANTHROPIC_MODELS or model.startswith("claude"):
            logger.info(f"Creating Anthropic LLM: {model}")
            return Anthropic(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens or 4096,
                **kwargs
            )

        else:
            raise ValueError(f"Unsupported model: {model}")

    @staticmethod
    def get_default_model() -> str:
        """Get default model name."""
        return "gpt-4o"

    @staticmethod
    def list_available_models() -> dict:
        """List all available models by provider."""
        return {
            "openai": OPENAI_MODELS,
            "anthropic": ANTHROPIC_MODELS,
        }
```

### 2.2 Memory System Implementation

Create `app/llamaindex/memory/conversation_memory.py`:

```python
"""
Conversation Memory Manager with LlamaIndex integration.
Handles chat buffer, summarization, and entity extraction.
"""

from typing import List, Dict, Any, Optional
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.llms import ChatMessage
from llama_index.core.llms import LLM
from datetime import datetime
import logging

from ...database import execute_query, execute_query_one

logger = logging.getLogger(__name__)

class ConversationMemoryManager:
    """
    Manages conversation memory with multiple strategies:
    - Buffer memory (sliding window)
    - Summary memory (auto-summarization)
    - Entity memory (key entities extraction)
    """

    def __init__(
        self,
        user_id: str,
        conversation_id: Optional[str] = None,
        llm: Optional[LLM] = None,
        token_limit: int = 2000,
        max_messages: int = 50
    ):
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.llm = llm
        self.token_limit = token_limit
        self.max_messages = max_messages

        # Initialize buffer memory
        self.buffer = ChatMemoryBuffer.from_defaults(
            token_limit=token_limit,
            llm=llm
        )

        # Entity tracking
        self.entities: Dict[str, List[str]] = {
            "names": [],
            "organizations": [],
            "locations": [],
            "dates": [],
        }

    async def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add message to memory buffer."""
        message = ChatMessage(role=role, content=content, additional_kwargs=metadata or {})
        self.buffer.put(message)

        # Extract entities if assistant message
        if role == "user" and self.llm:
            await self._extract_entities_from_message(content)

    async def get_messages(self, limit: Optional[int] = None) -> List[ChatMessage]:
        """Get messages from buffer."""
        messages = self.buffer.get()
        if limit:
            return messages[-limit:]
        return messages

    async def get_summary(self) -> Optional[str]:
        """Generate conversation summary if needed."""
        if not self.llm:
            return None

        messages = await self.get_messages()
        if len(messages) < 10:  # Don't summarize short conversations
            return None

        # Use LLM to summarize
        summary_prompt = f"""Summarize the following conversation concisely in 2-3 sentences:

{self._format_messages_for_summary(messages)}

Summary:"""

        response = await self.llm.acomplete(summary_prompt)
        return response.text

    async def extract_entities(self) -> Dict[str, List[str]]:
        """Extract key entities from conversation."""
        return self.entities

    async def _extract_entities_from_message(self, content: str):
        """Extract entities from a message using LLM."""
        # Simple entity extraction prompt
        entity_prompt = f"""Extract key entities from this message. Return as JSON.

Message: {content}

Extract:
- names (people's names)
- organizations (company names, organizations)
- locations (cities, countries, addresses)
- dates (any date references)

Format: {{"names": [], "organizations": [], "locations": [], "dates": []}}

Entities:"""

        try:
            response = await self.llm.acomplete(entity_prompt)
            import json
            entities = json.loads(response.text)

            # Merge with existing entities
            for key in self.entities:
                if key in entities:
                    self.entities[key].extend(entities[key])
                    self.entities[key] = list(set(self.entities[key]))  # Dedupe
        except Exception as e:
            logger.warning(f"Entity extraction failed: {e}")

    async def save_snapshot(self):
        """Save memory snapshot to database."""
        if not self.conversation_id:
            return

        messages = await self.get_messages()
        summary = await self.get_summary()

        snapshot = {
            "messages": [
                {"role": m.role, "content": m.content}
                for m in messages
            ],
            "summary": summary,
            "entities": self.entities,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Save buffer memory
        await execute_query(
            """
            INSERT INTO turfmapp_agent.memory_states
            (user_id, conversation_id, memory_type, content)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_id, conversation_id, memory_type)
            DO UPDATE SET content = $4, updated_at = NOW()
            """,
            self.user_id,
            self.conversation_id,
            "buffer",
            snapshot
        )

    async def load_snapshot(self):
        """Load memory snapshot from database."""
        if not self.conversation_id:
            return

        row = await execute_query_one(
            """
            SELECT content FROM turfmapp_agent.memory_states
            WHERE user_id = $1 AND conversation_id = $2 AND memory_type = $3
            ORDER BY updated_at DESC LIMIT 1
            """,
            self.user_id,
            self.conversation_id,
            "buffer"
        )

        if row:
            snapshot = row["content"]

            # Restore messages to buffer
            for msg in snapshot.get("messages", []):
                self.buffer.put(ChatMessage(
                    role=msg["role"],
                    content=msg["content"]
                ))

            # Restore entities
            self.entities = snapshot.get("entities", self.entities)

    def _format_messages_for_summary(self, messages: List[ChatMessage]) -> str:
        """Format messages for summarization."""
        formatted = []
        for msg in messages:
            formatted.append(f"{msg.role.upper()}: {msg.content}")
        return "\n".join(formatted)
```

### 2.3 Tool System Rewrite

Create `app/llamaindex/tools/gmail_tools.py`:

```python
"""
Gmail Tools using LlamaIndex FunctionTool pattern.
Provides async Gmail operations with automatic schema generation.
"""

from typing import Optional
from llama_index.core.tools import FunctionTool
import logging

from ...services.google_gmail_ops import (
    search_gmail as _search_gmail,
    get_recent_emails as _get_recent,
    get_email_by_id as _get_email,
)

logger = logging.getLogger(__name__)

async def gmail_search(
    user_id: str,
    query: str,
    max_results: int = 10,
    account: str = "primary"
) -> str:
    """
    Search Gmail messages using Gmail query syntax.

    Args:
        user_id: User ID for authentication
        query: Gmail search query (e.g., "from:john@example.com subject:meeting")
        max_results: Maximum number of results to return (default: 10)
        account: Google account identifier (default: "primary")

    Returns:
        Formatted string with email results including subject, sender, date, and snippet

    Examples:
        - "from:boss@company.com" - Emails from specific sender
        - "subject:project update" - Emails with specific subject
        - "is:unread" - Unread emails
        - "after:2025/01/01" - Emails after specific date
    """
    try:
        results = await _search_gmail(user_id, query, max_results, account)
        return _format_email_results(results)
    except Exception as e:
        logger.error(f"Gmail search error: {e}")
        return f"Error searching Gmail: {str(e)}"

async def gmail_get_recent(
    user_id: str,
    max_results: int = 10,
    account: str = "primary"
) -> str:
    """
    Get recent Gmail messages.

    Args:
        user_id: User ID for authentication
        max_results: Maximum number of recent emails (default: 10)
        account: Google account identifier (default: "primary")

    Returns:
        Formatted string with recent emails
    """
    try:
        results = await _get_recent(user_id, max_results, account)
        return _format_email_results(results)
    except Exception as e:
        logger.error(f"Gmail recent error: {e}")
        return f"Error fetching recent emails: {str(e)}"

async def gmail_get_message(
    user_id: str,
    message_id: str,
    account: str = "primary"
) -> str:
    """
    Get full details of a specific Gmail message.

    Args:
        user_id: User ID for authentication
        message_id: Gmail message ID
        account: Google account identifier (default: "primary")

    Returns:
        Formatted string with full email details including body
    """
    try:
        result = await _get_email(user_id, message_id, account)
        return _format_email_detail(result)
    except Exception as e:
        logger.error(f"Gmail get message error: {e}")
        return f"Error fetching email: {str(e)}"

def _format_email_results(results: list) -> str:
    """Format email results for LLM consumption."""
    if not results:
        return "No emails found."

    formatted = []
    for email in results:
        formatted.append(
            f"• Subject: {email.get('subject', 'No subject')}\n"
            f"  From: {email.get('from', 'Unknown')}\n"
            f"  Date: {email.get('date', 'Unknown')}\n"
            f"  Snippet: {email.get('snippet', '')}\n"
            f"  ID: {email.get('id', '')}"
        )

    return "\n\n".join(formatted)

def _format_email_detail(email: dict) -> str:
    """Format single email detail."""
    return (
        f"Subject: {email.get('subject', 'No subject')}\n"
        f"From: {email.get('from', 'Unknown')}\n"
        f"To: {email.get('to', 'Unknown')}\n"
        f"Date: {email.get('date', 'Unknown')}\n"
        f"Body:\n{email.get('body', 'No content')}"
    )

# Create LlamaIndex FunctionTool instances
# These automatically generate schemas for LLM tool calling
def create_gmail_tools(user_id: str) -> list[FunctionTool]:
    """
    Create Gmail tools for a specific user.

    Args:
        user_id: User ID to bind to tools

    Returns:
        List of FunctionTool instances for Gmail operations
    """
    # Bind user_id to tool functions
    async def bound_search(query: str, max_results: int = 10) -> str:
        return await gmail_search(user_id, query, max_results)

    async def bound_recent(max_results: int = 10) -> str:
        return await gmail_get_recent(user_id, max_results)

    async def bound_get_message(message_id: str) -> str:
        return await gmail_get_message(user_id, message_id)

    return [
        FunctionTool.from_defaults(
            fn=bound_search,
            name="gmail_search",
            description="Search Gmail messages using Gmail query syntax"
        ),
        FunctionTool.from_defaults(
            fn=bound_recent,
            name="gmail_get_recent",
            description="Get recent Gmail messages"
        ),
        FunctionTool.from_defaults(
            fn=bound_get_message,
            name="gmail_get_message",
            description="Get full details of a specific Gmail message by ID"
        ),
    ]
```

### 2.4 Deliverables

- [ ] `llm_factory.py` - Unified multi-model interface
- [ ] `conversation_memory.py` - Advanced memory management
- [ ] `gmail_tools.py` - Gmail tools as LlamaIndex FunctionTools
- [ ] `drive_tools.py` - Google Drive tools
- [ ] `calendar_tools.py` - Google Calendar tools
- [ ] Unit tests for each component
- [ ] Integration tests for LLM factory with real models

---

## Phase 3: Workflow Engine (Week 3-4)

### 3.1 Chat Workflow Definition

Create `app/llamaindex/workflows/chat_workflow.py`:

```python
"""
Chat Workflow using LlamaIndex Workflow engine.
Multi-step orchestration: context loading → intent routing → tool execution → response generation.
"""

from typing import Optional, Dict, Any, List
from llama_index.core.workflow import Workflow, step, Context, Event
from llama_index.core.llms import LLM, ChatMessage
import logging

from ..memory.conversation_memory import ConversationMemoryManager
from ..services.llm_factory import LLMFactory
from ..tools.gmail_tools import create_gmail_tools
from ..tools.drive_tools import create_drive_tools
from ..tools.calendar_tools import create_calendar_tools

logger = logging.getLogger(__name__)

# Define workflow events
class ContextLoadedEvent(Event):
    """Emitted when context is loaded."""
    messages: List[ChatMessage]
    memory: ConversationMemoryManager
    tools: List[Any]

class IntentClassifiedEvent(Event):
    """Emitted when user intent is classified."""
    intent: str  # 'chat', 'tool_use', 'rag_query'
    requires_tools: bool

class ToolsExecutedEvent(Event):
    """Emitted when tools are executed."""
    tool_results: List[Dict[str, Any]]

class ResponseGeneratedEvent(Event):
    """Emitted when final response is generated."""
    response: str
    metadata: Dict[str, Any]

class ChatWorkflow(Workflow):
    """
    Main chat workflow orchestrating:
    1. Context loading (memory, user preferences, RAG)
    2. Intent classification
    3. Tool execution (if needed)
    4. Response generation
    5. State persistence
    """

    def __init__(self, llm: Optional[LLM] = None, **kwargs):
        super().__init__(**kwargs)
        self.llm = llm or LLMFactory.create_llm("gpt-4o")

    @step
    async def load_context(
        self,
        ctx: Context,
        message: str,
        user_id: str,
        conversation_id: Optional[str] = None,
        use_rag: bool = False
    ) -> ContextLoadedEvent:
        """
        Load conversation context including memory, preferences, and RAG.

        Args:
            ctx: Workflow context
            message: User message
            user_id: User ID
            conversation_id: Optional conversation ID
            use_rag: Whether to use RAG retrieval
        """
        logger.info(f"Loading context for user {user_id}")

        # Initialize memory manager
        memory = ConversationMemoryManager(
            user_id=user_id,
            conversation_id=conversation_id,
            llm=self.llm
        )

        # Load existing conversation if any
        if conversation_id:
            await memory.load_snapshot()

        # Add current user message
        await memory.add_message("user", message)

        # Get all messages for LLM
        messages = await memory.get_messages()

        # Load tools for this user
        tools = []
        tools.extend(create_gmail_tools(user_id))
        tools.extend(create_drive_tools(user_id))
        tools.extend(create_calendar_tools(user_id))

        # TODO: RAG retrieval if use_rag=True

        # Store in context
        ctx.data["user_id"] = user_id
        ctx.data["conversation_id"] = conversation_id
        ctx.data["memory"] = memory
        ctx.data["user_message"] = message

        return ContextLoadedEvent(
            messages=messages,
            memory=memory,
            tools=tools
        )

    @step
    async def route_intent(
        self,
        ctx: Context,
        ev: ContextLoadedEvent
    ) -> IntentClassifiedEvent:
        """
        Classify user intent to determine if tools are needed.

        Args:
            ctx: Workflow context
            ev: Context loaded event
        """
        logger.info("Classifying user intent")

        user_message = ctx.data["user_message"]

        # Simple intent classification
        # TODO: Use LLM for more sophisticated classification
        tool_keywords = [
            "search", "find", "email", "gmail", "calendar",
            "drive", "document", "file", "schedule", "meeting"
        ]

        requires_tools = any(keyword in user_message.lower() for keyword in tool_keywords)

        intent = "tool_use" if requires_tools else "chat"

        ctx.data["tools"] = ev.tools
        ctx.data["requires_tools"] = requires_tools

        return IntentClassifiedEvent(
            intent=intent,
            requires_tools=requires_tools
        )

    @step
    async def execute_tools(
        self,
        ctx: Context,
        ev: IntentClassifiedEvent
    ) -> ToolsExecutedEvent:
        """
        Execute tools if needed.

        Args:
            ctx: Workflow context
            ev: Intent classified event
        """
        tool_results = []

        if ev.requires_tools:
            logger.info("Executing tools")

            # Get tools from context
            tools = ctx.data["tools"]
            messages = ctx.data.get("messages", [])

            # Create agent with tools
            from llama_index.agent.openai import OpenAIAgent

            agent = OpenAIAgent.from_tools(
                tools=tools,
                llm=self.llm,
                verbose=True
            )

            # Run agent
            user_message = ctx.data["user_message"]
            response = await agent.achat(user_message)

            # Extract tool results from agent response
            # Store for next step
            ctx.data["agent_response"] = response

        ctx.data["tool_results"] = tool_results

        return ToolsExecutedEvent(tool_results=tool_results)

    @step
    async def generate_response(
        self,
        ctx: Context,
        ev: ToolsExecutedEvent
    ) -> ResponseGeneratedEvent:
        """
        Generate final response with full context.

        Args:
            ctx: Workflow context
            ev: Tools executed event
        """
        logger.info("Generating response")

        # Check if we have agent response (from tool execution)
        if "agent_response" in ctx.data:
            response_text = str(ctx.data["agent_response"])
        else:
            # No tools used, direct LLM chat
            memory: ConversationMemoryManager = ctx.data["memory"]
            messages = await memory.get_messages()

            # Convert to LLM format
            llm_messages = [
                ChatMessage(role=msg.role, content=msg.content)
                for msg in messages
            ]

            # Generate response
            response = await self.llm.achat(llm_messages)
            response_text = response.message.content

        # Add assistant response to memory
        memory: ConversationMemoryManager = ctx.data["memory"]
        await memory.add_message("assistant", response_text)

        metadata = {
            "model": self.llm.metadata.model_name,
            "tool_calls": len(ev.tool_results),
        }

        return ResponseGeneratedEvent(
            response=response_text,
            metadata=metadata
        )

    @step
    async def save_state(
        self,
        ctx: Context,
        ev: ResponseGeneratedEvent
    ) -> Dict[str, Any]:
        """
        Save conversation state to database.

        Args:
            ctx: Workflow context
            ev: Response generated event
        """
        logger.info("Saving conversation state")

        # Save memory snapshot
        memory: ConversationMemoryManager = ctx.data["memory"]
        await memory.save_snapshot()

        # Return final result
        return {
            "status": "completed",
            "response": ev.response,
            "metadata": ev.metadata,
            "conversation_id": ctx.data.get("conversation_id"),
        }
```

### 3.2 Tool Execution Workflow

Create `app/llamaindex/workflows/tool_workflow.py`:

```python
"""
Tool Execution Workflow with parallel execution and retry logic.
"""

from typing import List, Dict, Any
from llama_index.core.workflow import Workflow, step, Context
import asyncio
import logging

logger = logging.getLogger(__name__)

class ToolWorkflow(Workflow):
    """Workflow for executing tools with parallelization and error handling."""

    def __init__(self, max_retries: int = 3, **kwargs):
        super().__init__(**kwargs)
        self.max_retries = max_retries

    async def execute_tools(
        self,
        tool_calls: List[Dict[str, Any]],
        user_id: str,
        parallel: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Execute multiple tool calls with optional parallelization.

        Args:
            tool_calls: List of tool calls with name and args
            user_id: User ID for authentication
            parallel: Whether to execute in parallel

        Returns:
            List of tool results
        """
        if parallel:
            # Execute in parallel
            tasks = [
                self._execute_single_tool(tc, user_id)
                for tc in tool_calls
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # Execute sequentially
            results = []
            for tc in tool_calls:
                result = await self._execute_single_tool(tc, user_id)
                results.append(result)

        return results

    async def _execute_single_tool(
        self,
        tool_call: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Execute a single tool with retry logic.

        Args:
            tool_call: Tool call with name and args
            user_id: User ID

        Returns:
            Tool execution result
        """
        tool_name = tool_call.get("name")
        args = tool_call.get("args", {})

        for attempt in range(self.max_retries):
            try:
                # Execute tool
                # TODO: Implement actual tool execution
                result = await self._call_tool(tool_name, args, user_id)

                return {
                    "status": "success",
                    "tool": tool_name,
                    "result": result,
                    "retry_count": attempt
                }

            except Exception as e:
                logger.warning(f"Tool {tool_name} failed (attempt {attempt + 1}): {e}")

                if attempt == self.max_retries - 1:
                    return {
                        "status": "error",
                        "tool": tool_name,
                        "error_message": str(e),
                        "retry_count": attempt + 1
                    }

                # Exponential backoff
                await asyncio.sleep(2 ** attempt)

    async def _call_tool(
        self,
        tool_name: str,
        args: Dict[str, Any],
        user_id: str
    ) -> Any:
        """
        Call the actual tool function.

        Args:
            tool_name: Name of tool
            args: Tool arguments
            user_id: User ID

        Returns:
            Tool result
        """
        # Import and call appropriate tool
        # This is where actual tool execution happens

        if tool_name == "gmail_search":
            from ..tools.gmail_tools import gmail_search
            return await gmail_search(user_id, **args)

        elif tool_name == "drive_search_files":
            from ..tools.drive_tools import drive_search_files
            return await drive_search_files(user_id, **args)

        # Add more tools as needed

        else:
            raise ValueError(f"Unknown tool: {tool_name}")
```

### 3.3 RAG Workflow

Create `app/llamaindex/workflows/rag_workflow.py`:

```python
"""
RAG Workflow for document ingestion and retrieval.
"""

from typing import List, Optional
from llama_index.core.workflow import Workflow, step, Context
from llama_index.core import VectorStoreIndex, Document
from llama_index.core.node_parser import SentenceSplitter
import logging

logger = logging.getLogger(__name__)

class RAGWorkflow(Workflow):
    """Workflow for RAG operations: ingestion and querying."""

    def __init__(self, vector_store, llm, **kwargs):
        super().__init__(**kwargs)
        self.vector_store = vector_store
        self.llm = llm
        self.index = None

    async def ingest_documents(
        self,
        documents: List[str],
        user_id: str,
        metadata: Optional[dict] = None
    ) -> dict:
        """
        Ingest documents into vector store.

        Args:
            documents: List of document texts
            user_id: User ID
            metadata: Optional metadata

        Returns:
            Ingestion result
        """
        logger.info(f"Ingesting {len(documents)} documents for user {user_id}")

        # Create Document objects
        docs = [
            Document(text=text, metadata={"user_id": user_id, **(metadata or {})})
            for text in documents
        ]

        # Parse into nodes
        parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)
        nodes = parser.get_nodes_from_documents(docs)

        # Create/update index
        if self.index is None:
            self.index = VectorStoreIndex.from_documents(
                docs,
                vector_store=self.vector_store
            )
        else:
            self.index.insert_nodes(nodes)

        return {
            "status": "success",
            "documents_ingested": len(documents),
            "nodes_created": len(nodes)
        }

    async def query(
        self,
        query: str,
        user_id: str,
        top_k: int = 5
    ) -> dict:
        """
        Query documents with RAG.

        Args:
            query: Query string
            user_id: User ID
            top_k: Number of results

        Returns:
            Query result with response and sources
        """
        if self.index is None:
            return {
                "response": "No documents indexed yet.",
                "sources": []
            }

        # Create query engine
        query_engine = self.index.as_query_engine(
            similarity_top_k=top_k,
            llm=self.llm
        )

        # Filter by user
        # TODO: Add user_id filter

        # Execute query
        response = await query_engine.aquery(query)

        # Extract sources
        sources = [
            {
                "text": node.text,
                "score": node.score,
                "metadata": node.metadata
            }
            for node in response.source_nodes
        ]

        return {
            "response": str(response),
            "sources": sources,
            "citations": self._extract_citations(response)
        }

    def _extract_citations(self, response) -> List[dict]:
        """Extract citations from response."""
        citations = []
        for node in response.source_nodes:
            citations.append({
                "source_id": node.node_id,
                "score": node.score,
                "text_snippet": node.text[:200] + "..."
            })
        return citations
```

### 3.4 Deliverables

- [ ] `chat_workflow.py` - Main chat orchestration workflow
- [ ] `tool_workflow.py` - Parallel tool execution with retries
- [ ] `rag_workflow.py` - Document ingestion and retrieval
- [ ] Unit tests for each workflow
- [ ] Integration tests for complete workflow execution
- [ ] Workflow visualization documentation

---

## Phase 4: RAG Implementation (Week 4-5)

### 4.1 Vector Store Setup

Create `app/llamaindex/rag/document_store.py`:

```python
"""
Document Store with PostgreSQL + pgvector backend.
"""

from typing import List, Optional, Dict, Any
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.core import VectorStoreIndex, Document
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.openai import OpenAIEmbedding
import logging
import os

logger = logging.getLogger(__name__)

class DocumentStore:
    """Handles document ingestion, storage, and retrieval."""

    def __init__(self, embeddings: Optional[OpenAIEmbedding] = None):
        # Initialize embeddings
        self.embeddings = embeddings or OpenAIEmbedding(
            model="text-embedding-ada-002"
        )

        # Initialize vector store
        self.vector_store = PGVectorStore.from_params(
            database=os.getenv("SUPABASE_DB", "postgres"),
            host=os.getenv("SUPABASE_HOST", "localhost"),
            password=os.getenv("SUPABASE_PASSWORD", ""),
            port=5432,
            user="postgres",
            table_name="document_embeddings",
            embed_dim=1536,  # OpenAI ada-002
            schema_name="turfmapp_agent"
        )

        # Text splitter for chunking
        self.text_splitter = SentenceSplitter(
            chunk_size=512,
            chunk_overlap=50
        )

    async def ingest_document(
        self,
        text: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Ingest a document into the store.

        Args:
            text: Document text
            user_id: User ID
            metadata: Optional metadata

        Returns:
            Document ID
        """
        import uuid
        doc_id = str(uuid.uuid4())

        # Create document with metadata
        doc_metadata = {
            "user_id": user_id,
            "document_id": doc_id,
            **(metadata or {})
        }

        document = Document(
            text=text,
            metadata=doc_metadata,
            id_=doc_id
        )

        # Create index and insert
        index = VectorStoreIndex.from_documents(
            [document],
            vector_store=self.vector_store,
            embed_model=self.embeddings
        )

        logger.info(f"Ingested document {doc_id} for user {user_id}")

        return doc_id

    async def chunk_document(self, text: str) -> List[str]:
        """
        Chunk document into smaller pieces.

        Args:
            text: Document text

        Returns:
            List of text chunks
        """
        chunks = self.text_splitter.split_text(text)
        return chunks

    async def get_document_metadata(self, doc_id: str) -> Dict[str, Any]:
        """Get document metadata."""
        # Query from PostgreSQL
        from ...database import execute_query_one

        row = await execute_query_one(
            """
            SELECT metadata FROM turfmapp_agent.document_nodes
            WHERE document_id = $1
            LIMIT 1
            """,
            doc_id
        )

        if row:
            return row["metadata"]

        raise ValueError(f"Document {doc_id} not found")

    async def delete_document(self, doc_id: str):
        """Delete a document and all its chunks."""
        from ...database import execute_query

        await execute_query(
            """
            DELETE FROM turfmapp_agent.document_nodes
            WHERE document_id = $1
            """,
            doc_id
        )

        logger.info(f"Deleted document {doc_id}")
```

### 4.2 Retrieval Service

Create `app/llamaindex/rag/retriever.py`:

```python
"""
RAG Retriever with hybrid search and MMR.
"""

from typing import List, Optional
from llama_index.core import VectorStoreIndex
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.postprocessor import SimilarityPostprocessor
import logging

logger = logging.getLogger(__name__)

class RAGRetriever:
    """Advanced retrieval with semantic search, hybrid search, and MMR."""

    def __init__(
        self,
        vector_store,
        embeddings,
        use_hybrid: bool = False
    ):
        self.vector_store = vector_store
        self.embeddings = embeddings
        self.use_hybrid = use_hybrid

        # Create index
        self.index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            embed_model=embeddings
        )

    async def add_documents(self, documents: List[str]):
        """Add documents to index."""
        from llama_index.core import Document

        docs = [Document(text=text) for text in documents]
        self.index.insert_nodes(docs)

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        min_relevance_score: Optional[float] = None,
        use_mmr: bool = False,
        diversity_weight: float = 0.3
    ) -> List[Any]:
        """
        Retrieve relevant documents.

        Args:
            query: Query string
            top_k: Number of results
            min_relevance_score: Minimum similarity score
            use_mmr: Use Maximal Marginal Relevance for diversity
            diversity_weight: Weight for MMR diversity (0-1)

        Returns:
            List of retrieved nodes with scores
        """
        # Create retriever
        retriever = VectorIndexRetriever(
            index=self.index,
            similarity_top_k=top_k * 2 if use_mmr else top_k
        )

        # Retrieve nodes
        nodes = await retriever.aretrieve(query)

        # Apply MMR if requested
        if use_mmr:
            nodes = self._apply_mmr(nodes, top_k, diversity_weight)

        # Apply minimum relevance filter
        if min_relevance_score:
            postprocessor = SimilarityPostprocessor(
                similarity_cutoff=min_relevance_score
            )
            nodes = postprocessor.postprocess_nodes(nodes)

        return nodes[:top_k]

    def _apply_mmr(
        self,
        nodes: List,
        top_k: int,
        diversity_weight: float
    ) -> List:
        """
        Apply Maximal Marginal Relevance for diverse results.

        Args:
            nodes: Retrieved nodes
            top_k: Number of final results
            diversity_weight: Weight for diversity (0-1)

        Returns:
            Reranked nodes with diversity
        """
        # Simple MMR implementation
        # Select first node (highest relevance)
        if not nodes:
            return []

        selected = [nodes[0]]
        remaining = nodes[1:]

        while len(selected) < top_k and remaining:
            # Calculate MMR scores
            mmr_scores = []
            for node in remaining:
                # Relevance score
                relevance = node.score

                # Diversity score (minimum similarity to selected)
                max_sim = max(
                    self._similarity(node, s)
                    for s in selected
                )
                diversity = 1 - max_sim

                # Combined MMR score
                mmr = (1 - diversity_weight) * relevance + diversity_weight * diversity
                mmr_scores.append((mmr, node))

            # Select node with highest MMR
            mmr_scores.sort(reverse=True, key=lambda x: x[0])
            selected.append(mmr_scores[0][1])
            remaining.remove(mmr_scores[0][1])

        return selected

    def _similarity(self, node1, node2) -> float:
        """Calculate similarity between two nodes."""
        # Simplified: use embedding cosine similarity
        # In practice, would use actual embeddings
        return 0.5  # Placeholder
```

### 4.3 Ingestion Pipeline

Create `app/llamaindex/rag/ingestion.py`:

```python
"""
Document Ingestion Pipeline with file parsing and chunking.
"""

from typing import Optional, Dict, Any, List
from llama_index.core import SimpleDirectoryReader, Document
from llama_index.core.node_parser import SentenceSplitter
import logging
import tempfile
import os

logger = logging.getLogger(__name__)

class IngestionPipeline:
    """Pipeline for ingesting various document formats."""

    def __init__(self):
        self.text_splitter = SentenceSplitter(
            chunk_size=512,
            chunk_overlap=50
        )

    async def ingest_file(
        self,
        file,
        user_id: str,
        filename: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Ingest a file (PDF, DOCX, TXT, etc.).

        Args:
            file: File object
            user_id: User ID
            filename: Original filename
            metadata: Optional metadata

        Returns:
            Ingestion result
        """
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # Load document
            reader = SimpleDirectoryReader(input_files=[tmp_path])
            documents = reader.load_data()

            # Add metadata
            for doc in documents:
                doc.metadata["user_id"] = user_id
                doc.metadata["filename"] = filename
                if metadata:
                    doc.metadata.update(metadata)

            # Chunk documents
            nodes = self.text_splitter.get_nodes_from_documents(documents)

            # TODO: Store in vector database

            return {
                "status": "success",
                "filename": filename,
                "chunks_created": len(nodes)
            }

        finally:
            # Clean up temp file
            os.unlink(tmp_path)

    async def ingest_text(
        self,
        text: str,
        user_id: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Ingest plain text.

        Args:
            text: Text content
            user_id: User ID
            metadata: Optional metadata

        Returns:
            Ingestion result
        """
        # Create document
        doc = Document(
            text=text,
            metadata={"user_id": user_id, **(metadata or {})}
        )

        # Chunk
        nodes = self.text_splitter.get_nodes_from_documents([doc])

        # TODO: Store in vector database

        return {
            "status": "success",
            "chunks_created": len(nodes)
        }

    async def ingest_batch(
        self,
        documents: List[Dict[str, Any]],
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Ingest multiple documents in batch.

        Args:
            documents: List of dicts with 'text' and 'metadata'
            user_id: User ID

        Returns:
            List of ingestion results
        """
        results = []

        for doc_data in documents:
            result = await self.ingest_text(
                text=doc_data["text"],
                user_id=user_id,
                metadata=doc_data.get("metadata")
            )
            results.append(result)

        return results
```

### 4.4 Deliverables

- [ ] `document_store.py` - Vector store integration
- [ ] `retriever.py` - Advanced retrieval with MMR
- [ ] `ingestion.py` - File parsing and ingestion pipeline
- [ ] Unit tests for all RAG components
- [ ] Integration tests for end-to-end RAG flow
- [ ] Performance benchmarks for retrieval speed

---

## Phase 5: New Chat Service (Week 5-6)

### 5.1 ChatServiceV2 Implementation

Create `app/llamaindex/services/chat_service_v2.py`:

```python
"""
ChatServiceV2 - LlamaIndex-powered chat service.
Replaces EnhancedChatService with workflow-based orchestration.
"""

from typing import Optional, Dict, Any
from llama_index.core.llms import LLM
import logging
import uuid

from .llm_factory import LLMFactory
from ..workflows.chat_workflow import ChatWorkflow
from ..memory.conversation_memory import ConversationMemoryManager
from ..rag.document_store import DocumentStore
from ..rag.retriever import RAGRetriever
from ...database import execute_query, execute_query_one

logger = logging.getLogger(__name__)

class ChatServiceV2:
    """
    New chat service powered by LlamaIndex.

    Features:
    - Workflow-based orchestration
    - Advanced memory management
    - RAG capabilities
    - Unified multi-model interface
    - Tool integration
    """

    def __init__(
        self,
        llm: Optional[LLM] = None,
        vector_store = None
    ):
        self.llm_factory = LLMFactory()
        self.llm = llm
        self.vector_store = vector_store

        # Initialize components
        self.document_store = DocumentStore() if vector_store else None
        self.retriever = RAGRetriever(
            vector_store=vector_store,
            embeddings=self.document_store.embeddings if self.document_store else None
        ) if vector_store else None

    async def process_message(
        self,
        user_id: str,
        message: str,
        conversation_id: Optional[str] = None,
        model: str = "gpt-4o",
        use_rag: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process a chat message using LlamaIndex workflows.

        Args:
            user_id: User ID
            message: User message
            conversation_id: Optional conversation ID
            model: Model to use
            use_rag: Whether to use RAG retrieval
            **kwargs: Additional parameters

        Returns:
            Response dict with assistant message, conversation ID, metadata
        """
        logger.info(f"Processing message for user {user_id}")

        # Create or get conversation
        if not conversation_id:
            conversation_id = await self._create_conversation(user_id, message)

        # Get or create LLM
        if not self.llm:
            self.llm = self.llm_factory.create_llm(model)

        # Create workflow
        workflow = ChatWorkflow(llm=self.llm)

        # Run workflow
        result = await workflow.run(
            message=message,
            user_id=user_id,
            conversation_id=conversation_id,
            use_rag=use_rag
        )

        # Format response
        return {
            "conversation_id": conversation_id,
            "user_message": {
                "id": str(uuid.uuid4()),
                "role": "user",
                "content": message
            },
            "assistant_message": {
                "id": str(uuid.uuid4()),
                "role": "assistant",
                "content": result["response"]
            },
            "model": model,
            "provider": "openai" if model.startswith("gpt") else "anthropic",
            "metadata": result.get("metadata", {})
        }

    async def upload_document(
        self,
        user_id: str,
        text: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Upload a document for RAG.

        Args:
            user_id: User ID
            text: Document text
            metadata: Optional metadata

        Returns:
            Upload result with document ID
        """
        if not self.document_store:
            raise ValueError("RAG not enabled")

        doc_id = await self.document_store.ingest_document(
            text=text,
            user_id=user_id,
            metadata=metadata
        )

        return {
            "status": "success",
            "document_id": doc_id
        }

    async def set_user_preference(
        self,
        user_id: str,
        model: str,
        temperature: float = 0.7,
        **kwargs
    ):
        """Set user preferences."""
        await execute_query(
            """
            INSERT INTO turfmapp_agent.user_preferences (user_id, default_model, settings)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id) DO UPDATE
            SET default_model = $2, settings = $3, updated_at = NOW()
            """,
            user_id,
            model,
            {"temperature": temperature, **kwargs}
        )

    async def _create_conversation(self, user_id: str, first_message: str) -> str:
        """Create new conversation."""
        conv_id = str(uuid.uuid4())

        # Generate title from first message
        title = first_message[:50] + "..." if len(first_message) > 50 else first_message

        await execute_query(
            """
            INSERT INTO turfmapp_agent.conversations (id, user_id, title)
            VALUES ($1, $2, $3)
            """,
            conv_id,
            user_id,
            title
        )

        return conv_id
```

### 5.2 Context Manager

Create `app/llamaindex/services/context_manager.py`:

```python
"""
Context Manager for smart context window management.
"""

from typing import List, Dict, Any, Optional
from llama_index.core.llms import ChatMessage, LLM
import logging

logger = logging.getLogger(__name__)

class ContextManager:
    """
    Manages conversation context windows with:
    - Token budget management
    - Priority-based message inclusion
    - Automatic summarization
    """

    def __init__(
        self,
        max_tokens: int = 4000,
        use_summarization: bool = True,
        llm: Optional[LLM] = None
    ):
        self.max_tokens = max_tokens
        self.use_summarization = use_summarization
        self.llm = llm

    async def prune_messages(
        self,
        messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Prune messages to fit within token budget.

        Args:
            messages: List of messages

        Returns:
            Pruned list of messages
        """
        # Count tokens
        total_tokens = self.count_tokens(messages)

        if total_tokens <= self.max_tokens:
            return messages

        # Keep system messages and recent messages
        system_messages = [m for m in messages if m.get("priority", 0) >= 10]
        user_messages = [m for m in messages if m.get("priority", 0) < 10]

        # Sort by recency and priority
        user_messages.sort(
            key=lambda m: (m.get("priority", 0), m.get("timestamp", 0)),
            reverse=True
        )

        # Build pruned list
        pruned = system_messages.copy()
        current_tokens = self.count_tokens(pruned)

        for msg in user_messages:
            msg_tokens = self.count_tokens([msg])
            if current_tokens + msg_tokens <= self.max_tokens:
                pruned.append(msg)
                current_tokens += msg_tokens
            else:
                break

        return pruned

    async def build_context(
        self,
        messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Build context with optional summarization.

        Args:
            messages: List of messages

        Returns:
            Context dict with messages and optional summary
        """
        pruned = await self.prune_messages(messages)

        result = {"messages": pruned}

        # Generate summary if enabled and many messages
        if self.use_summarization and len(messages) > 20 and self.llm:
            old_messages = messages[:-10]  # Summarize old messages
            summary = await self._summarize_messages(old_messages)
            result["summary"] = summary

        return result

    def count_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """Count tokens in messages."""
        # Simple approximation: 4 chars per token
        total_chars = sum(
            len(str(m.get("content", "")))
            for m in messages
        )
        return total_chars // 4

    async def _summarize_messages(
        self,
        messages: List[Dict[str, Any]]
    ) -> str:
        """Summarize old messages."""
        if not self.llm:
            return ""

        # Format messages
        formatted = "\n".join([
            f"{m.get('role', 'unknown')}: {m.get('content', '')}"
            for m in messages
        ])

        prompt = f"""Summarize this conversation in 2-3 sentences:

{formatted}

Summary:"""

        response = await self.llm.acomplete(prompt)
        return response.text
```

### 5.3 Deliverables

- [ ] `chat_service_v2.py` - New chat service with workflows
- [ ] `context_manager.py` - Smart context management
- [ ] `llm_factory.py` - Multi-model factory (from Phase 2)
- [ ] Unit tests for chat service
- [ ] Integration tests for end-to-end chat flow
- [ ] API compatibility tests

---

## Phase 6: API Layer Adaptation (Week 6)

### 6.1 Update REST Endpoints

Modify `app/api/v1/chat.py`:

```python
"""
Updated Chat API endpoints with LlamaIndex v2 support.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

from ...core.jwt_auth import get_current_user_from_token
from ...llamaindex.services.chat_service_v2 import ChatServiceV2
from ...services.chat_service import EnhancedChatService  # Old service for fallback

logger = logging.getLogger(__name__)
router = APIRouter()

# Feature flag for gradual rollout
USE_LLAMAINDEX_V2 = True  # Set to True to use new system

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    model: Optional[str] = "gpt-4o"
    use_rag: bool = False
    use_llamaindex: bool = True  # New parameter

class ChatResponse(BaseModel):
    conversation_id: str
    user_message: Dict[str, Any]
    assistant_message: Dict[str, Any]
    model: str
    provider: str
    metadata: Optional[Dict[str, Any]] = None

@router.post("/send", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    user_id: str = Depends(get_current_user_from_token)
):
    """
    Send a chat message.
    Supports both old and new (LlamaIndex) backends.
    """
    try:
        # Route to appropriate service
        if request.use_llamaindex and USE_LLAMAINDEX_V2:
            logger.info(f"Using LlamaIndex v2 for user {user_id}")
            service = ChatServiceV2()

            result = await service.process_message(
                user_id=user_id,
                message=request.message,
                conversation_id=request.conversation_id,
                model=request.model,
                use_rag=request.use_rag
            )
        else:
            logger.info(f"Using legacy service for user {user_id}")
            service = EnhancedChatService()

            result = await service.process_chat_request(
                user_id=user_id,
                message=request.message,
                conversation_id=request.conversation_id,
                model=request.model
            )

        return result

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_from_token)
):
    """
    Upload a document for RAG.
    """
    try:
        service = ChatServiceV2()

        # Read file content
        content = await file.read()
        text = content.decode('utf-8')

        result = await service.upload_document(
            user_id=user_id,
            text=text,
            metadata={"filename": file.filename}
        )

        return result

    except Exception as e:
        logger.error(f"Document upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents")
async def list_documents(
    user_id: str = Depends(get_current_user_from_token)
):
    """List user's uploaded documents."""
    # TODO: Implement document listing
    return {"documents": []}

@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    user_id: str = Depends(get_current_user_from_token)
):
    """Delete a document."""
    # TODO: Implement document deletion
    return {"status": "success"}

@router.post("/migrate-conversation/{conversation_id}")
async def migrate_conversation(
    conversation_id: str,
    user_id: str = Depends(get_current_user_from_token)
):
    """
    Migrate an old conversation to LlamaIndex format.
    """
    try:
        # TODO: Implement migration logic
        # 1. Load old conversation
        # 2. Convert to LlamaIndex memory format
        # 3. Save new format

        return {
            "status": "success",
            "conversation_id": conversation_id,
            "migrated": True
        }

    except Exception as e:
        logger.error(f"Migration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

### 6.2 Deliverables

- [ ] Updated `/api/v1/chat.py` with v2 support
- [ ] New document upload/delete endpoints
- [ ] Migration endpoint for old conversations
- [ ] Feature flag system for gradual rollout
- [ ] API documentation updates
- [ ] Postman collection for new endpoints

---

## Phase 7: Comprehensive Test Suite (Week 7-8)

See detailed test specifications in separate sections above. Summary of test coverage:

### Test Files to Create (25+)

**Unit Tests:**
- `tests/llamaindex/test_tools/test_gmail_tools.py`
- `tests/llamaindex/test_tools/test_drive_tools.py`
- `tests/llamaindex/test_tools/test_calendar_tools.py`
- `tests/llamaindex/test_memory/test_conversation_memory.py`
- `tests/llamaindex/test_memory/test_user_memory.py`
- `tests/llamaindex/test_rag/test_document_store.py`
- `tests/llamaindex/test_rag/test_retriever.py`
- `tests/llamaindex/test_rag/test_ingestion.py`
- `tests/llamaindex/test_workflows.py`
- `tests/llamaindex/test_agents.py`
- `tests/llamaindex/test_services/test_chat_service_v2.py`
- `tests/llamaindex/test_services/test_context_manager.py`

**Integration Tests:**
- `tests/integration/test_end_to_end_chat.py`
- `tests/integration/test_rag_pipeline.py`
- `tests/integration/test_tool_execution_flow.py`

**Regression Tests:**
- `tests/regression/test_critical_flows_v2.py`
- `tests/regression/test_backward_compatibility.py`

**Performance Tests:**
- `tests/performance/test_workflow_latency.py`
- `tests/performance/test_memory_usage.py`
- `tests/performance/test_rag_retrieval_speed.py`

### Test Configuration

**Update `pytest.ini`:**
```ini
[pytest]
asyncio_mode = auto
testpaths = tests
addopts =
    --cov=app/llamaindex
    --cov=app/services
    --cov-report=term-missing
    --cov-report=html
    --cov-fail-under=35
    -v

markers =
    unit: Unit tests
    integration: Integration tests
    regression: Regression tests
    performance: Performance tests
```

**Update Dockerfile:**
```dockerfile
# Test during build
RUN python -m pytest tests/llamaindex/ \
                     tests/regression/test_critical_flows_v2.py \
                     --cov=app/llamaindex \
                     --cov-fail-under=35 \
                     -v
```

### 7.4 Deliverables

- [ ] 25+ new test files covering all components
- [ ] Test fixtures in `conftest.py`
- [ ] Mock objects for external APIs
- [ ] Integration test suite
- [ ] Regression test suite
- [ ] Performance benchmarks
- [ ] Updated test documentation
- [ ] CI/CD integration

---

## Phase 8: Deployment & Monitoring (Week 8)

### 8.1 Gradual Rollout Strategy

**Week 8.1: Internal Testing**
- Deploy to staging environment
- Enable for internal test users (10%)
- Monitor for errors and performance issues
- Collect feedback

**Week 8.2: Beta Testing**
- Enable for beta users (25%)
- A/B testing: compare v1 vs v2 metrics
- Monitor:
  - Response latency
  - Token usage
  - Error rates
  - User satisfaction

**Week 8.3: Gradual Rollout**
- 50% traffic to v2
- Continue monitoring
- Fix any issues found

**Week 8.4: Full Deployment**
- 100% traffic to v2
- Keep v1 as fallback for 2 weeks
- Final performance tuning

### 8.2 Monitoring & Observability

**Metrics to Track:**

1. **Performance Metrics**
   - Workflow execution time
   - RAG retrieval latency
   - Tool execution duration
   - End-to-end response time

2. **Quality Metrics**
   - RAG retrieval relevance scores
   - Tool execution success rate
   - LLM token usage
   - User satisfaction ratings

3. **System Metrics**
   - Memory usage
   - Database query performance
   - Vector search performance
   - Error rates by component

**Logging Strategy:**
```python
# Add structured logging throughout
logger.info(
    "Workflow completed",
    extra={
        "user_id": user_id,
        "workflow_type": "chat",
        "duration_ms": duration,
        "tools_used": len(tool_calls),
        "rag_enabled": use_rag
    }
)
```

**Alerting:**
- Alert on error rate > 5%
- Alert on p95 latency > 5 seconds
- Alert on RAG retrieval failures
- Alert on tool execution failures

### 8.3 Deliverables

- [ ] Deployment scripts for staging/production
- [ ] Feature flag configuration
- [ ] Monitoring dashboards
- [ ] Alert configuration
- [ ] Rollback procedures
- [ ] Performance benchmarks documented
- [ ] User migration guides

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| LlamaIndex API changes | High | Pin specific versions, monitor releases |
| Performance degradation | High | Extensive performance testing, rollback plan |
| Data migration issues | High | Thorough testing, backup procedures |
| Vector search slow | Medium | Optimize indexes, implement caching |
| Tool integration breaks | Medium | Comprehensive integration tests |

### Business Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| User confusion | Medium | Clear documentation, gradual rollout |
| Increased costs | Medium | Monitor token usage, optimize prompts |
| Downtime during migration | High | Feature flags, zero-downtime deployment |
| Data loss | Critical | Backups, migration testing |

### Mitigation Strategies

1. **Feature Flags**: Enable safe rollback at any time
2. **Comprehensive Testing**: 35%+ code coverage with all test types
3. **Gradual Rollout**: 10% → 25% → 50% → 100%
4. **Monitoring**: Real-time alerts on key metrics
5. **Backup Plan**: Keep old system running for 2 weeks
6. **Documentation**: Complete migration guides and runbooks

---

## Success Metrics

### Technical Success Criteria

- [ ] All 61 existing tests pass
- [ ] New test coverage >35%
- [ ] Zero data loss during migration
- [ ] p95 latency <3 seconds
- [ ] Error rate <2%
- [ ] RAG retrieval accuracy >80%

### Business Success Criteria

- [ ] User satisfaction maintained or improved
- [ ] Support tickets not increased
- [ ] Token costs optimized (±10% of current)
- [ ] New RAG features adopted by >20% users
- [ ] Tool execution success rate >95%

### Feature Completeness

- [ ] All existing features working in v2
- [ ] RAG document upload functional
- [ ] Multi-model switching working
- [ ] Advanced memory functional
- [ ] Tool orchestration improved
- [ ] Backward compatibility verified

---

## Timeline Summary

| Week | Phase | Deliverables |
|------|-------|--------------|
| 1 | Foundation | Dependencies, DB schema, directory structure |
| 2-3 | Core Integration | LLM factory, memory, tools |
| 3-4 | Workflows | Chat, tool, RAG workflows |
| 4-5 | RAG | Document store, retriever, ingestion |
| 5-6 | Chat Service | ChatServiceV2, context manager |
| 6 | API Layer | Updated endpoints, migration |
| 7-8 | Testing | Comprehensive test suite (25+ files) |
| 8 | Deployment | Gradual rollout, monitoring |

**Total Duration: 8 weeks**
**Team Size: 1-2 senior engineers**

---

## Appendix

### A. LlamaIndex Resources

- Documentation: https://docs.llamaindex.ai/
- GitHub: https://github.com/run-llama/llama_index
- Discord Community: https://discord.gg/dGcwcsnxhU
- Examples: https://github.com/run-llama/llama_index/tree/main/docs/examples

### B. Migration Checklist

**Pre-Migration:**
- [ ] Backup all production data
- [ ] Document current system behavior
- [ ] Set up staging environment
- [ ] Install dependencies
- [ ] Run database migrations

**During Migration:**
- [ ] Deploy with feature flag disabled
- [ ] Run smoke tests
- [ ] Enable for test users
- [ ] Monitor metrics
- [ ] Collect feedback

**Post-Migration:**
- [ ] Full rollout
- [ ] Archive old code
- [ ] Update documentation
- [ ] Conduct retrospective
- [ ] Plan next improvements

### C. Glossary

- **RAG**: Retrieval-Augmented Generation - combining document retrieval with LLM generation
- **LlamaIndex**: Data framework for LLM applications
- **Workflow**: Multi-step orchestration pattern
- **Vector Store**: Database for storing embeddings
- **Embedding**: Numerical representation of text for semantic search
- **MMR**: Maximal Marginal Relevance - diversity in search results
- **FunctionTool**: LlamaIndex abstraction for tool calling

---

## Conclusion

This migration to LlamaIndex is **highly feasible** and will significantly enhance the TurfMapp AI Agent's capabilities. The complete rewrite approach allows for clean implementation of best practices while the comprehensive test suite ensures reliability.

**Key Benefits:**
- ✅ Modern, maintainable architecture
- ✅ Advanced features (RAG, workflows, memory)
- ✅ Industry-standard patterns
- ✅ Reduced code complexity
- ✅ Better scalability

**Next Steps:**
1. Review and approve this plan
2. Set up development environment
3. Begin Phase 1: Foundation
4. Weekly progress reviews

For questions or clarifications, please contact the development team.

---

**Document Version**: 1.0
**Last Updated**: January 2025
**Status**: Ready for Implementation

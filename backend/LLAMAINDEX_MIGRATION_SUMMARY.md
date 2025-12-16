# LlamaIndex Migration Summary

## Overview

This document summarizes the LlamaIndex integration implementation for the TurfMapp AI Agent project. The migration introduces a modern, scalable architecture for LLM operations, conversation memory, tool management, and workflow orchestration.

**Date**: January 20, 2025  
**Status**: Phase 2 & 3 Complete  
**Total Tests**: 52 LlamaIndex tests (100% passing)

---

## Architecture

### Components Hierarchy

```
app/llamaindex/
├── services/          # Core services
│   ├── llm_factory.py        # Multi-model LLM interface
│   └── README.md             # Usage documentation
├── memory/            # Conversation memory
│   └── conversation_memory.py # Auto-summarization & entity extraction
├── tools/             # Google service integrations
│   ├── gmail_tools.py        # Gmail operations (2 tools)
│   ├── drive_tools.py        # Drive operations (4 tools)
│   └── calendar_tools.py     # Calendar operations (3 tools)
└── workflows/         # Workflow orchestration
    ├── base_workflow.py      # Base classes & state management
    ├── chat_workflow.py      # Conversational workflow
    └── tool_workflow.py      # Tool-based workflow
```

---

## Phase 1: Local Database Setup

### PostgreSQL Configuration
- **Version**: PostgreSQL 17
- **Location**: `/Library/PostgreSQL/17/`
- **Database**: `turfmapp_dev`
- **User**: `turfmapp_agent`
- **Extensions**: pgvector 0.8.1

### Database Schema
Created 8 tables in `turfmapp_agent` schema:
1. `users` - User accounts
2. `conversations` - Conversation sessions
3. `messages` - Chat messages
4. `user_preferences` - User settings
5. `document_nodes` - Document chunks for RAG
6. `embeddings` - Vector embeddings (1536-dim)
7. `memory_states` - Conversation summaries & entities
8. `workflow_executions` - Workflow execution logs

---

## Phase 2: Core LlamaIndex Integration

### 1. LLM Factory (`app/llamaindex/services/llm_factory.py`)

**Purpose**: Unified interface for multiple LLM providers

**Models Supported**:
- **OpenAI**: GPT-4o, GPT-4o Mini, GPT-3.5 Turbo
- **Anthropic**: Claude Sonnet 4.5, Claude 3.5 Sonnet, Claude 3 Haiku

**Key Features**:
- Task-based model recommendations (chat, code, analysis, summarization, tool use)
- Cost estimation (input/output tokens)
- Model capability tracking (function calling, streaming, vision, large context)
- Automatic provider selection based on API key availability

**Usage Example**:
```python
from app.llamaindex.services.llm_factory import llm_factory, TaskType

# Get recommended model for task
model_id = llm_factory.recommend_model_for_task(TaskType.CHAT)

# Create LLM instance
llm = llm_factory.create_llm(
    model_id=model_id,
    temperature=0.7,
    max_tokens=2048
)

# Use with LlamaIndex
response = await llm.acomplete("What is Python?")
```

**Tests**: 18 tests covering model creation, recommendations, cost estimation

---

### 2. Conversation Memory (`app/llamaindex/memory/conversation_memory.py`)

**Purpose**: Intelligent conversation memory with auto-summarization

**Key Features**:
- **ChatMemoryBuffer**: LlamaIndex buffer for recent messages
- **Auto-summarization**: Triggered at configurable threshold (default: 30 messages)
- **Entity Extraction**: LLM-powered extraction of people, places, topics
- **PostgreSQL Persistence**: Messages and memory states saved to database
- **Memory Caching**: Performance optimization via MemoryManager

**Architecture**:
```
ConversationMemory
├── Buffer (recent 20 messages)
├── Summary (generated every 30 messages)
├── Entities (extracted automatically)
└── Database persistence
```

**Usage Example**:
```python
from app.llamaindex.memory.conversation_memory import MemoryManager

# Initialize manager
memory_manager = MemoryManager(db_pool=db_pool)

# Get memory for conversation
memory = memory_manager.get_memory(
    user_id="user-123",
    conversation_id="conv-456"
)

# Load from database
await memory.load_from_database()

# Add messages
await memory.add_message("user", "Hello, how are you?")
await memory.add_message("assistant", "I'm doing well, thank you!")

# Get formatted context
context = await memory.get_context(
    include_summary=True,
    include_entities=True
)
```

**Tests**: 23 tests covering messages, summarization, entities, persistence

---

### 3. Google Tools (LlamaIndex FunctionTools)

#### Gmail Tools (`app/llamaindex/tools/gmail_tools.py`)

**Tools**:
1. `search_gmail_messages` - Search with Gmail operators (is:unread, from:, subject:, etc.)
2. `get_gmail_message` - Get detailed message content by ID

**Example**:
```python
from app.llamaindex.tools.gmail_tools import create_gmail_tools

tools = create_gmail_tools(credentials)
# Returns 2 FunctionTool instances ready for agent use
```

#### Drive Tools (`app/llamaindex/tools/drive_tools.py`)

**Tools**:
1. `search_drive_files` - Search with filters (search_term, file_type, year)
2. `search_drive_folders` - Search for folders by name
3. `list_recent_drive_files` - List recently modified files
4. `list_shared_drives` - List shared/team drives

**Example**:
```python
from app.llamaindex.tools.drive_tools import create_drive_tools

tools = create_drive_tools(credentials)
# Returns 4 FunctionTool instances
```

#### Calendar Tools (`app/llamaindex/tools/calendar_tools.py`)

**Tools**:
1. `list_upcoming_calendar_events` - List future events
2. `list_recent_calendar_events` - List past and upcoming events
3. `search_calendar_events` - Search by keywords in summary/description

**Example**:
```python
from app.llamaindex.tools.calendar_tools import create_calendar_tools

tools = create_calendar_tools(credentials)
# Returns 3 FunctionTool instances
```

**Tests**: 11 tests covering all 9 tools (creation, descriptions, metadata)

---

## Phase 3: Workflow Orchestration

### Base Workflow (`app/llamaindex/workflows/base_workflow.py`)

**Purpose**: Foundation for all workflow types

**Key Classes**:
- `WorkflowType`: Enum for workflow types (CHAT, TOOL, RAG, HYBRID)
- `WorkflowState`: Enum for execution states (PENDING, RUNNING, COMPLETED, FAILED)
- `WorkflowContext`: Stores state, messages, events, metadata
- `WorkflowEvent`: Base event for workflow operations
- `BaseAgentWorkflow`: Base class with error handling and logging

**Features**:
- State management across workflow steps
- Event tracking for auditing
- Error handling and recovery
- Execution metadata

---

### Chat Workflow (`app/llamaindex/workflows/chat_workflow.py`)

**Purpose**: Handle conversational interactions with memory

**Workflow Steps**:
1. **Prepare Context**: Load conversation memory
2. **Build Messages**: Construct message list with history
3. **Generate Response**: Call LLM for response
4. **Save to Memory**: Persist conversation

**Usage Example**:
```python
from app.llamaindex.workflows import ChatWorkflow, ChatWorkflowInput

# Create workflow
workflow = ChatWorkflow(
    memory_manager=memory_manager,
    default_system_prompt="You are a helpful assistant."
)

# Create input
workflow_input = ChatWorkflowInput(
    user_id="user-123",
    conversation_id="conv-456",
    message="What is machine learning?",
    model_id="gpt-4o",
    temperature=0.7,
    include_memory=True
)

# Execute workflow
output = await workflow.run(input=workflow_input)

# Access response
print(output.response)
print(f"Model used: {output.model_used}")
print(f"State: {output.context.state}")
```

**Features**:
- Automatic memory integration
- Conversation context from history
- Model selection per request
- Token usage tracking

---

### Tool Workflow (`app/llamaindex/workflows/tool_workflow.py`)

**Purpose**: Handle tool-based operations using ReAct agent

**Workflow Steps**:
1. **Prepare Agent**: Create ReAct agent with tools
2. **Build Context**: Load conversation history
3. **Execute Agent**: Run agent with tools (iterative reasoning)
4. **Save to Memory**: Persist results

**Usage Example**:
```python
from app.llamaindex.workflows import ToolWorkflow, ToolWorkflowInput
from app.llamaindex.tools import create_gmail_tools, create_drive_tools

# Get credentials (from OAuth)
credentials = get_user_credentials(user_id)

# Create tools
gmail_tools = create_gmail_tools(credentials)
drive_tools = create_drive_tools(credentials)
all_tools = gmail_tools + drive_tools

# Create workflow
workflow = ToolWorkflow(
    memory_manager=memory_manager,
    default_system_prompt="Use tools to help answer questions."
)

# Create input
workflow_input = ToolWorkflowInput(
    user_id="user-123",
    conversation_id="conv-456",
    message="Find all unread emails from boss@company.com",
    tools=all_tools,
    max_iterations=10,
    include_memory=True
)

# Execute workflow
output = await workflow.run(input=workflow_input)

# Access response
print(output.response)
print(f"Tools used: {output.tools_used}")
print(f"Iterations: {output.iterations}")
```

**Features**:
- Multi-tool support (Gmail, Drive, Calendar)
- ReAct (Reasoning + Acting) pattern
- Iterative problem solving
- Tool usage tracking

---

## Integration with Existing System

### How to Use in Existing Endpoints

**Example: Chat Endpoint Integration**
```python
from fastapi import APIRouter, Depends
from app.llamaindex.workflows import ChatWorkflow, ChatWorkflowInput
from app.llamaindex.memory.conversation_memory import MemoryManager

router = APIRouter()

# Initialize once at startup
memory_manager = MemoryManager(db_pool=db_pool)

@router.post("/chat")
async def chat(
    message: str,
    user_id: str = Depends(get_current_user),
    conversation_id: str = Depends(get_conversation_id)
):
    # Create workflow
    workflow = ChatWorkflow(memory_manager=memory_manager)
    
    # Create input
    workflow_input = ChatWorkflowInput(
        user_id=user_id,
        conversation_id=conversation_id,
        message=message,
        include_memory=True
    )
    
    # Execute
    output = await workflow.run(input=workflow_input)
    
    # Return response
    return {
        "response": output.response,
        "model": output.model_used,
        "conversation_id": conversation_id
    }
```

**Example: Tool Endpoint Integration**
```python
@router.post("/tools/execute")
async def execute_tools(
    message: str,
    user_id: str = Depends(get_current_user),
    credentials: Credentials = Depends(get_google_credentials)
):
    # Create tools
    from app.llamaindex.tools import (
        create_gmail_tools,
        create_drive_tools,
        create_calendar_tools
    )
    
    tools = (
        create_gmail_tools(credentials) +
        create_drive_tools(credentials) +
        create_calendar_tools(credentials)
    )
    
    # Create workflow
    workflow = ToolWorkflow(memory_manager=memory_manager)
    
    # Create input
    workflow_input = ToolWorkflowInput(
        user_id=user_id,
        conversation_id=f"tool-{user_id}",
        message=message,
        tools=tools,
        max_iterations=10
    )
    
    # Execute
    output = await workflow.run(input=workflow_input)
    
    return {
        "response": output.response,
        "tools_used": output.tools_used,
        "iterations": output.iterations
    }
```

---

## Testing

### Test Suite Summary

**Total Tests**: 52 (100% passing)

**Breakdown**:
- LLM Factory: 18 tests
- Conversation Memory: 23 tests  
- Google Tools: 11 tests

**Run Tests**:
```bash
# Run all LlamaIndex tests
python -m pytest tests/llamaindex/ -v

# Run specific test file
python -m pytest tests/llamaindex/test_llm_factory.py -v

# Run with coverage
python -m pytest tests/llamaindex/ --cov=app/llamaindex
```

---

## Configuration

### Environment Variables

```bash
# OpenAI
OPENAI_API_KEY=sk-...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Database
SUPABASE_DB_URL=postgresql://turfmapp_agent:password@localhost:5432/turfmapp_dev

# Google OAuth (for tools)
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

---

## Performance Considerations

### Memory Management
- Buffer limited to 20 recent messages
- Auto-summarization at 30 message threshold
- Memory caching via MemoryManager
- Database indexing on conversation_id and user_id

### Cost Optimization
- Use `llm_factory.estimate_cost()` before requests
- Task-based model selection (use cheaper models for simple tasks)
- GPT-4o Mini for summarization
- GPT-4o for complex reasoning and tool use

### Token Limits
- GPT-4o: 128k context window
- Claude Sonnet 4.5: 200k context window
- Automatic truncation in memory buffer

---

## Next Steps

### Immediate Integration Tasks
1. **Update conversation endpoints** to use ChatWorkflow
2. **Update tool endpoints** to use ToolWorkflow  
3. **Migrate existing memory** to ConversationMemory
4. **Add workflow execution logging** to database

### Future Enhancements
1. **RAG Workflow**: Document retrieval and question answering
2. **Streaming Support**: Real-time response streaming
3. **Workflow Persistence**: Save/resume long-running workflows
4. **Tool Caching**: Cache tool results for performance
5. **Multi-Agent Workflows**: Orchestrate multiple agents

---

## File Structure

```
backend/
├── app/
│   ├── llamaindex/
│   │   ├── __init__.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── llm_factory.py      (400+ lines)
│   │   │   └── README.md           (196 lines)
│   │   ├── memory/
│   │   │   ├── __init__.py
│   │   │   └── conversation_memory.py  (450+ lines)
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── gmail_tools.py      (200+ lines)
│   │   │   ├── drive_tools.py      (300+ lines)
│   │   │   └── calendar_tools.py   (300+ lines)
│   │   └── workflows/
│   │       ├── __init__.py
│   │       ├── base_workflow.py    (300+ lines)
│   │       ├── chat_workflow.py    (300+ lines)
│   │       └── tool_workflow.py    (350+ lines)
├── tests/
│   └── llamaindex/
│       ├── __init__.py
│       ├── test_llm_factory.py         (18 tests)
│       ├── test_conversation_memory.py (23 tests)
│       └── test_google_tools.py        (11 tests)
├── scripts/
│   ├── setup_local_db.sh
│   ├── create_turfmapp_user.sh
│   └── install_pgvector.sh
└── LLAMAINDEX_MIGRATION_SUMMARY.md (this file)
```

**Total Lines of Code**: ~3000+ lines
**Total Test Lines**: ~1500+ lines

---

## Dependencies

```toml
# requirements.txt additions
llama-index==0.14.5              # Core framework
llama-index-llms-openai==0.1.13  # OpenAI integration
llama-index-llms-anthropic==0.1.9 # Anthropic integration
llama-index-embeddings-openai==0.1.6  # OpenAI embeddings
pgvector==0.8.1                  # Vector database support
```

---

## References

- [LlamaIndex Documentation](https://docs.llamaindex.ai/)
- [LlamaIndex Workflows](https://docs.llamaindex.ai/en/stable/module_guides/workflow/)
- [LlamaIndex Agents](https://docs.llamaindex.ai/en/stable/module_guides/deploying/agents/)
- [OpenAI API](https://platform.openai.com/docs)
- [Anthropic API](https://docs.anthropic.com/)

---

**Generated**: January 20, 2025  
**Author**: Claude Code  
**Project**: TurfMapp AI Agent - LlamaIndex Migration

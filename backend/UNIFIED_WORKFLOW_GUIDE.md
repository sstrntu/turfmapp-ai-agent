# Unified Workflow Guide

## Overview

The Unified Workflow is an intelligent agent system that automatically decides which tools to use based on the user's query. It combines:

- **RAG (Retrieval-Augmented Generation)** for document queries
- **Gmail Tools** for email tasks
- **Drive Tools** for file management
- **Calendar Tools** for scheduling
- **Direct LLM** for general knowledge questions

The system uses **LlamaIndex's ReActAgent** to analyze queries and autonomously select the appropriate tools.

---

## How It Works

```
User Query
    ↓
[UnifiedWorkflow]
    ↓
1. Load Memory (user facts + conversation history)
    ↓
2. Prepare All Available Tools
   ├─ RAG Tools (search_documents, list_documents)
   ├─ Gmail Tools (if credentials available)
   ├─ Drive Tools (if credentials available)
   └─ Calendar Tools (if credentials available)
    ↓
3. Execute ReActAgent
   - Agent analyzes query
   - Decides which tools to use (or none)
   - Executes tools in appropriate order
   - Generates response
    ↓
4. Save to Memory & Return Response
```

---

## Key Features

### 🧠 **Intelligent Tool Selection**

The agent automatically chooses the right tools:

| Query Type | Tools Used | Example |
|------------|-----------|---------|
| Document question | `search_documents` | "What does my PDF say about ML?" |
| Email task | Gmail tools | "Find emails from john@example.com" |
| File management | Drive tools | "List my recent Drive files" |
| Scheduling | Calendar tools | "What meetings do I have tomorrow?" |
| General question | None (direct answer) | "What is machine learning?" |
| Complex task | Multiple tools | "Find the deadline in my emails and create a calendar event" |

### 💾 **Memory Integration**

- **User Memory**: Facts about the user (name, preferences, background) persist across all conversations
- **Conversation Memory**: Recent messages from the current conversation
- **Automatic Fact Extraction**: Learns new facts about users from conversations

### 🔄 **Multi-Step Reasoning**

The ReActAgent can:
- Chain multiple tool calls together
- Reason about tool outputs
- Make decisions based on intermediate results
- Handle complex, multi-step tasks

---

## API Endpoint

### Chat with Intelligent Tool Selection

**`POST /api/v2/chat/send`**

Uses the Unified Workflow with intelligent tool selection.

```json
{
  "message": "What does my uploaded PDF say about neural networks?",
  "conversation_id": "optional-uuid",
  "model": "gpt-4o",  // optional, auto-selects if not provided
  "temperature": 0.7,
  "include_memory": true
}
```

**Response:**
```json
{
  "conversation_id": "uuid",
  "user_message": {...},
  "assistant_message": {
    "content": "According to your PDF...",
    "metadata": {
      "model": "gpt-4o",
      "tools_used": ["search_documents"],
      "reasoning_steps": [...]
    }
  },
  "model_used": "gpt-4o",
  "provider": "openai"
}
```

---

## Tool Descriptions

### RAG Tools

#### 1. `search_documents`
Searches through user's uploaded documents using vector similarity search.

**When it's used:**
- User asks about document content
- Questions reference "my PDF", "my files", "uploaded documents"
- Specific information requests that might be in documents

**Example queries:**
- "What does my contract say about termination?"
- "Find information about pricing in my documents"
- "Summarize the key points from my uploaded PDF"

#### 2. `list_documents`
Lists all documents user has uploaded.

**When it's used:**
- User wants to know what documents are available
- Checking if specific document was uploaded
- Getting overview of document library

**Example queries:**
- "What documents have I uploaded?"
- "Do I have a contract file uploaded?"
- "Show me my document library"

### Gmail Tools

Activated when user has connected Google account:
- `search_gmail`: Search emails by keywords
- `get_gmail_thread`: Get email thread details
- `list_gmail_labels`: List Gmail labels/folders
- And more...

### Drive Tools

Activated when user has connected Google account:
- `search_drive`: Search files by name
- `list_drive_files`: List recent files
- `get_drive_file_info`: Get file metadata
- And more...

### Calendar Tools

Activated when user has connected Google account:
- `list_calendar_events`: List upcoming events
- `search_calendar`: Search events
- `get_event_details`: Get event information
- And more...

---

## Decision Flow

### How the Agent Decides

1. **Query Analysis**: Agent analyzes the user's natural language query

2. **Intent Classification**: Determines what type of task this is:
   - Information retrieval? → Consider RAG
   - Email-related? → Consider Gmail tools
   - File-related? → Consider Drive tools
   - Scheduling-related? → Consider Calendar tools
   - General knowledge? → Answer directly

3. **Tool Selection**: Chooses 0 or more tools to use

4. **Execution**: Runs selected tools and processes results

5. **Response Generation**: Creates final answer based on tool outputs and reasoning

### Example: Complex Multi-Tool Query

**Query:** "Find the project deadline in my emails and check if I have any uploaded documents about the project"

**Agent's Reasoning:**
1. Analyzes query → Needs both email search AND document search
2. Selects tools: `search_gmail`, `search_documents`
3. First calls `search_gmail("project deadline")`
4. Then calls `search_documents("project")`
5. Combines results: "Based on your email from... and your uploaded document..."

---

## Configuration

### Chunk Settings (for RAG)

Current settings in `app/api/v1/rag.py`:
```python
chunk_size=1024,      # Characters per chunk
chunk_overlap=128,    # Overlap between chunks
```

**Why these values?**
- 1024 chars provides enough context for semantic understanding
- 128 char overlap prevents information loss at boundaries
- Results in better similarity scores (0.7-0.9 for good matches)

### Model Selection

The workflow auto-selects models based on task:
- **Tool Use**: `gpt-4o` (best function calling)
- **RAG Answer Generation**: `gpt-4o-mini` (faster, cheaper)
- **Fact Extraction**: `gpt-4o-mini` (simple task)

You can override by specifying `model` in request.

### Similarity Threshold

In `unified_workflow.py`:
```python
similarity_threshold=0.3  # Minimum similarity for RAG results
```

- 0.3 = Catches more results (may include less relevant)
- 0.7 = Only highly relevant results
- Adjust based on your needs

---

## Testing

### Basic Test

```bash
# Test document query
curl -X POST http://localhost:8000/api/v2/chat/send \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT" \
  -d '{
    "message": "What does my uploaded PDF say about machine learning?"
  }'
```

### Check Tools Used

Look at the response metadata:
```json
{
  "assistant_message": {
    "metadata": {
      "tools_used": ["search_documents"],  // ← Shows which tools were used
      "reasoning_steps": [...]
    }
  }
}
```

### Verify RAG Working

1. Upload a document via `/api/v1/rag/upload`
2. Ask a question about it via `/send-smart`
3. Check response includes: `"tools_used": ["search_documents"]`

---


## Architecture

### Components

```
app/llamaindex/
├── workflows/
│   ├── unified_workflow.py      # Main workflow orchestration
│   ├── tool_workflow.py         # Tool-only workflow
│   └── base_workflow.py         # Base classes
├── tools/
│   ├── rag_tools.py            # RAG as tools
│   ├── gmail_tools.py          # Gmail integration
│   ├── drive_tools.py          # Drive integration
│   └── calendar_tools.py       # Calendar integration
├── memory/
│   ├── conversation_memory.py  # Per-conversation memory
│   └── user_memory.py          # Cross-conversation facts
└── rag/
    ├── document_ingestion.py   # Document upload & chunking
    ├── vector_store.py         # Embedding & search
    └── rag_query.py           # RAG query service
```

### Workflow Steps

1. **`load_memory`**: Load user facts and conversation history
2. **`prepare_tools`**: Initialize all available tools (RAG, Gmail, Drive, Calendar)
3. **`execute_agent`**: Run ReActAgent to analyze query and use tools
4. **`save_and_respond`**: Save to memory, extract new facts, return response

---

## Performance Tips

### Optimize for Speed

1. **Use caching** for repeated queries
2. **Limit conversation history** (currently 5 messages)
3. **Adjust `max_iterations`** if agent is too slow (default: 10)

### Optimize for Quality

1. **Increase similarity threshold** (0.5-0.7) for more precise RAG results
2. **Increase chunk size** (1500-2000) for more context
3. **Use better models** (gpt-4o instead of gpt-4o-mini)

---

## Troubleshooting

### Agent Not Using Tools

**Symptom:** `tools_used: []` even for document questions

**Causes:**
1. No documents uploaded yet
2. Query is ambiguous
3. Similarity threshold too high

**Solution:**
- Check documents exist: `/api/v1/rag/documents`
- Make query more specific: "my uploaded PDF" instead of "documents"
- Lower similarity threshold

### Wrong Tool Selected

**Symptom:** Agent uses Gmail when should use RAG

**Cause:** Agent reasoning based on query phrasing

**Solution:**
- Rephrase query to be more specific
- Mention "uploaded document" or "my files" explicitly

### Tools Not Available

**Symptom:** Google tools never used

**Cause:** User hasn't connected Google account

**Solution:**
- Complete Google OAuth flow
- Check credentials in database

---

## Future Enhancements

- [ ] **Streaming support** for real-time responses
- [ ] **Cost tracking** per tool usage
- [ ] **Tool result caching** for repeated queries
- [ ] **Custom tools** via plugin system
- [ ] **Multi-agent collaboration** for complex tasks
- [ ] **Tool usage analytics** dashboard

---

## Questions?

See also:
- `AGENT_USAGE_GUIDE.md` - Legacy agent endpoint docs
- `MEMORY_SYSTEM_EXPLAINED.md` - Memory architecture
- `NEXT_STEPS.md` - Implementation roadmap

For issues, check backend logs:
```bash
docker-compose logs -f backend | grep "unified_workflow"
```

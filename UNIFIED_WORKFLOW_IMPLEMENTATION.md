# Unified Workflow Implementation Complete ✅

## Overview

We've successfully built an **intelligent agent system** that automatically decides which tools to use based on user queries. This is the "ChatGPT-like" experience where the AI understands intent and routes to the appropriate tools.

---

## What Was Built

### 1. **RAG as Tools** (`backend/app/llamaindex/tools/rag_tools.py`)

Created two tools that the agent can use:
- **`search_documents`**: Search through uploaded documents
- **`list_documents`**: List available documents

These allow the agent to decide **when** to query documents instead of always querying them.

### 2. **Unified Workflow** (`backend/app/llamaindex/workflows/unified_workflow.py`)

A complete workflow that:
1. Loads user memory (facts) and conversation memory (history)
2. Prepares all available tools (RAG, Gmail, Drive, Calendar)
3. Uses ReActAgent to analyze query and select tools
4. Executes selected tools and generates response
5. Saves conversation and extracts new user facts

**Key Features:**
- **Intelligent routing**: Agent decides which tools to use
- **Multi-tool support**: Can use multiple tools in one query
- **Memory integration**: User facts + conversation history
- **Reasoning transparency**: Shows which tools were used

### 3. **Updated Chat Endpoint** (`backend/app/api/v1/chat_v2.py`)

The existing endpoint **`POST /api/v2/chat/send`** now uses the unified workflow!

Returns:
- Assistant response
- Tools used (transparency)
- Reasoning steps
- Model used

### 4. **Documentation** (`backend/UNIFIED_WORKFLOW_GUIDE.md`)

Comprehensive guide covering:
- How the system works
- API endpoints
- Tool descriptions
- Decision flow examples
- Configuration options
- Troubleshooting

### 5. **Test Script** (`backend/test_unified_workflow.py`)

Test suite to verify:
- General knowledge queries (no tools)
- Document queries (RAG tools)
- Memory integration
- Tool selection accuracy

---

## How It Works

### Decision Flow

```
User: "What does my PDF say about machine learning?"
    ↓
[Unified Workflow]
    ↓
1. Load Memory
   - User facts: name=Sira, role=developer
   - Recent conversation: last 5 messages
    ↓
2. Prepare Tools
   - RAG tools: ✅ Available (user has documents)
   - Gmail tools: ❌ No credentials
   - Drive tools: ❌ No credentials
   - Calendar tools: ❌ No credentials
    ↓
3. Execute Agent (ReActAgent)
   Thinks: "User is asking about their PDF"
   Decision: Use search_documents tool
   Action: search_documents("machine learning")
   Result: Found relevant chunks with score 0.85
    ↓
4. Generate Response
   "According to your uploaded PDF titled 'ML Guide'..."
    ↓
5. Save to Memory
   - Saves user message and response
   - Extracts new facts: user interested in ML
```

### Tool Selection Examples

| Query | Tools Used | Reasoning |
|-------|------------|-----------|
| "What is ML?" | None | General knowledge, no tools needed |
| "What does my PDF say?" | `search_documents` | Document-specific question |
| "List my files" | `list_documents` | Document inventory request |
| "Find emails from John" | `search_gmail` | Email task (if credentials) |
| "What's in my uploaded contract and when should I respond?" | `search_documents`, `search_gmail` | Multi-tool task |

---

## Key Improvements Over Previous System

### Before (Simple RAG)
```python
# Always query RAG, even if not needed
rag_result = await rag_service.query(message)
if rag_result['chunks_found'] > 0:
    # Add to context
    # LLM decides whether to use
```

**Problems:**
- ❌ Always queries even for "What is 2+2?"
- ❌ No access to Gmail, Drive, Calendar
- ❌ Can't combine multiple tools
- ❌ Wastes tokens on irrelevant context

### After (Unified Workflow)
```python
# Agent analyzes query first
workflow = UnifiedWorkflow(...)
result = await workflow.run(input)
# Agent decided which tools to use (or none)
```

**Benefits:**
- ✅ Only queries when needed
- ✅ Access to all tools (RAG, Gmail, Drive, Calendar)
- ✅ Can combine multiple tools intelligently
- ✅ More efficient token usage
- ✅ Transparent (shows reasoning)

---

## File Structure

```
backend/
├── app/
│   ├── api/v1/
│   │   └── chat_v2.py                    # ✨ New /send-smart endpoint
│   └── llamaindex/
│       ├── workflows/
│       │   ├── unified_workflow.py       # ✨ Main workflow
│       │   ├── tool_workflow.py          # (existing)
│       │   └── base_workflow.py          # (existing)
│       ├── tools/
│       │   ├── rag_tools.py             # ✨ RAG as tools
│       │   ├── gmail_tools.py           # (existing)
│       │   ├── drive_tools.py           # (existing)
│       │   └── calendar_tools.py        # (existing)
│       ├── memory/
│       │   ├── conversation_memory.py   # (existing)
│       │   └── user_memory.py           # (existing)
│       └── rag/
│           ├── document_ingestion.py    # (existing)
│           ├── vector_store.py          # (fixed)
│           └── rag_query.py            # (existing)
├── UNIFIED_WORKFLOW_GUIDE.md           # ✨ Documentation
└── test_unified_workflow.py            # ✨ Test script
```

---

## Testing

### Quick Test

```bash
# 1. Restart backend
cd backend
docker-compose restart backend

# 2. Test the endpoint (same endpoint, now smarter!)
curl -X POST http://localhost:8000/api/v2/chat/send \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "message": "What does my uploaded PDF say about machine learning?"
  }'

# 3. Check response
# Should include: "tools_used": ["search_documents"]
```

### Full Test Suite

```bash
# Update user_id in test_unified_workflow.py first!
python test_unified_workflow.py
```

---

## What's Different in the User Experience

### How It Works Now

```
User: "What does my PDF say about ML?"
🤖: [Analyzes query → Decides to use search_documents tool]
    [Searches documents → Finds relevant chunks]
    "According to your uploaded PDF titled 'ML Fundamentals'..."

    Response metadata shows:
    - tools_used: ["search_documents"]  ← Agent selected this
    - model: "gpt-4o"
    - reasoning_steps: [...]
```

**User Benefits:**
- 📄 Smarter about when to search documents
- 📧 Can handle Gmail questions (if connected)
- 📁 Can handle Drive questions (if connected)
- 📅 Can handle Calendar questions (if connected)
- 🔗 Can combine multiple tools in one query
- 💡 More transparent (shows which tools were used)

---

## Configuration

### Adjusting Tool Selection

In `unified_workflow.py`, you can modify the system prompt to guide tool selection:

```python
system_prompt_parts.append(
    "Think step by step and use tools only when necessary."
)
```

### Adjusting RAG Sensitivity

In `rag_tools.py`:

```python
similarity_threshold=0.3  # Lower = more results, higher = more precise
top_k=3  # Number of chunks to retrieve
```

### Adjusting Agent Behavior

In chat endpoint:

```python
workflow_input = UnifiedWorkflowInput(
    max_iterations=10,  # Max reasoning steps
    temperature=0.7,     # Creativity vs precision
)
```

---

## Future Enhancements

Based on this foundation, you can:

1. **Add More Tools**
   - Web search tool
   - Database query tool
   - API integration tools
   - Custom business logic tools

2. **Improve Decision Making**
   - Fine-tune prompts for better tool selection
   - Add query classification step
   - Implement tool usage analytics

3. **Add Streaming**
   - Stream agent reasoning in real-time
   - Show tools being executed live
   - Better UX for long-running queries

4. **Cost Optimization**
   - Cache tool results
   - Use cheaper models for simple tools
   - Implement query rewriting for efficiency

5. **Advanced Features**
   - Multi-agent collaboration
   - Parallel tool execution
   - Custom tool creation UI
   - Tool usage analytics dashboard

---

## Integration with Frontend

Your existing frontend code already works - no changes needed! The endpoint is the same:

```javascript
// In chat.js
async function sendMessage(message) {
    const response = await fetch('/api/v2/chat/send', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ message })
    });

    const data = await response.json();

    // Access tools used
    const toolsUsed = data.assistant_message.metadata.tools_used;

    // Show in UI: "🔧 Used tools: search_documents"
    if (toolsUsed.length > 0) {
        showToolIndicator(toolsUsed);
    }
}
```

---

## Rollout Strategy

### ✅ Already Done - Drop-in Replacement

The `/send` endpoint has been replaced with the unified workflow. It's a **drop-in replacement**:
- ✅ Same API interface (request/response format unchanged)
- ✅ No frontend changes needed
- ✅ Backwards compatible
- ✅ More intelligent (agent-based tool selection)

### Recommended: Monitor After Deploy

1. **Deploy** - Restart backend with new code
2. **Monitor** - Watch backend logs for tool selection
3. **Verify** - Check that agent is making good decisions
4. **Adjust** - Tune prompts if needed

---

## Summary

✅ **What We Built:**
- Intelligent agent that decides which tools to use
- RAG wrapped as tools for agent selection
- Unified workflow combining all capabilities
- New smart chat endpoint
- Comprehensive documentation

✅ **How It's Better:**
- Smarter tool selection (not always RAG)
- Multi-tool support (Gmail, Drive, Calendar)
- More efficient (only uses what's needed)
- More transparent (shows reasoning)
- Extensible (easy to add new tools)

🎯 **Next Steps:**
1. Test the new `/send-smart` endpoint
2. Upload a document and ask questions about it
3. Monitor which tools the agent selects
4. Compare responses with old `/send` endpoint
5. Gradually migrate users to smart endpoint

---

**Questions?** Check `UNIFIED_WORKFLOW_GUIDE.md` for detailed documentation!

🎉 **The unified workflow is ready to use!**

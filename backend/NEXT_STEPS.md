# TurfMapp AI Agent - Next Steps

## Current Status ✅

**Completed:**
- ✅ Local PostgreSQL database setup with pgvector
- ✅ LLM Factory (6 models, 18 tests passing)
- ✅ Conversation Memory Manager (auto-summarization, 23 tests passing)
- ✅ Google Tools as LlamaIndex FunctionTools (9 tools, 11 tests passing)
- ✅ Workflow architecture designed
- ✅ **Total: 52 tests passing (100%)**

---

## Immediate Next Steps (Priority Order)

### 1. **Integrate LlamaIndex Components into Existing Endpoints** 🎯

**Why:** Make the new LlamaIndex components actually usable in your application

**Tasks:**
- [ ] Update chat endpoint to use `ChatWorkflow` (or direct LLM Factory for simpler implementation)
- [ ] Update conversation endpoint to use `ConversationMemory`
- [ ] Create tool execution endpoint using Google Tools
- [ ] Migrate existing database connections to use local PostgreSQL

**Estimated Time:** 2-3 hours

**Code Example:**
```python
# In app/api/routes/chat.py
from app.llamaindex.services.llm_factory import llm_factory, TaskType
from app.llamaindex.memory.conversation_memory import MemoryManager

@router.post("/chat")
async def chat_endpoint(
    request: ChatRequest,
    current_user = Depends(get_current_user),
    db_pool = Depends(get_db_pool)
):
    # Initialize memory manager
    memory_manager = MemoryManager(db_pool=db_pool)
    memory = memory_manager.get_memory(
        user_id=current_user.id,
        conversation_id=request.conversation_id
    )
    await memory.load_from_database()

    # Get LLM
    llm = llm_factory.create_llm(
        model_id=llm_factory.recommend_model_for_task(TaskType.CHAT),
        temperature=0.7
    )

    # Build messages from memory
    messages = []
    history = await memory.get_messages(limit=10)
    for msg in history:
        messages.append(ChatMessage(
            role=MessageRole(msg["role"]),
            content=msg["content"]
        ))

    # Add current message
    messages.append(ChatMessage(
        role=MessageRole.USER,
        content=request.message
    ))

    # Get response
    response = await llm.achat(messages)

    # Save to memory
    await memory.add_message("user", request.message)
    await memory.add_message("assistant", response.message.content)

    return {"response": response.message.content}
```

---

### 2. **Create Google OAuth Integration Endpoint** 🔐

**Why:** Enable users to authenticate with Google so they can use Gmail/Drive/Calendar tools

**Tasks:**
- [ ] Add Google OAuth routes (`/auth/google`, `/auth/google/callback`)
- [ ] Store OAuth credentials securely in database
- [ ] Create middleware to retrieve user credentials
- [ ] Test OAuth flow end-to-end

**Estimated Time:** 2-3 hours

**Files to Create:**
```
app/api/routes/auth.py
app/services/oauth_service.py
app/models/oauth_credentials.py
```

---

### 3. **Build Agent Tool Execution System** 🤖

**Why:** Allow the AI to actually use Gmail, Drive, and Calendar tools

**Tasks:**
- [ ] Create `/agent/execute` endpoint
- [ ] Use LlamaIndex ReActAgent with Google tools
- [ ] Add tool usage tracking and logging
- [ ] Create frontend interface for agent interactions

**Estimated Time:** 3-4 hours

**Code Example:**
```python
from llama_index.core.agent import ReActAgent
from app.llamaindex.tools import create_gmail_tools, create_drive_tools

@router.post("/agent/execute")
async def execute_agent(
    request: AgentRequest,
    credentials = Depends(get_google_credentials)
):
    # Create tools
    tools = (
        create_gmail_tools(credentials) +
        create_drive_tools(credentials) +
        create_calendar_tools(credentials)
    )

    # Create agent
    llm = llm_factory.create_llm(
        model_id=llm_factory.recommend_model_for_task(TaskType.TOOL_USE)
    )
    agent = ReActAgent.from_tools(tools, llm=llm)

    # Execute
    response = await agent.achat(request.message)

    return {"response": str(response)}
```

---

### 4. **Implement RAG (Retrieval-Augmented Generation)** 📚

**Why:** Enable document-based question answering

**Tasks:**
- [ ] Create document ingestion endpoint
- [ ] Implement vector indexing using pgvector
- [ ] Create retrieval system
- [ ] Build RAG query endpoint
- [ ] Add document management UI

**Estimated Time:** 4-6 hours

**Components:**
```python
# app/llamaindex/rag/document_indexer.py
# app/llamaindex/rag/vector_store.py
# app/llamaindex/rag/retriever.py
# app/api/routes/documents.py
```

---

### 5. **Add Streaming Support** 📡

**Why:** Better UX with real-time responses

**Tasks:**
- [ ] Update chat endpoint to support streaming
- [ ] Implement SSE (Server-Sent Events) or WebSocket
- [ ] Update frontend to handle streaming responses
- [ ] Add streaming tests

**Estimated Time:** 2-3 hours

**Code Example:**
```python
from fastapi.responses import StreamingResponse

@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    async def generate():
        llm = llm_factory.create_llm(streaming=True)
        response_stream = await llm.astream_chat(messages)

        async for chunk in response_stream:
            yield f"data: {chunk.delta}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

---

### 6. **Fix Workflow Integration** 🔧

**Why:** Complete the workflow system for orchestrated multi-step operations

**Tasks:**
- [ ] Study LlamaIndex Event base class requirements
- [ ] Refactor workflow events to inherit from proper base
- [ ] Create simplified workflow runner without LlamaIndex's Workflow
- [ ] Or use simpler orchestration pattern

**Estimated Time:** 3-4 hours

**Alternative Approach:**
Instead of LlamaIndex Workflows, you could use a simpler orchestration pattern:

```python
# app/llamaindex/orchestration/simple_workflow.py
class SimpleWorkflow:
    async def run_chat_workflow(self, user_id, message):
        # Step 1: Load memory
        memory = await self.load_memory(user_id)

        # Step 2: Build context
        context = await self.build_context(memory)

        # Step 3: Get LLM response
        response = await self.get_response(context, message)

        # Step 4: Save to memory
        await self.save_memory(memory, message, response)

        return response
```

---

### 7. **Add Monitoring and Analytics** 📊

**Why:** Track usage, costs, and performance

**Tasks:**
- [ ] Add token usage tracking
- [ ] Implement cost monitoring
- [ ] Create admin dashboard for analytics
- [ ] Add performance metrics (latency, error rates)
- [ ] Set up alerts for API quota limits

**Estimated Time:** 3-4 hours

---

### 8. **Write Integration Tests** 🧪

**Why:** Ensure end-to-end functionality works

**Tasks:**
- [ ] Create E2E test for chat flow
- [ ] Create E2E test for agent tool execution
- [ ] Create E2E test for RAG queries
- [ ] Add load testing
- [ ] Set up CI/CD pipeline

**Estimated Time:** 2-3 hours

---

## Recommended Implementation Order

### **Week 1: Core Integration**
1. **Day 1-2**: Integrate LlamaIndex into existing endpoints (#1)
2. **Day 3**: Google OAuth integration (#2)
3. **Day 4-5**: Agent tool execution system (#3)

### **Week 2: Advanced Features**
1. **Day 1-3**: RAG implementation (#4)
2. **Day 4**: Streaming support (#5)
3. **Day 5**: Monitoring setup (#7)

### **Week 3: Polish & Testing**
1. **Day 1-2**: Integration tests (#8)
2. **Day 3**: Workflow fixes if needed (#6)
3. **Day 4-5**: Documentation and deployment prep

---

## Quick Wins (Do First) 🚀

**These can be done in 1-2 hours and provide immediate value:**

1. **Replace existing LLM calls with LLM Factory**
   ```python
   # Old code
   # response = openai.chat.completions.create(...)

   # New code
   llm = llm_factory.create_llm(model_id="gpt-4o")
   response = await llm.acomplete(prompt)
   ```

2. **Add conversation memory to one endpoint**
   - Pick your most-used chat endpoint
   - Add ConversationMemory
   - Test that context is maintained

3. **Create a simple tool demo**
   - Build a `/demo/gmail-search` endpoint
   - Show tool execution working
   - Use for demos/testing

---

## Technology Decisions to Make

### 1. **Workflow Approach**
**Options:**
- **A)** Fix LlamaIndex Workflow integration (complex, but official)
- **B)** Use simple orchestration class (simple, works now)
- **C)** Use LangGraph for workflows (different framework)

**Recommendation:** Start with **B** (simple orchestration), migrate to **A** later if needed

### 2. **Vector Store**
**Options:**
- **A)** pgvector (already installed, simple)
- **B)** Pinecone (managed, scalable)
- **C)** Weaviate (feature-rich)

**Recommendation:** **A** (pgvector) for MVP, consider **B** at scale

### 3. **Streaming**
**Options:**
- **A)** Server-Sent Events (SSE)
- **B)** WebSockets
- **C)** HTTP chunked responses

**Recommendation:** **A** (SSE) - simpler, works with HTTP/2

---

## Migration Strategy

### Phase 1: Parallel Run ✅ (Recommended)
- Keep existing endpoints working
- Add new LlamaIndex endpoints with `/v2/` prefix
- Gradually migrate users
- Compare performance and quality

### Phase 2: Feature Flag
- Use feature flags to toggle between old/new
- Test with subset of users
- Roll back easily if issues

### Phase 3: Full Migration
- Deprecate old endpoints
- Remove old code
- Update documentation

---

## Testing Strategy

```bash
# Run all tests
python -m pytest tests/ -v

# Run only LlamaIndex tests
python -m pytest tests/llamaindex/ -v

# Run integration tests
python -m pytest tests/integration/ -v

# Run with coverage
python -m pytest tests/ --cov=app/llamaindex --cov-report=html
```

---

## Performance Benchmarks to Track

1. **Response Latency**
   - Target: < 2s for chat
   - Target: < 5s for tool execution
   - Target: < 1s for RAG retrieval

2. **Token Usage**
   - Track per user/conversation
   - Set budgets and limits
   - Optimize prompt sizes

3. **Database Performance**
   - Query times < 100ms
   - Vector search < 200ms
   - Connection pool size monitoring

---

## Documentation to Create

1. **API Documentation**
   - OpenAPI/Swagger for all endpoints
   - Usage examples
   - Error codes and handling

2. **Developer Guide**
   - How to add new tools
   - How to add new models
   - How to extend workflows

3. **User Guide**
   - How to connect Google account
   - How to use agent features
   - How to upload documents for RAG

---

## Cost Optimization Tips

1. **Use cheaper models for simple tasks**
   ```python
   # For summarization
   llm = llm_factory.create_llm(model_id="gpt-4o-mini")

   # For complex reasoning
   llm = llm_factory.create_llm(model_id="gpt-4o")
   ```

2. **Implement caching**
   - Cache LLM responses for common queries
   - Cache tool results (e.g., Drive file lists)
   - Use Redis for fast cache access

3. **Set token limits**
   ```python
   llm = llm_factory.create_llm(
       model_id="gpt-4o",
       max_tokens=500  # Limit response size
   )
   ```

4. **Monitor costs**
   ```python
   cost = llm_factory.estimate_cost(
       model_id="gpt-4o",
       input_tokens=1000,
       output_tokens=500
   )
   # Log to analytics
   ```

---

## Questions to Answer

1. **What's the primary use case?**
   - Chat assistant?
   - Document Q&A?
   - Task automation?
   - All of the above?

2. **What's the expected load?**
   - Users per day?
   - Requests per second?
   - Storage requirements?

3. **What's the budget?**
   - LLM API costs?
   - Infrastructure costs?
   - Development time?

4. **What are the privacy requirements?**
   - Data retention policies?
   - User data handling?
   - Compliance needs (GDPR, etc.)?

---

## Get Started Now

**To begin with the most impactful change:**

```bash
# 1. Create a new v2 chat endpoint
touch app/api/routes/chat_v2.py

# 2. Copy this starter code to the file
cat > app/api/routes/chat_v2.py << 'EOF'
from fastapi import APIRouter, Depends, HTTPException
from app.llamaindex.services.llm_factory import llm_factory, TaskType
from app.llamaindex.memory.conversation_memory import MemoryManager
from llama_index.core.llms import ChatMessage, MessageRole

router = APIRouter()

@router.post("/v2/chat")
async def chat_v2(
    message: str,
    conversation_id: str,
    user_id: str = Depends(get_current_user_id),
    db_pool = Depends(get_db_pool)
):
    """New chat endpoint using LlamaIndex."""

    # Get memory
    memory_manager = MemoryManager(db_pool=db_pool)
    memory = memory_manager.get_memory(user_id, conversation_id)
    await memory.load_from_database()

    # Build messages
    messages = []
    for msg in await memory.get_messages(limit=10):
        messages.append(ChatMessage(
            role=MessageRole(msg["role"]),
            content=msg["content"]
        ))
    messages.append(ChatMessage(role=MessageRole.USER, content=message))

    # Get response
    llm = llm_factory.create_llm(
        model_id=llm_factory.recommend_model_for_task(TaskType.CHAT)
    )
    response = await llm.achat(messages)

    # Save to memory
    await memory.add_message("user", message)
    await memory.add_message("assistant", response.message.content)

    return {
        "response": response.message.content,
        "conversation_id": conversation_id
    }
EOF

# 3. Register the router in main.py
# Add to app/main.py:
# from app.api.routes import chat_v2
# app.include_router(chat_v2.router)

# 4. Test it
python -m pytest tests/api/test_chat_v2.py -v
```

---

**Ready to start? Pick one item from the Quick Wins section and let's implement it!**

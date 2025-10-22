# AI Agent with Tool Execution - Usage Guide

## 🎉 What's New

The **AI Agent** endpoint is now live! This bridges your Google OAuth integration with LlamaIndex tools, allowing the AI to:
- 🔍 Search and read Gmail messages
- 📁 Search Google Drive files
- 📅 List calendar events
- 🤖 Use multi-step reasoning to accomplish complex tasks

## Architecture

```
User Request
    ↓
/api/v1/agent/execute
    ↓
Get Google Credentials (from OAuth system)
    ↓
Create LlamaIndex Tools (Gmail, Drive, Calendar)
    ↓
ReActAgent (multi-step reasoning)
    ↓
Execute Tools & Return Results
```

## API Endpoints

### 1. Execute Agent Task
**POST** `/api/v1/agent/execute`

Execute an AI agent with access to Google tools.

**Request:**
```json
{
    "task": "Find unread emails from john@example.com and summarize them",
    "model": "gpt-4o",
    "temperature": 0.7,
    "max_iterations": 10,
    "verbose": true,
    "account_email": "optional@gmail.com"
}
```

**Response:**
```json
{
    "success": true,
    "result": "I found 3 unread emails from john@example.com:\n1. Project Update...\n2. Meeting Request...\n3. Document Review...",
    "reasoning_steps": [...],
    "tools_used": ["search_gmail_messages", "get_gmail_message"],
    "model_used": "gpt-4o",
    "execution_time_ms": 2345.67
}
```

### 2. Get Available Tools
**GET** `/api/v1/agent/available-tools`

List tools available for the current authenticated user.

**Response:**
```json
{
    "google_authenticated": true,
    "total_tools": 6,
    "tools": [
        {
            "name": "search_gmail_messages",
            "description": "Search Gmail messages using Gmail search operators",
            "category": "gmail",
            "enabled": true
        },
        ...
    ],
    "categories": ["gmail", "drive", "calendar"]
}
```

### 3. Health Check
**GET** `/api/v1/agent/health`

Check agent service status.

## Example Use Cases

### 1. Email Management
```json
{
    "task": "Find all unread emails from my boss this week and create a summary"
}
```

### 2. Document Search
```json
{
    "task": "Search my Google Drive for PDF files modified in the last 7 days"
}
```

### 3. Calendar Queries
```json
{
    "task": "What meetings do I have tomorrow and who are the attendees?"
}
```

### 4. Complex Multi-Step Tasks
```json
{
    "task": "Find the email about the Q4 project deadline, then search my Drive for related project files"
}
```

## Available Tools

### Gmail Tools (2)
1. **search_gmail_messages** - Search emails with Gmail operators
   - `is:unread`
   - `from:email@example.com`
   - `subject:keyword`
   - `has:attachment`
   - `after:YYYY/MM/DD`

2. **get_gmail_message** - Get full message details by ID

### Drive Tools (2)
1. **search_drive_files** - Search Drive files and folders
2. **get_drive_file** - Get file details by ID

### Calendar Tools (2)
1. **list_calendar_events** - List upcoming events
2. **get_calendar_event** - Get event details by ID

## Prerequisites

### 1. User Must Connect Google Account
Users need to authenticate with Google OAuth first:

1. **Get Auth URL:**
   ```bash
   GET /api/v1/google/auth/url
   ```

2. **Complete OAuth Flow:**
   - User visits auth URL
   - Grants permissions
   - Callback saves credentials to database

3. **Verify Connection:**
   ```bash
   GET /api/v1/google/auth/status
   ```

### 2. Required Environment Variables
```env
OPENAI_API_KEY=sk-...         # For GPT models
ANTHROPIC_API_KEY=sk-...      # Optional, for Claude models
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=http://localhost:3000/auth/google/callback
```

## Testing

### 1. Check Agent Health
```bash
curl http://localhost:8000/api/v1/agent/health
```

### 2. Check Available Tools (Requires Auth)
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     http://localhost:8000/api/v1/agent/available-tools
```

### 3. Execute Simple Task (Requires Auth + Google OAuth)
```bash
curl -X POST http://localhost:8000/api/v1/agent/execute \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task": "List my recent emails",
    "model": "gpt-4o-mini",
    "verbose": true
  }'
```

## Integration with Frontend

### Step 1: Connect Google Account
```javascript
// Get auth URL
const response = await fetch('/api/v1/google/auth/url', {
  headers: { 'Authorization': `Bearer ${jwt}` }
});
const { auth_url } = await response.json();

// Redirect user to Google OAuth
window.location.href = auth_url;
```

### Step 2: Use Agent
```javascript
// Execute agent task
const response = await fetch('/api/v1/agent/execute', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${jwt}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    task: "Find unread emails from john@company.com",
    model: "gpt-4o",
    verbose: false
  })
});

const result = await response.json();
console.log(result.result);  // Agent's response
console.log(result.tools_used);  // Which tools were used
```

## Error Handling

### 1. User Not Authenticated with Google
**Status:** 401 Unauthorized
```json
{
    "detail": "Google authentication required. Please connect your Google account in Settings."
}
```

**Solution:** User must complete Google OAuth flow first.

### 2. No Tools Available
**Status:** 500 Internal Server Error
```json
{
    "detail": "No tools available. Please check Google API configuration."
}
```

**Solution:** Check environment variables and Google API credentials.

### 3. Agent Execution Failed
**Status:** 500 Internal Server Error
```json
{
    "detail": "Agent execution failed: <error message>"
}
```

**Solution:** Check logs for detailed error. May be due to:
- Invalid OpenAI API key
- Tool execution error
- Rate limiting

## Performance Considerations

### 1. Execution Time
- Simple queries: 1-3 seconds
- Multi-step reasoning: 5-15 seconds
- Complex tasks: 15-30 seconds

### 2. Cost Optimization
- Use `gpt-4o-mini` for simple tasks (cheaper)
- Use `gpt-4o` for complex reasoning
- Set reasonable `max_iterations` (default: 10)

### 3. Rate Limiting
- Google APIs have rate limits
- OpenAI APIs have rate limits
- Implement exponential backoff for retries

## Monitoring

### Key Metrics to Track
1. **Execution Time** - `execution_time_ms` in response
2. **Tools Used** - `tools_used` array
3. **Success Rate** - `success` boolean
4. **Model Costs** - Track by `model_used`

### Logging
All agent executions are logged with:
- User ID
- Task description
- Tools loaded
- Execution result
- Errors (if any)

Check logs:
```bash
docker logs turfmapp-ai-agent-backend-1 | grep "agent"
```

## Next Steps

### Immediate (Already Working ✅)
- ✅ Agent endpoint live
- ✅ Gmail tools integrated
- ✅ Drive tools integrated
- ✅ Calendar tools integrated
- ✅ Google OAuth connected

### Future Enhancements
1. **Streaming Support** - Stream agent reasoning steps in real-time
2. **Tool Usage Analytics** - Track which tools are most used
3. **Custom Tools** - Add more tools (Slack, Notion, etc.)
4. **RAG Integration** - Allow agent to query uploaded documents
5. **Workflow Automation** - Chain multiple agent tasks

## Troubleshooting

### Issue: "Google authentication required"
**Cause:** User hasn't connected Google account
**Fix:** Complete OAuth flow via `/api/v1/google/auth/url`

### Issue: "No tools available"
**Cause:** Google credentials expired or invalid
**Fix:**
1. Check OAuth token expiry
2. Refresh tokens via `/api/v1/google/auth/refresh`
3. Re-authenticate if needed

### Issue: Agent gives incomplete responses
**Cause:** Max iterations reached
**Fix:** Increase `max_iterations` in request (default: 10, max: 20)

### Issue: Slow responses
**Cause:** Complex multi-step reasoning
**Fix:**
1. Use simpler queries
2. Use faster model (`gpt-4o-mini`)
3. Reduce `max_iterations`

## API Documentation

Full interactive API documentation available at:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

Look for the **"agent"** tag to see all agent endpoints.

---

## Summary

✅ **What's Working Now:**
- AI Agent with ReActAgent (multi-step reasoning)
- Google OAuth integration (Gmail, Drive, Calendar)
- 6 tools available (2 per service)
- LlamaIndex integration with LLM Factory
- Conversation Memory from Chat V2

🎯 **Ready to Use:**
1. User authenticates with Google OAuth
2. Frontend calls `/api/v1/agent/execute`
3. Agent uses tools to accomplish task
4. Returns natural language response

🚀 **Try It:**
```bash
# 1. Check health
curl http://localhost:8000/api/v1/agent/health

# 2. Explore in browser
open http://localhost:8000/docs

# 3. Test with authenticated user
# (Requires JWT token and Google OAuth)
```

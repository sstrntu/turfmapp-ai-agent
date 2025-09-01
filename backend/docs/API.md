# API Documentation

## Overview

The TURFMAPP AI Agent backend provides RESTful APIs for chat functionality, authentication, and user management. All endpoints use JSON for request/response bodies and follow OpenAPI 3.0 standards.

## Base URL
- Development: `http://localhost:8000`
- Production: `https://your-domain.com`

## Authentication

All protected endpoints require a valid JWT token in the Authorization header:

```http
Authorization: Bearer <jwt_token>
```

### Authentication Flow
1. Exchange Supabase token for application JWT at `/api/v1/auth/exchange-tokens`
2. Use JWT token for all subsequent API calls
3. Token automatically refreshed by frontend when needed

## Chat API (`/api/v1/chat`)

### Send Chat Message
Send a message to the AI assistant and receive a response.

**Endpoint:** `POST /api/v1/chat/send`

**Authentication:** Required

**Request Body:**
```json
{
  "message": "string (required, min_length=1)",
  "conversation_id": "string (optional)",
  "model": "string (optional, default='gpt-4o')",
  "attachments": "array (optional)",
  "include_reasoning": "boolean (optional, default=false)",
  "developer_instructions": "string (optional)",
  "assistant_context": "string (optional)",
  "text_format": "string (optional, default='text')",
  "text_verbosity": "string (optional, default='medium')",
  "reasoning_effort": "string (optional, default='medium')",
  "reasoning_summary": "string (optional, default='auto')",
  "tools": "array (optional)",
  "tool_choice": "string (optional, default='auto')",
  "store": "boolean (optional, default=true)"
}
```

**Response:**
```json
{
  "conversation_id": "uuid",
  "user_message": {
    "id": "uuid",
    "role": "user",
    "content": "string",
    "created_at": "ISO datetime"
  },
  "assistant_message": {
    "id": "uuid", 
    "role": "assistant",
    "content": "string",
    "created_at": "ISO datetime"
  },
  "reasoning": "string (optional, for O1 models)",
  "sources": [
    {
      "url": "string",
      "site": "string", 
      "favicon": "string",
      "favicon_fallbacks": ["string"],
      "title": "string (optional)",
      "thumbnail": "string (optional)"
    }
  ]
}
```

**Error Responses:**
- `401 Unauthorized`: Missing or invalid authentication token
- `422 Unprocessable Entity`: Invalid request body or missing required fields
- `500 Internal Server Error`: Server error or AI API failure

### Get Conversations List
Retrieve list of conversations for the authenticated user.

**Endpoint:** `GET /api/v1/chat/conversations`

**Authentication:** Required

**Response:**
```json
{
  "conversations": [
    {
      "id": "uuid",
      "title": "string",
      "created_at": "ISO datetime",
      "updated_at": "ISO datetime",
      "message_count": "integer (optional)"
    }
  ]
}
```

### Get Conversation Details
Retrieve messages for a specific conversation.

**Endpoint:** `GET /api/v1/chat/conversations/{conversation_id}`

**Authentication:** Required

**Path Parameters:**
- `conversation_id`: UUID of the conversation

**Response:**
```json
{
  "conversation": {
    "id": "uuid",
    "title": "string"
  },
  "messages": [
    {
      "id": "uuid",
      "role": "user|assistant",
      "content": "string",
      "created_at": "ISO datetime",
      "metadata": {
        "sources": [
          {
            "url": "string",
            "site": "string",
            "favicon": "string"
          }
        ],
        "model": "string",
        "api_response": "object (optional)"
      }
    }
  ]
}
```

**Error Responses:**
- `404 Not Found`: Conversation not found or user doesn't have access
- `401 Unauthorized`: Missing or invalid authentication token
- `500 Internal Server Error`: Server error

### Delete Conversation
Delete a conversation and all its messages.

**Endpoint:** `DELETE /api/v1/chat/conversations/{conversation_id}`

**Authentication:** Required

**Path Parameters:**
- `conversation_id`: UUID of the conversation

**Response:**
```json
{
  "message": "Conversation deleted successfully"
}
```

**Error Responses:**
- `404 Not Found`: Conversation not found or user doesn't have access
- `401 Unauthorized`: Missing or invalid authentication token
- `500 Internal Server Error`: Server error

### Add Message to Conversation
Add a message to an existing conversation.

**Endpoint:** `POST /api/v1/chat/conversations/{conversation_id}/messages`

**Authentication:** Required

**Path Parameters:**
- `conversation_id`: UUID of the conversation

**Request Body:**
```json
{
  "role": "user|assistant",
  "content": "string (required, min_length=1)"
}
```

**Response:**
```json
{
  "message": "Message added successfully"
}
```

### Health Check
Check the health status of the chat service.

**Endpoint:** `GET /api/v1/chat/health`

**Authentication:** Not required

**Response:**
```json
{
  "status": "healthy",
  "service": "chat", 
  "timestamp": "ISO datetime"
}
```

### Get Available Models
Get list of supported AI models.

**Endpoint:** `GET /api/v1/chat/models`

**Authentication:** Not required

**Response:**
```json
{
  "models": [
    {
      "id": "gpt-4o",
      "name": "GPT-4O",
      "description": "Most capable model"
    },
    {
      "id": "gpt-4o-mini", 
      "name": "GPT-4O Mini",
      "description": "Fast and efficient"
    },
    {
      "id": "o1",
      "name": "O1",
      "description": "Advanced reasoning"
    },
    {
      "id": "o1-mini",
      "name": "O1 Mini", 
      "description": "Reasoning optimized"
    },
    {
      "id": "o1-preview",
      "name": "O1 Preview",
      "description": "Latest reasoning model"
    }
  ]
}
```

## Authentication API (`/api/v1/auth`)

### Exchange Tokens
Exchange Supabase authentication token for application JWT.

**Endpoint:** `POST /api/v1/auth/exchange-tokens`

**Authentication:** Not required

**Request Body:**
```json
{
  "access_token": "string (required)"
}
```

**Response:**
```json
{
  "access_token": "string (JWT)",
  "user": {
    "id": "uuid",
    "email": "string",
    "name": "string (optional)"
  }
}
```

**Error Responses:**
- `400 Bad Request`: Missing or invalid access_token
- `401 Unauthorized`: Invalid Supabase token
- `500 Internal Server Error`: Authentication service error

### Get Authenticated User
Get current user information from JWT token.

**Endpoint:** `GET /api/v1/auth/user`

**Authentication:** Required

**Response:**
```json
{
  "id": "uuid",
  "email": "string", 
  "name": "string (optional)",
  "created_at": "ISO datetime (optional)",
  "last_login": "ISO datetime (optional)"
}
```

## Model-Specific Behavior

### GPT-4O & GPT-4O Mini
- **Token Limit**: 1500 tokens
- **API**: OpenAI Responses API
- **Features**: Standard chat, sources extraction
- **Response Time**: 2-10 seconds

### O1 Models (O1, O1-Mini, O1-Preview)
- **Token Limit**: 1500 tokens  
- **API**: OpenAI Responses API
- **Features**: Advanced reasoning, reasoning summary in response
- **Response Time**: 10-30 seconds
- **Special**: `include_reasoning=true` returns reasoning process

### GPT-5-mini
- **Token Limit**: 4000 tokens (increased for web search)
- **API**: OpenAI Responses API
- **Features**: Web search, enhanced reasoning, tool calling
- **Response Time**: 15-45 seconds
- **Special**: Handles incomplete responses gracefully

## Sources Extraction

The system automatically extracts URLs from AI responses and enriches them with metadata:

### Source Object Structure
```json
{
  "url": "https://example.com/page",
  "site": "example.com",
  "favicon": "https://www.google.com/s2/favicons?domain=example.com&sz=64",
  "favicon_fallbacks": [
    "https://favicon.io/favicon/example.com/64",
    "https://t1.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&url=example.com&size=64"
  ],
  "title": "Page Title (optional)",
  "thumbnail": "https://example.com/og-image.jpg (optional)"
}
```

### Source Enhancement Process
1. **URL Extraction**: RegEx pattern finds HTTPS URLs in response content
2. **Deduplication**: Removes duplicate URLs and cleans trailing punctuation
3. **Favicon Generation**: Creates multiple favicon URLs for fallback
4. **Metadata Enrichment**: Fetches page title and Open Graph images (async, timeout protected)
5. **Limit Application**: Maximum 8 sources per response

## Error Handling

### Standard Error Response Format
```json
{
  "detail": "string (error message)",
  "type": "string (optional error type)",
  "code": "integer (optional error code)"
}
```

### Common Error Codes
- `400`: Bad Request - Invalid request format or parameters
- `401`: Unauthorized - Missing, invalid, or expired authentication token  
- `404`: Not Found - Resource doesn't exist or user lacks access
- `422`: Unprocessable Entity - Request validation failed
- `429`: Too Many Requests - Rate limit exceeded (future implementation)
- `500`: Internal Server Error - Server error or external service failure

### Error Handling Best Practices
1. **Always check status codes** before processing response body
2. **Handle network timeouts** gracefully (30-60 second timeouts for AI responses)
3. **Implement retry logic** for 5xx errors with exponential backoff
4. **Display user-friendly messages** instead of raw error details
5. **Log errors** for debugging while protecting sensitive information

## Rate Limiting (Future Implementation)

Planned rate limiting structure:

```
- Chat messages: 60 per hour per user
- Conversation operations: 100 per hour per user  
- Health/model endpoints: 1000 per hour per IP
```

Rate limit headers will be included in responses:
```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1693440000
```

## Webhooks (Future Implementation)

Planned webhook support for:
- Conversation events (created, updated, deleted)
- Message events (sent, received)  
- User events (authenticated, preferences changed)

## SDK Examples

### JavaScript/TypeScript
```javascript
// Initialize client
const client = new TurfmappClient({
  baseUrl: 'http://localhost:8000',
  authToken: 'your-jwt-token'
});

// Send message
const response = await client.chat.send({
  message: 'Hello, what can you help me with?',
  model: 'gpt-4o'
});

console.log(response.assistant_message.content);
console.log(response.sources);

// Load conversation
const conversation = await client.chat.getConversation('conversation-id');
```

### Python
```python
# Initialize client  
from turfmapp import TurfmappClient

client = TurfmappClient(
    base_url='http://localhost:8000',
    auth_token='your-jwt-token'
)

# Send message
response = client.chat.send(
    message='Hello, what can you help me with?',
    model='gpt-4o'
)

print(response['assistant_message']['content'])
print(response['sources'])

# Load conversation
conversation = client.chat.get_conversation('conversation-id')
```

---

**API Version**: v1.0  
**Last Updated**: August 30, 2025  
**OpenAPI Spec**: Available at `/docs` (Swagger UI) and `/redoc` (ReDoc)
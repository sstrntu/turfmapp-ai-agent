# Memory System Architecture

The TurfMapp AI Agent uses a hybrid memory system managed by the `UnifiedWorkflow` (LlamaIndex) and PostgreSQL.

## 1. Conversation Memory (Short-Term)
This is the immediate context window provided to the LLM.

- **Storage**: PostgreSQL (`turfmapp_agent.messages`).
- **Retrieval**: `ConversationService` fetches the recent message history for a given `conversation_id`.
- **Context Window**: The system automatically manages context limits (e.g., sliding window) to fit within the model's token limit (128k for GPT-4o/Claude).

## 2. Long-Term Memory (RAG)
Used for retrieving knowledge from uploaded documents or external data.

- **Storage**: Vector Store (via LlamaIndex).
- **Indexing**: Documents uploaded via the API are parsed and indexed.
- **Retrieval**: The `UnifiedWorkflow` uses a `QueryEngine` to fetch relevant context based on user queries *before* generation.

## 3. Workflow State
During an active request, the `UnifiedWorkflow` maintains:
- `user_msg`: The current input.
- `chat_history`: The loaded conversation history.
- `sources`: Collected citations from tools (Web Search, RAG).
- `tool_outputs`: Results from tool executions (Gmail, Calendar, etc.).

This state is ephemeral for the duration of the request but the final result (message + metadata) is persisted to Postgres.

# Database Schema Documentation

The application uses a PostgreSQL database (hosted on Supabase) with a dedicated schema `turfmapp_agent` to isolate agent data.

## Schema: `turfmapp_agent`

### 1. Users Table (`users`)
Stores user profiles and links to Supabase Auth.
- `id` (UUID, PK): Matches `auth.users.id`.
- `email` (Text): User email.
- `name` (Text): Display name.
- `created_at` (Timestamptz)
- `updated_at` (Timestamptz)

### 2. Conversations Table (`conversations`)
Stores chat threads.
- `id` (UUID, PK)
- `user_id` (UUID, FK -> `users.id`)
- `title` (Text): Auto-generated title (e.g., "J1 League Analysis").
- `model` (Text): Model used (e.g., `gpt-4o`, `claude-3-5-sonnet`).
- `system_prompt` (Text, Nullable)
- `created_at` (Timestamptz)
- `updated_at` (Timestamptz)

### 3. Messages Table (`messages`)
Stores individual chat messages.
- `id` (UUID, PK)
- `conversation_id` (UUID, FK -> `conversations.id`)
- `role` (Text): `user` or `assistant`.
- `content` (Text): The message body.
- `metadata` (JSONB): structured data (citations, sources, tool calls).
    - `sources`: Array of citation objects `{title, url, snippet}`.
    - `tool_calls`: Array of executed tools.
- `created_at` (Timestamptz)

## Indexes
- `idx_conversations_user_id`: Optimize fetching user history.
- `idx_messages_conversation_id`: Optimize fetching chat threads.

## Security (RLS)
Row Level Security is enabled.
- Users can only view/edit their own data (`user_id = auth.uid()`).
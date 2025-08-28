# TURFMAPP Setup Guide

This guide will help you set up TURFMAPP with Supabase database integration and Google OAuth authentication.

## Architecture Overview

TURFMAPP now features:
- **Pure OpenAI Chat Completions** (ChatGPT-like experience)
- **Optional User System Prompts** (like ChatGPT Custom Instructions)
- **Supabase Database** with PostgreSQL + vector support
- **Dedicated Database Schema** (`turfmapp_agent`) for multi-app isolation
- **Google OAuth Authentication** via Supabase Auth
- **Modular Backend Architecture** ready for MCP tools, agents, and API integrations
- **Admin User Management** with role-based access control
- **RAG Document Management** (admin-only)

## Prerequisites

- Node.js 16+ and npm/yarn
- Python 3.8+
- Supabase account
- Google Cloud Console project
- OpenAI API key

## 1. Supabase Setup

### Create Supabase Project

1. Go to [Supabase](https://supabase.com) and create a new project
2. Wait for the database to be ready
3. Note down your project URL and API keys

### Configure Database Schema

1. In your Supabase dashboard, go to the SQL Editor
2. Run the complete schema from `backend/supabase_schema.sql`
3. This will create:
   - A dedicated `turfmapp_agent` schema for isolation
   - All tables, indexes, RLS policies, and triggers
   - Proper separation from other apps in the same Supabase project

**Note**: The schema uses `turfmapp_agent` to separate this app from other applications you might have in the same Supabase project.

### Enable Google OAuth

1. In Supabase dashboard, go to Authentication → Settings
2. Enable Google provider
3. Add your Google OAuth credentials:
   - Client ID and Client Secret from Google Console
   - Set redirect URL to: `https://your-project.supabase.co/auth/v1/callback`

### Configure Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URIs:
   - `https://your-project.supabase.co/auth/v1/callback`
   - `http://localhost:3000/auth-callback.html` (for local development)

## 2. Backend Setup

### Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### Environment Configuration

1. Copy `.env.example` to `.env`
2. Configure your environment variables:

```env
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_DB_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o-mini

# Security
SECRET_KEY=your-random-secret-key

# CORS
BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:8080
```

### Run Backend

```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend will be available at `http://localhost:8000`

## 3. Frontend Setup

### Configure Supabase Client

1. Edit `frontend/public/scripts/supabase-client.js`
2. Update the Supabase configuration:

```javascript
const SUPABASE_CONFIG = {
    url: 'https://your-project.supabase.co',
    anonKey: 'your-supabase-anon-key'
};
```

### Serve Frontend

For local development, you can use any static file server:

```bash
cd frontend/public
python -m http.server 3000
```

Or use a more advanced server like `live-server`:

```bash
npm install -g live-server
cd frontend/public
live-server --port=3000
```

The frontend will be available at `http://localhost:3000`

## 4. First-Time Setup

### Create Super Admin

After setting up the database, you need to create your first super admin user:

1. Sign in through Google OAuth once to create your user record
2. In Supabase dashboard, go to Table Editor → `users`
3. Find your user record and update:
   - `role`: Change to `super_admin`
   - `status`: Change to `active`

### Test the Application

1. Visit `http://localhost:3000/portal.html`
2. Click "Sign in with Google"
3. Complete OAuth flow
4. You should be redirected to the chat interface

## 5. Key Features

### Chat System

- **Pure OpenAI Integration**: Uses standard Chat Completions API (like ChatGPT)
- **System Prompts**: Users can set custom system prompts in their profile
- **Conversation History**: All chats are stored in the database
- **Message Rating**: Users can rate and provide feedback on responses

### User Management

- **Google OAuth**: Seamless authentication
- **Admin Approval**: New users require admin approval
- **Role-Based Access**: User, Admin, Super Admin roles
- **Profile Management**: Users can customize their experience

### Admin Features

- **User Management**: Approve, suspend, promote users
- **Announcements**: System-wide announcements
- **Statistics Dashboard**: User and usage analytics
- **RAG Document Management**: Upload and manage knowledge base documents

## 6. API Endpoints

### Authentication
- `POST /api/v1/auth/exchange` - Exchange Supabase tokens
- `GET /api/v1/auth/me` - Get current user
- `GET /api/v1/auth/status` - Check auth status

### User Management
- `GET /api/v1/users/me` - Get current user profile
- `PUT /api/v1/users/me` - Update profile
- `GET /api/v1/users/me/preferences` - Get user preferences
- `PUT /api/v1/users/me/preferences` - Update system prompt

### Chat
- `POST /api/v1/chat/send` - Send chat message
- `GET /api/v1/chat/conversations` - Get conversation list
- `GET /api/v1/chat/conversations/{id}` - Get conversation with messages

### Admin (Admin+ only)
- `GET /api/v1/admin/stats` - System statistics
- `GET /api/v1/admin/announcements` - Manage announcements
- `GET /api/v1/users/pending` - Users pending approval
- `POST /api/v1/users/users/{id}/approve` - Approve user

## 7. Development vs Production

### Development
- Uses SQLite fallback if Supabase not configured
- Includes dev login button for testing
- CORS allows localhost origins

### Production
- Requires Supabase PostgreSQL
- Remove dev login functionality
- Configure proper CORS origins
- Use production Supabase URLs

## 8. Customization

### Adding System Prompts
Users can set system prompts in their profile that will be applied to all conversations, similar to ChatGPT's Custom Instructions.

### Modular Architecture
The backend is designed for easy extension:
- Add new API tools in `backend/app/tools/`
- Add MCP integrations in `backend/app/integrations/`
- Add AI agents in `backend/app/agents/`

### RAG System
Admins can upload documents that will be processed and stored with vector embeddings for semantic search and retrieval-augmented generation.

## 9. Troubleshooting

### Common Issues

1. **Database Connection Issues**: Check your `SUPABASE_DB_URL` format
2. **Authentication Failures**: Verify Google OAuth configuration
3. **CORS Errors**: Ensure frontend origin is in `BACKEND_CORS_ORIGINS`
4. **OpenAI API Errors**: Check your `OPENAI_API_KEY`

### Logs
- Backend logs: Check FastAPI console output
- Frontend logs: Check browser developer console
- Database logs: Check Supabase dashboard logs

## 10. Next Steps

With the basic setup complete, you can:
- Customize the system prompts feature
- Add more OpenAI models
- Implement RAG document search
- Add MCP tool integrations
- Create custom AI agents
- Build admin analytics dashboard

The modular architecture makes it easy to extend with new features while maintaining the core ChatGPT-like experience.
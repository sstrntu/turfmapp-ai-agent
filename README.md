# 🤖 TurfMapp AI Agent

**A Production-Ready Agentic RAG System**

This repository houses a sophisticated AI agent built with **LlamaIndex Workflows**, **FastAPI**, and **React**. It features a "Unified Workflow" that intelligently routes user queries between RAG (Document Search), External Tools (Google Workspace), and Direct Conversation, all underpinned by a human-in-the-loop (HITL) memory system.

---

## ✨ Key Features

### 🧠 **Agentic RAG & Unified Workflow**
The system doesn't just "chat." It thinks.
- **Smart Routing**: The `UnifiedWorkflow` analyzes your intent.
    - *Asking about a meeting?* → Routes to **Google Calendar Tool**.
    - *Asking about a PDF?* → Routes to **RAG (Vector Store)**.
    - *Just saying hi?* → Responds directly (Zero latency).
- **Multi-Step Reasoning**: Can perform complex tasks like "Find the email from John and summarize the attached PDF."

### 💾 **One-Click Memory System**
- **Personalized Context**: Remembers your role, preferences, and facts across conversations.
- **Privacy-First**: The agent *proposes* facts to remember (e.g., "User lives in Bangkok"). You must explicitly click **"Yes, remember this"** in the UI to save them to the database.
- **Strict Filtering**: Automatically ignores transactional data (emails, search results) to keep memory clean.

### 🔌 **Google Workspace Integration**
- **Gmail**: Read, search, and draft emails.
- **Calendar**: List events, check availability.
- **Drive**: Search and read files directly.
- *Note: Uses a simplified OAuth client (`SimplifiedGoogleMCPClient`) for reliability.*

### 🛠 **Modern Tech Stack**
- **Backend**: Python 3.13, FastAPI, LlamaIndex (Workflows), Supabase (Postgres + pgvector).
- **Frontend**: React 18, Vite, TailwindCSS (via plain CSS utility classes), Streaming UI (Server-Sent Events).
- **LLMs**: Multi-model support (OpenAI GPT-4o, Anthropic Claude 3.5 Sonnet).

---

## 🚀 Quick Start

### Prerequisites
- **Docker & Docker Compose**
- **API Keys**: OpenAI, Supabase, Google OAuth (optional).

### 1. Configure Environment
Copy the example environment file:
```bash
cp .env.local.example .env.local
```
Fill in your keys in `.env.local`:
- `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY`
- `OPENAI_API_KEY`
- `GOOGLE_...` (Client ID/Secret for Tools)

### 2. Run with Docker (Recommended)
This brings up the Backend, Frontend, and ensures all dependencies are linked.
```bash
docker compose up --build
```
- **Frontend**: `http://localhost:3005`
- **Backend API**: `http://localhost:8000`
- **API Docs**: `http://localhost:8000/docs`

---

## 📂 Repository Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/v1/             # Endpoints (Chat V2, Memory, Tools)
│   │   ├── llamaindex/         # Core AI Logic
│   │   │   ├── workflows/      # UnifiedWorkflow engine
│   │   │   ├── memory/         # User & Conversation Memory
│   │   │   └── tools/          # RAG & Google Client tools
│   │   ├── services/           # ChatService, GoogleOAuth
│   │   └── main.py             # App Entrypoint
│   └── tests/                  # Pytest Suite (Unit + Integration)
├── frontend/
│   ├── src/
│   │   ├── components/         # React Components (MemoryConsent, ChatThread)
│   │   └── runtime/            # Chat Adapter & Streaming Logic
│   └── vite.config.js
└── docker-compose.yml
```

---

## 🧪 Testing

We value reliability. The repository includes a comprehensive test suite.

**Run Backend Tests:**
```bash
cd backend
./run_tests.sh
```
*Includes: Unit tests, Integration tests (V2 API), and Tool Execution tests.*

**Frontend Tests:**
```bash
cd frontend
npm run test
```

---

## 📚 Documentation
- **[Memory System Explained](backend/MEMORY_SYSTEM_EXPLAINED.md)**: Deep dive into how user facts are extracted and stored.
- **[Database Schema](backend/SCHEMA_INFO.md)**: Overview of `turfmapp_agent` schema (users, conversations, memory).
- **[Setup Guide](SETUP.md)**: Detailed local development setup (non-Docker).

---

## 🛡️ License
Proprietary / Internal Use Only.

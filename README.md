# TURFMAPP AI Agent

Modern AI assistant that combines a FastAPI backend, a streaming chat workflow, and a React/Vite frontend.  
This repository contains everything needed to run the unified chat agent locally, in Docker, or in CI.

---

## 1. Quick Start

```bash
git clone https://github.com/turfmapp/turfmapp-ai-agent.git
cd turfmapp-ai-agent
```

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.local.example .env.local   # fill in Supabase, OpenAI, Anthropic, Google, etc.
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev -- --port 3005
```
The frontend proxies API calls to `http://localhost:8000`.

### Full Stack with Docker
```bash
docker compose up --build
```
The backend Dockerfile runs a critical pytest suite (regression, health, MCP integration, tool manager) and enforces a minimal coverage threshold during the build.

---

## 2. Repository Layout

```
.
├── backend/
│   ├── app/
│   │   ├── api/v1/        # FastAPI routers (chat, chat_v2, agent, rag, settings…)
│   │   ├── core/          # Config, logging, auth helpers
│   │   ├── services/      # Chat orchestration, tool handlers, MCP clients
│   │   ├── models/        # Pydantic + SQL models
│   │   └── main.py        # FastAPI entrypoint
│   ├── tests/             # Unit, API, regression, integration suites
│   ├── Dockerfile*        # Dev, prod, and CI builds
│   ├── requirements.txt
│   └── README_TESTING.md  # Detailed backend testing doc
├── frontend/
│   ├── src/components/    # React assistant UI (ChatThread, message bubbles, etc.)
│   ├── src/runtime/       # TurfmappChatAdapter + helpers
│   ├── public/            # HTML entrypoints & static assets
│   ├── package.json / vite.config.js
│   └── tests via Vitest   # Lives alongside src files
├── docker-compose.yml
├── code.md                # Project standards & conventions
└── TASK.md                # Current backlog
```

Historical milestone documents were removed; remaining `.md` files describe living architecture or workflow guides.

---

## 3. Backend Highlights

- **Enhanced chat service (`app/services/chat_service.py`)**  
  Streams responses, saves conversation history, orchestrates tool calls, falls back to in-memory storage if Supabase is unavailable.

- **Chat v2 API (`app/api/v1/chat_v2.py`)**  
  Unified workflow with LlamaIndex integration, Google MCP tooling, and SSE streaming.

- **Agent automation (`app/api/v1/agent.py`)**  
  ReAct agent that uses Gmail/Drive/Calendar tools through LlamaIndex.
- **Image generation tool (`generate_image`)**  
  Always calls OpenAI GPT-Image-1 regardless of the selected chat model. Exposed to models via function calling and returns markdown with the generated image.
- **Memory consent workflow**  
  The agent proposes new user facts but only stores them in Supabase after the user approves the detailed “Do you want me to remember…” prompt.

- **RAG endpoints (`app/api/v1/rag.py`)**  
  Document upload + query pipeline backed by PostgreSQL/pgvector.

- **Tool handlers**  
  - `chat_tool_handler.py` / `chat_tool_executor.py` – manage function-call routing  
  - `google_mcp_handler.py` – Gmail/Drive/Calendar logic with AI summarisation  
  - `chat_api_client.py` – OpenAI Responses API wrapper (web search, image gen, tool calls)  
  - `supabase_auth.py` – fetch Supabase user profiles with access tokens  

### Running Tests

```bash
# Unit / service coverage
python -m pytest tests/unit

# API behaviour (v1/v2/agent/rag)
python -m pytest tests/test_api

# Regression guardrails
python -m pytest tests/regression

# Coverage snapshot (resolves SQLAlchemy Base import first)
python -m pytest tests/unit tests/test_api --cov=app --cov-report=term-missing
```

Pytest runs in strict asyncio mode. The Docker build executes a reduced suite with `--cov-fail-under=12`.

---

## 4. Frontend Highlights

- React + Vite + Assistant UI, with tests written in Vitest / React Testing Library.
- Streaming adapter: `src/runtime/TurfmappChatAdapter.js` bridges the UI to `/api/v2/chat/stream`.
- Core chat UI: `src/components/ChatThread.jsx` (attachments, model selector, suggestions).
- Rendering helpers: `AssistantMessage`, `SourcesPanel`, `BlockRenderer` display metadata, reasoning, and tool blocks.

### Frontend Tests
```bash
npm run test        # vitest run --coverage
npm run test:watch
```
Coverage includes adapter helpers (`TurfmappChatAdapter.test.js`, `.run.test.js`) and UI behaviour (`ChatThread.test.jsx`, `AssistantMessage.test.jsx`, etc.).

---

## 5. Configuration & Environment

- **Backend `.env.local`**: Supabase credentials, OpenAI/Anthropic keys, Google OAuth, secret key.
- **Frontend proxy**: configure Vite proxy in `vite.config.js` or set `VITE_BACKEND_URL`.
- **Supabase schema**: see `backend/SCHEMA_INFO.md` for table overview and `supabase_schema.sql` for reference data.

---

## 6. Development Workflow

1. Follow coding standards in `code.md` (type hints, logging, error handling, consistent structure).
2. Update docs (`README_TESTING.md`, `API_DOCUMENTATION.md`, etc.) when workflows change.
3. Before pushing / opening a PR:
   ```bash
   python -m pytest tests/unit tests/test_api
   npm run test
   docker compose build
   ```
4. Keep historical or redundant files trimmed to avoid confusion (the repo has been cleaned accordingly).

---

## 7. Support / Questions

- Architecture overviews: `backend/README_TESTING.md`, `backend/UNIFIED_WORKFLOW_GUIDE.md`, `frontend/USER_GUIDE.md`
- Project standards: `code.md`
- Issue tracking / next steps: `TASK.md`

Happy shipping! 🚀

# Docker Setup for TurfMapp AI Agent Backend

This guide explains how to run the TurfMapp AI Agent backend using Docker with PostgreSQL on port 3005.

## Prerequisites

- Docker Desktop installed and running
- `.env` file with required API keys

## Quick Start

### 1. Ensure .env file exists

Create a `.env` file in the backend directory with your API keys:

```bash
# Required
OPENAI_API_KEY=sk-...

# Optional but recommended
ANTHROPIC_API_KEY=sk-ant-...

# Google OAuth (optional)
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:3005/auth/google/callback

# Security (change in production)
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-here
```

### 2. Start the application

```bash
# Build and start all services
docker-compose up --build

# Or run in detached mode (background)
docker-compose up -d --build
```

This will start:
- **PostgreSQL 17** with pgvector on port 5432
- **Backend API** on port **3005** (mapped from container port 8000)

### 3. Verify it's running

```bash
# Check health
curl http://localhost:3005/healthz

# Check Chat V2 health
curl http://localhost:3005/api/v1/chat/v2/health

# List available models
curl http://localhost:3005/api/v1/chat/v2/models
```

## Services

### Backend API (Port 3005)

- **URL:** http://localhost:3005
- **API Docs:** http://localhost:3005/docs
- **ReDoc:** http://localhost:3005/redoc
- **Container Name:** turfmapp-backend

**Endpoints:**
- `/healthz` - Basic health check
- `/api/v1/chat/send` - V1 chat endpoint
- `/api/v1/chat/v2/send` - V2 chat endpoint (LlamaIndex)
- `/api/v1/chat/v2/models` - List available models
- `/docs` - Interactive API documentation

### PostgreSQL Database (Port 5432)

- **Host:** localhost (from host machine) or `postgres` (from backend container)
- **Port:** 5432
- **Database:** turfmapp_dev
- **User:** turfmapp_agent
- **Password:** Z3c2et-2025
- **Container Name:** turfmapp-postgres

**Features:**
- PostgreSQL 17
- pgvector extension installed
- 8 tables pre-created in `turfmapp_agent` schema
- Vector similarity search indexes
- Persistent data volume

## Common Commands

### Start services
```bash
docker-compose up -d
```

### Stop services
```bash
docker-compose down
```

### Stop and remove volumes (clean slate)
```bash
docker-compose down -v
```

### View logs
```bash
# All services
docker-compose logs -f

# Backend only
docker-compose logs -f backend

# Postgres only
docker-compose logs -f postgres
```

### Restart a service
```bash
# Restart backend
docker-compose restart backend

# Restart postgres
docker-compose restart postgres
```

### Rebuild after code changes
```bash
# Rebuild and restart
docker-compose up -d --build

# Rebuild specific service
docker-compose up -d --build backend
```

### Execute commands in containers
```bash
# Access backend shell
docker-compose exec backend bash

# Access postgres shell
docker-compose exec postgres psql -U turfmapp_agent -d turfmapp_dev

# Run tests in backend
docker-compose exec backend python -m pytest tests/ -v
```

## Database Management

### Connect to PostgreSQL

From host machine:
```bash
psql -h localhost -p 5432 -U turfmapp_agent -d turfmapp_dev
```

From backend container:
```bash
docker-compose exec backend python -c "
from app.database import get_db_pool
import asyncio

async def test_db():
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchval('SELECT 1')
        print(f'Database connected: {result}')

asyncio.run(test_db())
"
```

### View tables
```bash
docker-compose exec postgres psql -U turfmapp_agent -d turfmapp_dev -c "\dt turfmapp_agent.*"
```

### Check pgvector installation
```bash
docker-compose exec postgres psql -U turfmapp_agent -d turfmapp_dev -c "\dx"
```

### Backup database
```bash
docker-compose exec postgres pg_dump -U turfmapp_agent turfmapp_dev > backup.sql
```

### Restore database
```bash
cat backup.sql | docker-compose exec -T postgres psql -U turfmapp_agent -d turfmapp_dev
```

## Testing

### Run all tests
```bash
docker-compose exec backend python -m pytest tests/ -v
```

### Run LlamaIndex tests only
```bash
docker-compose exec backend python -m pytest tests/llamaindex/ -v
```

### Run with coverage
```bash
docker-compose exec backend python -m pytest tests/ --cov=app --cov-report=html
```

### Run Chat V2 endpoint test
```bash
docker-compose exec backend python test_chat_v2_endpoint.py
```

## Development Workflow

The docker-compose.yml is configured for **hot reload** during development:

1. Edit files in `app/` directory
2. Changes are automatically mounted into the container
3. uvicorn detects changes and reloads (because of `--reload` flag)
4. No need to rebuild the container for code changes

**When you need to rebuild:**
- After changing `requirements.txt`
- After changing `Dockerfile`
- After adding new files outside `app/` or `tests/`

## Environment Variables

The docker-compose.yml loads environment variables from your `.env` file:

**Required:**
- `OPENAI_API_KEY` - OpenAI API key for GPT models

**Optional:**
- `ANTHROPIC_API_KEY` - For Claude models
- `GOOGLE_CLIENT_ID` - For Google OAuth
- `GOOGLE_CLIENT_SECRET` - For Google OAuth
- `SECRET_KEY` - For session encryption
- `JWT_SECRET_KEY` - For JWT tokens
- `LOG_LEVEL` - Logging level (default: INFO)

**Database (auto-configured):**
- `DATABASE_URL` - Set automatically to Docker postgres service
- `SUPABASE_DB_URL` - Same as DATABASE_URL for compatibility

## Networking

Docker creates a bridge network called `turfmapp-network`:

- Backend can access Postgres at `postgres:5432`
- Host machine can access Backend at `localhost:3005`
- Host machine can access Postgres at `localhost:5432`

## Volumes

Persistent data is stored in Docker volumes:

```bash
# List volumes
docker volume ls | grep turfmapp

# Inspect volume
docker volume inspect backend_postgres_data

# Remove volume (WARNING: deletes all data)
docker volume rm backend_postgres_data
```

## Troubleshooting

### Port already in use

If port 3005 or 5432 is already in use:

**Option 1:** Stop the conflicting service
```bash
# Find what's using port 3005
lsof -i :3005

# Kill the process
kill -9 <PID>
```

**Option 2:** Change the port in docker-compose.yml
```yaml
services:
  backend:
    ports:
      - "8000:8000"  # Change 3005 to another port
```

### Database connection failed

```bash
# Check if postgres is healthy
docker-compose ps

# View postgres logs
docker-compose logs postgres

# Restart postgres
docker-compose restart postgres
```

### Backend won't start

```bash
# View backend logs
docker-compose logs backend

# Check if all required env vars are set
docker-compose exec backend env | grep -E "(OPENAI|DATABASE)"

# Restart backend
docker-compose restart backend
```

### "No such file or directory" errors

Make sure you're running docker-compose from the `backend/` directory:
```bash
cd /path/to/turfmapp-ai-agent/backend
docker-compose up
```

### Hot reload not working

```bash
# Check if volumes are mounted
docker-compose exec backend ls -la /app/app

# Restart with rebuild
docker-compose down
docker-compose up -d --build
```

## Production Deployment

For production, create a `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.prod
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      # ... other production env vars
    restart: always
    # Remove volume mounts for code
    # Remove --reload flag
```

Then run:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

## Monitoring

### View resource usage
```bash
docker stats turfmapp-backend turfmapp-postgres
```

### Check health status
```bash
# Backend health
docker inspect turfmapp-backend --format='{{.State.Health.Status}}'

# Postgres health
docker inspect turfmapp-postgres --format='{{.State.Health.Status}}'
```

## Clean Up

### Remove everything (start fresh)
```bash
# Stop and remove containers, networks
docker-compose down

# Also remove volumes (WARNING: deletes database)
docker-compose down -v

# Also remove images
docker-compose down -v --rmi all
```

### Remove only containers (keep volumes/data)
```bash
docker-compose down
```

## Next Steps

After starting with Docker:

1. Test the API: `curl http://localhost:3005/healthz`
2. Visit docs: http://localhost:3005/docs
3. Test Chat V2: `curl http://localhost:3005/api/v1/chat/v2/models`
4. Read `TESTING_CHAT_V2.md` for testing the LlamaIndex integration

---

**Questions?** Check the logs with `docker-compose logs -f`

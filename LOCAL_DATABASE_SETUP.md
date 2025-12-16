# Local PostgreSQL Database Setup Guide

This guide will help you set up a local PostgreSQL database for TurfMapp AI Agent development, so you don't need to use your production Supabase database.

---

## Prerequisites

✅ **Already Installed:**
- PostgreSQL 14.19 (Homebrew)
- PostgreSQL is running on port 5432

---

## Quick Setup (Automated)

### Option 1: Run the Setup Script

The easiest way to set up your local database is to run the automated setup script:

```bash
cd /Users/sirasasitorn/Documents/VScode/turfmapp-ai-agent/backend
./scripts/setup_local_db.sh
```

This script will:
1. ✅ Create database `turfmapp_dev`
2. ✅ Enable pgvector extension
3. ✅ Create turfmapp_agent schema
4. ✅ Create all base tables (users, conversations, messages, user_preferences)
5. ✅ Run LlamaIndex migration (document_nodes, embeddings, memory_states, workflow_executions)
6. ✅ Insert test user (sira@turfmapp.com)

---

## Manual Setup (Step by Step)

If you prefer to set up manually or the script doesn't work:

### Step 1: Create Database

```bash
createdb turfmapp_dev
```

### Step 2: Enable pgvector

```bash
psql -d turfmapp_dev -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

If pgvector is not installed:
```bash
brew install pgvector
```

### Step 3: Create Base Schema

```bash
psql -d turfmapp_dev <<EOF
-- Create schema
CREATE SCHEMA IF NOT EXISTS turfmapp_agent;

-- Users table
CREATE TABLE IF NOT EXISTS turfmapp_agent.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Conversations table
CREATE TABLE IF NOT EXISTS turfmapp_agent.conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES turfmapp_agent.users(id) ON DELETE CASCADE,
    title TEXT,
    model VARCHAR(100),
    system_prompt TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Messages table
CREATE TABLE IF NOT EXISTS turfmapp_agent.messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES turfmapp_agent.conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    rating INTEGER,
    feedback TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- User preferences table
CREATE TABLE IF NOT EXISTS turfmapp_agent.user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES turfmapp_agent.users(id) ON DELETE CASCADE,
    default_model VARCHAR(100),
    system_prompt TEXT,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_conversations_user ON turfmapp_agent.conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON turfmapp_agent.messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON turfmapp_agent.messages(created_at);
EOF
```

### Step 4: Run LlamaIndex Migrations

```bash
psql -d turfmapp_dev -f migrations/001_llamaindex_tables.sql
```

### Step 5: Create Test User

```bash
psql -d turfmapp_dev <<EOF
INSERT INTO turfmapp_agent.users (id, email, name)
VALUES (
    'c36d55aa-1704-4fdf-a1e5-55e8fce8656f',
    'sira@turfmapp.com',
    'Sira (Test User)'
)
ON CONFLICT (id) DO NOTHING;
EOF
```

---

## Configuration

### Step 1: Create .env.local

Copy the example environment file:

```bash
cp .env.local.example .env.local
```

### Step 2: Update .env.local

Edit `.env.local` with your settings:

```bash
# Local PostgreSQL
SUPABASE_DB_URL=postgresql://$(whoami)@localhost:5432/turfmapp_dev

# API Keys (use your own)
OPENAI_API_KEY=sk-your-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Google OAuth (use your own)
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# Secret Key (generate with: openssl rand -hex 32)
SECRET_KEY=$(openssl rand -hex 32)
```

### Step 3: Load Environment Variables

Your FastAPI app should automatically load `.env.local` if it exists. If not, you can use:

```bash
export $(cat .env.local | grep -v '^#' | xargs)
```

---

## Verification

### Test Database Connection

```bash
psql -d turfmapp_dev -c "\dt turfmapp_agent.*"
```

You should see:
- users
- conversations
- messages
- user_preferences
- document_nodes (LlamaIndex)
- embeddings (LlamaIndex)
- memory_states (LlamaIndex)
- workflow_executions (LlamaIndex)

### Test from Python

```python
import asyncpg
import asyncio

async def test_connection():
    conn = await asyncpg.connect(
        database='turfmapp_dev',
        user='your_username',
        host='localhost',
        port=5432
    )

    # Check tables
    tables = await conn.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'turfmapp_agent'"
    )

    print("Tables in turfmapp_agent schema:")
    for table in tables:
        print(f"  - {table['tablename']}")

    await conn.close()

asyncio.run(test_connection())
```

### Run Tests

```bash
pytest tests/test_regression_critical_flows.py -v
```

All 22 tests should pass.

---

## Useful Commands

### Connect to Database
```bash
psql -d turfmapp_dev
```

### View Schema
```sql
\dt turfmapp_agent.*
```

### Query Test User
```sql
SELECT * FROM turfmapp_agent.users WHERE email = 'sira@turfmapp.com';
```

### Check Vector Extension
```sql
SELECT * FROM pg_extension WHERE extname = 'vector';
```

### View Conversations
```sql
SELECT * FROM turfmapp_agent.conversations LIMIT 10;
```

### View LlamaIndex Tables
```sql
-- Document nodes
SELECT COUNT(*) FROM turfmapp_agent.document_nodes;

-- Embeddings
SELECT COUNT(*) FROM turfmapp_agent.embeddings;

-- Memory states
SELECT COUNT(*) FROM turfmapp_agent.memory_states;

-- Workflow executions
SELECT COUNT(*) FROM turfmapp_agent.workflow_executions;
```

---

## Troubleshooting

### Issue: "database does not exist"

```bash
createdb turfmapp_dev
```

### Issue: "extension vector does not exist"

```bash
brew install pgvector
psql -d turfmapp_dev -c "CREATE EXTENSION vector;"
```

### Issue: "permission denied for schema"

```bash
psql -d turfmapp_dev -c "GRANT ALL ON SCHEMA turfmapp_agent TO $(whoami);"
```

### Issue: "no password supplied"

PostgreSQL might be configured to require password auth. Update `pg_hba.conf`:

```bash
# Find pg_hba.conf
psql -c "SHOW hba_file;"

# Edit and change to trust for local connections
sudo nano /opt/homebrew/var/postgresql@14/pg_hba.conf

# Change this line:
# local   all             all                                     md5
# To:
local   all             all                                     trust

# Restart PostgreSQL
brew services restart postgresql@14
```

### Issue: Can't connect from Python

Make sure you're using the correct connection string:

```python
DATABASE_URL = "postgresql://username@localhost:5432/turfmapp_dev"
```

---

## Migration from Supabase to Local

If you want to copy data from your Supabase production database to local:

### Export from Supabase

```bash
# Using supabase CLI
supabase db dump -f backup.sql

# Or using pg_dump
pg_dump -h your-supabase-host -U postgres -d postgres > backup.sql
```

### Import to Local

```bash
psql -d turfmapp_dev < backup.sql
```

---

## Cleanup

To start fresh:

```bash
# Drop database
dropdb turfmapp_dev

# Recreate
createdb turfmapp_dev

# Re-run setup
./scripts/setup_local_db.sh
```

---

## Next Steps

Once your local database is set up:

1. ✅ Update `.env.local` with local database URL
2. ✅ Run the backend: `uvicorn app.main:app --reload`
3. ✅ Test API endpoints: `http://localhost:8000/healthz`
4. ✅ Continue with Phase 2 of LlamaIndex migration

---

## Production Database Safety

✅ **Your production Supabase database is safe!**

This local setup ensures:
- No changes to production database
- Independent development environment
- Safe testing of migrations
- Easy rollback if needed

When you're ready to deploy to production:
1. Test migrations thoroughly on local DB
2. Create backup of Supabase database
3. Run migrations on Supabase staging (if available)
4. Run migrations on Supabase production with monitoring

---

**Last Updated**: 2025-01-20
**Database Version**: PostgreSQL 14.19
**Schema Version**: 001 (LlamaIndex migration)

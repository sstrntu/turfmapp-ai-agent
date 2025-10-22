#!/bin/bash
# Local PostgreSQL Database Setup Script for TurfMapp AI Agent
# This script sets up a local development database with pgvector and all required schemas

set -e  # Exit on error

echo "🗄️  Setting up local PostgreSQL database for TurfMapp AI Agent..."

# Configuration
DB_NAME="turfmapp_dev"
DB_USER="${USER}"  # Use current system user
DB_HOST="localhost"
DB_PORT="5432"

# Colors for output
GREEN='\033[0.32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Database Configuration:${NC}"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo "  Host: $DB_HOST"
echo "  Port: $DB_PORT"
echo ""

# Step 1: Create database
echo -e "${BLUE}Step 1: Creating database...${NC}"
createdb $DB_NAME 2>/dev/null || echo "  Database $DB_NAME already exists (skipping)"
echo -e "${GREEN}✅ Database ready${NC}"

# Step 2: Enable pgvector extension
echo -e "${BLUE}Step 2: Enabling pgvector extension...${NC}"
psql -d $DB_NAME -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null || {
    echo "  ⚠️  pgvector not installed. Installing via homebrew..."
    brew install pgvector
    psql -d $DB_NAME -c "CREATE EXTENSION IF NOT EXISTS vector;"
}
echo -e "${GREEN}✅ pgvector enabled${NC}"

# Step 3: Create schema
echo -e "${BLUE}Step 3: Creating turfmapp_agent schema...${NC}"
psql -d $DB_NAME <<EOF
-- Create schema
CREATE SCHEMA IF NOT EXISTS turfmapp_agent;

-- Set search path
SET search_path TO turfmapp_agent, public;

-- Create users table
CREATE TABLE IF NOT EXISTS turfmapp_agent.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create conversations table
CREATE TABLE IF NOT EXISTS turfmapp_agent.conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES turfmapp_agent.users(id) ON DELETE CASCADE,
    title TEXT,
    model VARCHAR(100),
    system_prompt TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create messages table
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

-- Create user_preferences table
CREATE TABLE IF NOT EXISTS turfmapp_agent.user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES turfmapp_agent.users(id) ON DELETE CASCADE,
    default_model VARCHAR(100),
    system_prompt TEXT,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_conversations_user ON turfmapp_agent.conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON turfmapp_agent.messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON turfmapp_agent.messages(created_at);

EOF
echo -e "${GREEN}✅ Base schema created${NC}"

# Step 4: Run LlamaIndex migrations
echo -e "${BLUE}Step 4: Running LlamaIndex migrations...${NC}"
psql -d $DB_NAME -f migrations/001_llamaindex_tables.sql
echo -e "${GREEN}✅ LlamaIndex tables created${NC}"

# Step 5: Insert test user
echo -e "${BLUE}Step 5: Creating test user...${NC}"
psql -d $DB_NAME <<EOF
INSERT INTO turfmapp_agent.users (id, email, name)
VALUES (
    'c36d55aa-1704-4fdf-a1e5-55e8fce8656f',
    'sira@turfmapp.com',
    'Sira (Test User)'
)
ON CONFLICT (id) DO NOTHING;
EOF
echo -e "${GREEN}✅ Test user created${NC}"

# Step 6: Verify setup
echo -e "${BLUE}Step 6: Verifying setup...${NC}"
TABLE_COUNT=$(psql -d $DB_NAME -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'turfmapp_agent';")
echo "  Tables created: $TABLE_COUNT"

echo ""
echo -e "${GREEN}🎉 Local database setup complete!${NC}"
echo ""
echo "Database Details:"
echo "  📍 Connection String: postgresql://$DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"
echo "  🔧 Schema: turfmapp_agent"
echo "  📊 Tables: $TABLE_COUNT"
echo ""
echo "Next steps:"
echo "  1. Update your .env.local file with:"
echo "     SUPABASE_DB_URL=postgresql://$DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"
echo "  2. Test connection: psql -d $DB_NAME"
echo ""

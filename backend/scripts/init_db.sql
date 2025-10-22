-- Initialize TurfMapp Database for Docker
-- This script runs automatically when the PostgreSQL container starts

-- Install pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create schema
CREATE SCHEMA IF NOT EXISTS turfmapp_agent;

-- Grant permissions
GRANT ALL ON SCHEMA turfmapp_agent TO turfmapp_agent;

-- Set search path
ALTER DATABASE turfmapp_dev SET search_path TO turfmapp_agent, public;

-- Create users table
CREATE TABLE IF NOT EXISTS turfmapp_agent.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create conversations table
CREATE TABLE IF NOT EXISTS turfmapp_agent.conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES turfmapp_agent.users(id) ON DELETE CASCADE,
    title VARCHAR(500),
    model VARCHAR(100) DEFAULT 'gpt-4o',
    system_prompt TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create messages table
CREATE TABLE IF NOT EXISTS turfmapp_agent.messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES turfmapp_agent.conversations(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create conversation_memory_state table for LlamaIndex
CREATE TABLE IF NOT EXISTS turfmapp_agent.conversation_memory_state (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES turfmapp_agent.users(id) ON DELETE CASCADE,
    conversation_id UUID NOT NULL,
    summary TEXT,
    entities JSONB DEFAULT '{}',
    message_count INTEGER DEFAULT 0,
    last_summarized_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, conversation_id)
);

-- Create oauth_credentials table for Google OAuth
CREATE TABLE IF NOT EXISTS turfmapp_agent.oauth_credentials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES turfmapp_agent.users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL DEFAULT 'google',
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_expiry TIMESTAMP,
    scope TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, provider)
);

-- Create vector_documents table for RAG (future use)
CREATE TABLE IF NOT EXISTS turfmapp_agent.vector_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES turfmapp_agent.users(id) ON DELETE CASCADE,
    document_name VARCHAR(500) NOT NULL,
    document_type VARCHAR(100),
    content TEXT NOT NULL,
    embedding vector(1536),  -- OpenAI ada-002 embeddings
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create document_chunks table for RAG chunking
CREATE TABLE IF NOT EXISTS turfmapp_agent.document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES turfmapp_agent.vector_documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create agent_executions table for tracking agent tool usage
CREATE TABLE IF NOT EXISTS turfmapp_agent.agent_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES turfmapp_agent.users(id) ON DELETE CASCADE,
    conversation_id UUID,
    query TEXT NOT NULL,
    tools_used JSONB DEFAULT '[]',
    iterations INTEGER DEFAULT 0,
    result TEXT,
    status VARCHAR(50) DEFAULT 'success',
    execution_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON turfmapp_agent.conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON turfmapp_agent.conversations(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON turfmapp_agent.messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON turfmapp_agent.messages(created_at);
CREATE INDEX IF NOT EXISTS idx_memory_user_conv ON turfmapp_agent.conversation_memory_state(user_id, conversation_id);
CREATE INDEX IF NOT EXISTS idx_oauth_user_provider ON turfmapp_agent.oauth_credentials(user_id, provider);

-- Create vector similarity search index (for RAG)
CREATE INDEX IF NOT EXISTS idx_vector_docs_embedding ON turfmapp_agent.vector_documents
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding ON turfmapp_agent.document_chunks
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Grant all permissions on tables to user
GRANT ALL ON ALL TABLES IN SCHEMA turfmapp_agent TO turfmapp_agent;
GRANT ALL ON ALL SEQUENCES IN SCHEMA turfmapp_agent TO turfmapp_agent;

-- Print success message
DO $$
BEGIN
    RAISE NOTICE '✅ TurfMapp database initialized successfully!';
    RAISE NOTICE '📊 Created 8 tables in turfmapp_agent schema';
    RAISE NOTICE '🔌 pgvector extension installed';
    RAISE NOTICE '🔒 Permissions granted to turfmapp_agent user';
END $$;

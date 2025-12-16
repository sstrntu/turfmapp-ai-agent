-- LlamaIndex Migration Script
-- Version: 001
-- Description: Add tables for LlamaIndex integration (RAG, memory, workflows)
-- Created: 2025-01-20

-- Enable pgvector extension if not already enabled
CREATE EXTENSION IF NOT EXISTS vector;

-- Document nodes for RAG
CREATE TABLE IF NOT EXISTS turfmapp_agent.document_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES turfmapp_agent.users(id) ON DELETE CASCADE,
    document_id UUID NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Embeddings storage (with pgvector)
CREATE TABLE IF NOT EXISTS turfmapp_agent.embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id UUID NOT NULL REFERENCES turfmapp_agent.document_nodes(id) ON DELETE CASCADE,
    embedding vector(1536) NOT NULL,  -- OpenAI ada-002 dimension
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create vector similarity index
CREATE INDEX IF NOT EXISTS embeddings_vector_idx
ON turfmapp_agent.embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Memory states for conversation memory
CREATE TABLE IF NOT EXISTS turfmapp_agent.memory_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES turfmapp_agent.users(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES turfmapp_agent.conversations(id) ON DELETE CASCADE,
    memory_type VARCHAR(50) NOT NULL,  -- 'buffer', 'summary', 'entity'
    content JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, conversation_id, memory_type)
);

-- Workflow execution tracking
CREATE TABLE IF NOT EXISTS turfmapp_agent.workflow_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES turfmapp_agent.users(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES turfmapp_agent.conversations(id),
    workflow_type VARCHAR(100) NOT NULL,
    state JSONB NOT NULL,
    status VARCHAR(50) NOT NULL,  -- 'running', 'completed', 'failed'
    error_message TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Enhance conversations table with LlamaIndex fields
ALTER TABLE turfmapp_agent.conversations
ADD COLUMN IF NOT EXISTS memory_snapshot JSONB,
ADD COLUMN IF NOT EXISTS rag_context_ids UUID[],
ADD COLUMN IF NOT EXISTS workflow_state JSONB;

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_document_nodes_user ON turfmapp_agent.document_nodes(user_id);
CREATE INDEX IF NOT EXISTS idx_document_nodes_doc ON turfmapp_agent.document_nodes(document_id);
CREATE INDEX IF NOT EXISTS idx_memory_states_user ON turfmapp_agent.memory_states(user_id);
CREATE INDEX IF NOT EXISTS idx_memory_states_conv ON turfmapp_agent.memory_states(conversation_id);
CREATE INDEX IF NOT EXISTS idx_workflow_executions_user ON turfmapp_agent.workflow_executions(user_id);
CREATE INDEX IF NOT EXISTS idx_workflow_executions_status ON turfmapp_agent.workflow_executions(status);
CREATE INDEX IF NOT EXISTS idx_workflow_executions_conv ON turfmapp_agent.workflow_executions(conversation_id);

-- Comments for documentation
COMMENT ON TABLE turfmapp_agent.document_nodes IS 'Stores document chunks for RAG retrieval';
COMMENT ON TABLE turfmapp_agent.embeddings IS 'Stores vector embeddings for semantic search';
COMMENT ON TABLE turfmapp_agent.memory_states IS 'Stores conversation memory snapshots';
COMMENT ON TABLE turfmapp_agent.workflow_executions IS 'Tracks LlamaIndex workflow executions';

-- Migration complete
SELECT 'LlamaIndex migration 001 completed successfully' AS status;

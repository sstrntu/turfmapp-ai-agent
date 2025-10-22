-- Migration 002: Add missing documents and user_memory tables
-- Created: 2025-10-22

-- Documents table (parent for document_nodes)
CREATE TABLE IF NOT EXISTS turfmapp_agent.documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES turfmapp_agent.users(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    file_type TEXT,
    file_size BIGINT,
    status VARCHAR(50) DEFAULT 'processing',  -- 'processing', 'completed', 'failed'
    document_scope VARCHAR(50) DEFAULT 'personal',  -- 'personal', 'organization'
    metadata JSONB DEFAULT '{}',
    chunk_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User memory table (account-level facts)
CREATE TABLE IF NOT EXISTS turfmapp_agent.user_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES turfmapp_agent.users(id) ON DELETE CASCADE,
    memory_key VARCHAR(255) NOT NULL,
    memory_value TEXT NOT NULL,
    confidence FLOAT DEFAULT 1.0,
    source_conversation_id UUID REFERENCES turfmapp_agent.conversations(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, memory_key)
);

-- Add vector column to document_nodes (if not exists)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'turfmapp_agent'
        AND table_name = 'document_nodes'
        AND column_name = 'embedding'
    ) THEN
        ALTER TABLE turfmapp_agent.document_nodes
        ADD COLUMN embedding vector(1536);
    END IF;
END $$;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_documents_user ON turfmapp_agent.documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON turfmapp_agent.documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_scope ON turfmapp_agent.documents(document_scope);
CREATE INDEX IF NOT EXISTS idx_user_memory_user ON turfmapp_agent.user_memory(user_id);
CREATE INDEX IF NOT EXISTS idx_user_memory_key ON turfmapp_agent.user_memory(memory_key);

-- Create vector similarity index on document_nodes if not exists
CREATE INDEX IF NOT EXISTS document_nodes_embedding_idx
ON turfmapp_agent.document_nodes
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Add foreign key constraint to document_nodes if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'document_nodes_document_id_fkey'
        AND table_schema = 'turfmapp_agent'
    ) THEN
        ALTER TABLE turfmapp_agent.document_nodes
        ADD CONSTRAINT document_nodes_document_id_fkey
        FOREIGN KEY (document_id) REFERENCES turfmapp_agent.documents(id) ON DELETE CASCADE;
    END IF;
END $$;

-- Comments for documentation
COMMENT ON TABLE turfmapp_agent.documents IS 'Document metadata and tracking';
COMMENT ON TABLE turfmapp_agent.user_memory IS 'User account-level memory facts';

SELECT 'Migration 002 completed successfully' AS status;

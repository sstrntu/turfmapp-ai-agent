-- TURFMAPP-AGENT Supabase Database Schema
-- Run this in your Supabase SQL Editor

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- ================================
-- CREATE TURFMAPP-AGENT SCHEMA
-- ================================

-- Create dedicated schema for TURFMAPP-AGENT
CREATE SCHEMA IF NOT EXISTS turfmapp_agent;

-- Grant usage on schema to authenticated users
GRANT USAGE ON SCHEMA turfmapp_agent TO authenticated;
GRANT USAGE ON SCHEMA turfmapp_agent TO anon;

-- Set search path to include turfmapp_agent schema
ALTER DATABASE postgres SET search_path = turfmapp_agent, public;

-- Create custom types in turfmapp_agent schema
CREATE TYPE turfmapp_agent.user_role AS ENUM ('user', 'admin', 'super_admin');
CREATE TYPE turfmapp_agent.user_status AS ENUM ('pending', 'active', 'suspended');
CREATE TYPE turfmapp_agent.message_role AS ENUM ('user', 'assistant', 'system');

-- ================================
-- 1. USERS & AUTHENTICATION
-- ================================

-- Users table (extends Supabase auth.users)
CREATE TABLE turfmapp_agent.users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    name TEXT,
    avatar_url TEXT,
    role turfmapp_agent.user_role DEFAULT 'user',
    status turfmapp_agent.user_status DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login_at TIMESTAMP WITH TIME ZONE
);

-- User preferences (includes system prompt)
CREATE TABLE turfmapp_agent.user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES turfmapp_agent.users(id) ON DELETE CASCADE,
    system_prompt TEXT DEFAULT NULL,
    default_model TEXT DEFAULT 'gpt-4o-mini',
    settings JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id)
);

-- Admin permissions
CREATE TABLE turfmapp_agent.admin_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES turfmapp_agent.users(id) ON DELETE CASCADE,
    permission TEXT NOT NULL,
    granted_by UUID REFERENCES turfmapp_agent.users(id),
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, permission)
);

-- ================================
-- 2. CHAT SYSTEM
-- ================================

-- Conversations
CREATE TABLE turfmapp_agent.conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES turfmapp_agent.users(id) ON DELETE CASCADE,
    title TEXT,
    model TEXT NOT NULL DEFAULT 'gpt-4o-mini',
    system_prompt TEXT DEFAULT NULL, -- Snapshot of user's system prompt at conversation start
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Messages with feedback
CREATE TABLE turfmapp_agent.messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES turfmapp_agent.conversations(id) ON DELETE CASCADE,
    role turfmapp_agent.message_role NOT NULL,
    content TEXT NOT NULL,
    message_metadata JSONB DEFAULT '{}'::jsonb, -- attachments, sources, etc.
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    feedback TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ================================
-- 3. FILE MANAGEMENT
-- ================================

-- File uploads
CREATE TABLE turfmapp_agent.uploads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES turfmapp_agent.users(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_size BIGINT NOT NULL,
    storage_path TEXT NOT NULL,
    url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ================================
-- 4. RAG SYSTEM (Admin-Only)
-- ================================

-- Document collections (admin-only)
CREATE TABLE turfmapp_agent.document_collections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_by UUID NOT NULL REFERENCES turfmapp_agent.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Documents with embeddings
CREATE TABLE turfmapp_agent.documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collection_id UUID NOT NULL REFERENCES turfmapp_agent.document_collections(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    source_url TEXT,
    embedding vector(1536), -- OpenAI embedding dimension
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Vector search index
CREATE INDEX ON turfmapp_agent.documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ================================
-- 5. SYSTEM CONFIGURATION
-- ================================

-- Announcements
CREATE TABLE turfmapp_agent.announcements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_by UUID NOT NULL REFERENCES turfmapp_agent.users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE
);

-- ================================
-- 6. INDEXES FOR PERFORMANCE
-- ================================

-- User lookups
CREATE INDEX idx_users_email ON turfmapp_agent.users(email);
CREATE INDEX idx_users_status ON turfmapp_agent.users(status);
CREATE INDEX idx_users_role ON turfmapp_agent.users(role);

-- Conversation lookups
CREATE INDEX idx_conversations_user_id ON turfmapp_agent.conversations(user_id);
CREATE INDEX idx_conversations_created_at ON turfmapp_agent.conversations(created_at DESC);

-- Message lookups
CREATE INDEX idx_messages_conversation_id ON turfmapp_agent.messages(conversation_id);
CREATE INDEX idx_messages_created_at ON turfmapp_agent.messages(created_at DESC);
CREATE INDEX idx_messages_role ON turfmapp_agent.messages(role);

-- File uploads
CREATE INDEX idx_uploads_user_id ON turfmapp_agent.uploads(user_id);
CREATE INDEX idx_uploads_created_at ON turfmapp_agent.uploads(created_at DESC);

-- ================================
-- 7. ROW LEVEL SECURITY POLICIES
-- ================================

-- Enable RLS on all tables
ALTER TABLE turfmapp_agent.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE turfmapp_agent.user_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE turfmapp_agent.admin_permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE turfmapp_agent.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE turfmapp_agent.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE turfmapp_agent.uploads ENABLE ROW LEVEL SECURITY;
ALTER TABLE turfmapp_agent.document_collections ENABLE ROW LEVEL SECURITY;
ALTER TABLE turfmapp_agent.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE turfmapp_agent.announcements ENABLE ROW LEVEL SECURITY;

-- Users policies
CREATE POLICY "Users can view own profile" ON turfmapp_agent.users
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON turfmapp_agent.users
    FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Admins can view all users" ON turfmapp_agent.users
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM turfmapp_agent.users 
            WHERE id = auth.uid() AND role IN ('admin', 'super_admin')
        )
    );

-- User preferences policies
CREATE POLICY "Users can manage own preferences" ON turfmapp_agent.user_preferences
    FOR ALL USING (auth.uid() = user_id);

-- Conversations policies
CREATE POLICY "Users can manage own conversations" ON turfmapp_agent.conversations
    FOR ALL USING (auth.uid() = user_id);

-- Messages policies
CREATE POLICY "Users can access messages in own conversations" ON turfmapp_agent.messages
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM turfmapp_agent.conversations 
            WHERE id = conversation_id AND user_id = auth.uid()
        )
    );

-- Upload policies
CREATE POLICY "Users can manage own uploads" ON turfmapp_agent.uploads
    FOR ALL USING (auth.uid() = user_id);

-- RAG system policies (admin-only)
CREATE POLICY "Admins can manage document collections" ON turfmapp_agent.document_collections
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM turfmapp_agent.users 
            WHERE id = auth.uid() AND role IN ('admin', 'super_admin')
        )
    );

CREATE POLICY "Admins can manage documents" ON turfmapp_agent.documents
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM turfmapp_agent.users 
            WHERE id = auth.uid() AND role IN ('admin', 'super_admin')
        )
    );

-- Announcements policies
CREATE POLICY "Everyone can view active announcements" ON turfmapp_agent.announcements
    FOR SELECT USING (is_active = TRUE);

CREATE POLICY "Admins can manage announcements" ON turfmapp_agent.announcements
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM turfmapp_agent.users 
            WHERE id = auth.uid() AND role IN ('admin', 'super_admin')
        )
    );

-- ================================
-- 8. TRIGGERS FOR UPDATED_AT
-- ================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add triggers to tables with updated_at columns
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON turfmapp_agent.users 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_preferences_updated_at BEFORE UPDATE ON turfmapp_agent.user_preferences 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON turfmapp_agent.conversations 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ================================
-- 9. FUNCTIONS FOR USER MANAGEMENT
-- ================================

-- Function to create user profile on signup
CREATE OR REPLACE FUNCTION turfmapp_agent.handle_new_user() 
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO turfmapp_agent.users (id, email, name, avatar_url)
  VALUES (
    NEW.id, 
    NEW.email, 
    NEW.raw_user_meta_data->>'full_name',
    NEW.raw_user_meta_data->>'avatar_url'
  );
  
  -- Create default user preferences
  INSERT INTO turfmapp_agent.user_preferences (user_id)
  VALUES (NEW.id);
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to create user profile on signup
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION turfmapp_agent.handle_new_user();

-- Function to update last_login_at
CREATE OR REPLACE FUNCTION turfmapp_agent.update_last_login()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE turfmapp_agent.users 
  SET last_login_at = NOW() 
  WHERE id = NEW.id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to update last login time
CREATE TRIGGER on_auth_user_login
  AFTER UPDATE OF last_sign_in_at ON auth.users
  FOR EACH ROW EXECUTE FUNCTION turfmapp_agent.update_last_login();
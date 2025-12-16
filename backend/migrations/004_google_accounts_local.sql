-- Migration: Create Google OAuth accounts and tokens tables for LOCAL PostgreSQL
-- This stores user's connected Google accounts and their OAuth tokens
-- Compatible with turfmapp_agent schema (not Supabase)

-- Table to store Google accounts for each user
CREATE TABLE IF NOT EXISTS turfmapp_agent.google_accounts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES turfmapp_agent.users(id) ON DELETE CASCADE,
    email VARCHAR NOT NULL,
    name VARCHAR,
    picture TEXT,
    nickname VARCHAR, -- User-defined label like "Work", "Personal"
    is_primary BOOLEAN DEFAULT FALSE,
    connected_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Ensure one user can't have duplicate accounts
    UNIQUE(user_id, email)
);

-- Table to store OAuth tokens for Google accounts
CREATE TABLE IF NOT EXISTS turfmapp_agent.google_tokens (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    account_id UUID NOT NULL REFERENCES turfmapp_agent.google_accounts(id) ON DELETE CASCADE,
    -- Encrypted token storage (recommended)
    access_token_encrypted TEXT,
    refresh_token_encrypted TEXT,
    -- Plaintext columns (for development - encrypt in production!)
    access_token TEXT,
    refresh_token TEXT,
    -- Token metadata
    expires_at TIMESTAMPTZ,
    token_type VARCHAR DEFAULT 'Bearer',
    scope TEXT, -- Store granted scopes
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_google_accounts_user_id ON turfmapp_agent.google_accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_google_accounts_email ON turfmapp_agent.google_accounts(email);
CREATE INDEX IF NOT EXISTS idx_google_accounts_primary ON turfmapp_agent.google_accounts(user_id, is_primary) WHERE is_primary = TRUE;
CREATE INDEX IF NOT EXISTS idx_google_tokens_account_id ON turfmapp_agent.google_tokens(account_id);
CREATE INDEX IF NOT EXISTS idx_google_tokens_expires_at ON turfmapp_agent.google_tokens(expires_at);

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION turfmapp_agent.update_google_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers to update updated_at
DROP TRIGGER IF EXISTS update_google_accounts_updated_at ON turfmapp_agent.google_accounts;
CREATE TRIGGER update_google_accounts_updated_at
    BEFORE UPDATE ON turfmapp_agent.google_accounts
    FOR EACH ROW EXECUTE FUNCTION turfmapp_agent.update_google_updated_at();

DROP TRIGGER IF EXISTS update_google_tokens_updated_at ON turfmapp_agent.google_tokens;
CREATE TRIGGER update_google_tokens_updated_at
    BEFORE UPDATE ON turfmapp_agent.google_tokens
    FOR EACH ROW EXECUTE FUNCTION turfmapp_agent.update_google_updated_at();

-- Function to ensure only one primary account per user
CREATE OR REPLACE FUNCTION turfmapp_agent.ensure_single_primary_google_account()
RETURNS TRIGGER AS $$
BEGIN
    -- If setting an account as primary, unset all other primary accounts for this user
    IF NEW.is_primary = TRUE THEN
        UPDATE turfmapp_agent.google_accounts
        SET is_primary = FALSE
        WHERE user_id = NEW.user_id
          AND id != NEW.id
          AND is_primary = TRUE;
    END IF;

    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to ensure only one primary account
DROP TRIGGER IF EXISTS ensure_single_primary_google_account ON turfmapp_agent.google_accounts;
CREATE TRIGGER ensure_single_primary_google_account
    BEFORE INSERT OR UPDATE ON turfmapp_agent.google_accounts
    FOR EACH ROW EXECUTE FUNCTION turfmapp_agent.ensure_single_primary_google_account();

-- Grant permissions (for local PostgreSQL user)
GRANT ALL ON turfmapp_agent.google_accounts TO sirasasitorn;
GRANT ALL ON turfmapp_agent.google_tokens TO sirasasitorn;

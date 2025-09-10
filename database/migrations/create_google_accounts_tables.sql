-- Migration: Create Google OAuth accounts and tokens tables
-- This stores user's connected Google accounts and their OAuth tokens

-- Table to store Google accounts for each user
CREATE TABLE google_accounts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
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
CREATE TABLE google_tokens (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    account_id UUID NOT NULL REFERENCES google_accounts(id) ON DELETE CASCADE,
    -- Encrypted token storage (recommended)
    access_token_encrypted TEXT NOT NULL,
    refresh_token_encrypted TEXT,
    -- Legacy plaintext columns (for migration/fallback - can be removed later)
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
CREATE INDEX idx_google_accounts_user_id ON google_accounts(user_id);
CREATE INDEX idx_google_accounts_email ON google_accounts(email);
CREATE INDEX idx_google_accounts_primary ON google_accounts(user_id, is_primary) WHERE is_primary = TRUE;
CREATE INDEX idx_google_tokens_account_id ON google_tokens(account_id);
CREATE INDEX idx_google_tokens_expires_at ON google_tokens(expires_at);

-- Row Level Security (RLS) policies
ALTER TABLE google_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE google_tokens ENABLE ROW LEVEL SECURITY;

-- Users can only access their own Google accounts
CREATE POLICY "Users can view their own Google accounts" 
    ON google_accounts FOR SELECT 
    USING (user_id = auth.uid());

CREATE POLICY "Users can insert their own Google accounts" 
    ON google_accounts FOR INSERT 
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can update their own Google accounts" 
    ON google_accounts FOR UPDATE 
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can delete their own Google accounts" 
    ON google_accounts FOR DELETE 
    USING (user_id = auth.uid());

-- Users can only access tokens for their own Google accounts
CREATE POLICY "Users can view tokens for their own accounts" 
    ON google_tokens FOR SELECT 
    USING (account_id IN (
        SELECT id FROM google_accounts WHERE user_id = auth.uid()
    ));

CREATE POLICY "Users can insert tokens for their own accounts" 
    ON google_tokens FOR INSERT 
    WITH CHECK (account_id IN (
        SELECT id FROM google_accounts WHERE user_id = auth.uid()
    ));

CREATE POLICY "Users can update tokens for their own accounts" 
    ON google_tokens FOR UPDATE 
    USING (account_id IN (
        SELECT id FROM google_accounts WHERE user_id = auth.uid()
    ))
    WITH CHECK (account_id IN (
        SELECT id FROM google_accounts WHERE user_id = auth.uid()
    ));

CREATE POLICY "Users can delete tokens for their own accounts" 
    ON google_tokens FOR DELETE 
    USING (account_id IN (
        SELECT id FROM google_accounts WHERE user_id = auth.uid()
    ));

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers to update updated_at
CREATE TRIGGER update_google_accounts_updated_at 
    BEFORE UPDATE ON google_accounts 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_google_tokens_updated_at 
    BEFORE UPDATE ON google_tokens 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to ensure only one primary account per user
CREATE OR REPLACE FUNCTION ensure_single_primary_account()
RETURNS TRIGGER AS $$
BEGIN
    -- If setting an account as primary, unset all other primary accounts for this user
    IF NEW.is_primary = TRUE THEN
        UPDATE google_accounts 
        SET is_primary = FALSE 
        WHERE user_id = NEW.user_id 
          AND id != NEW.id 
          AND is_primary = TRUE;
    END IF;
    
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to ensure only one primary account
CREATE TRIGGER ensure_single_primary_google_account
    BEFORE INSERT OR UPDATE ON google_accounts
    FOR EACH ROW EXECUTE FUNCTION ensure_single_primary_account();

-- Grant necessary permissions
GRANT ALL ON google_accounts TO authenticated;
GRANT ALL ON google_tokens TO authenticated;
GRANT USAGE ON SCHEMA public TO authenticated;
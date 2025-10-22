-- Migration 003: Fix users table - add missing columns
-- Created: 2025-10-22

-- Create custom types if they don't exist
DO $$ BEGIN
    CREATE TYPE turfmapp_agent.user_role AS ENUM ('user', 'admin', 'super_admin');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE turfmapp_agent.user_status AS ENUM ('pending', 'active', 'suspended');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Add missing columns to users table
ALTER TABLE turfmapp_agent.users
ADD COLUMN IF NOT EXISTS avatar_url TEXT,
ADD COLUMN IF NOT EXISTS role turfmapp_agent.user_role DEFAULT 'user',
ADD COLUMN IF NOT EXISTS status turfmapp_agent.user_status DEFAULT 'active',
ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ;

-- Create indexes for the new columns
CREATE INDEX IF NOT EXISTS idx_users_role ON turfmapp_agent.users(role);
CREATE INDEX IF NOT EXISTS idx_users_status ON turfmapp_agent.users(status);

-- Update existing users to have 'active' status if NULL
UPDATE turfmapp_agent.users
SET status = 'active'
WHERE status IS NULL;

SELECT 'Migration 003 completed successfully' AS status;

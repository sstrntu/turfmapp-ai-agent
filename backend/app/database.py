from __future__ import annotations

import os
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
import asyncpg
import ssl
import asyncio

# Database configuration
def _ensure_sslmode(url: str) -> str:
    """Append sslmode=require to the connection string if missing."""
    if not url:
        return url
    lower = url.lower()
    if 'sslmode=' in lower:
        return url
    separator = '&' if '?' in url else '?'
    return f"{url}{separator}sslmode=require"


# Database configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")

# Database URL setup
DATABASE_URL = os.getenv("DATABASE_URL") or SUPABASE_DB_URL
if DATABASE_URL:
    DATABASE_URL = _ensure_sslmode(DATABASE_URL)

print(f"Supabase URL: {SUPABASE_URL}")
print(f"Service role key present: {bool(SUPABASE_SERVICE_ROLE_KEY)}")
print(f"Database URL present: {bool(SUPABASE_DB_URL)}")


def get_supabase_config():
    """Get Supabase configuration"""
    return {
        "url": SUPABASE_URL,
        "service_role_key": SUPABASE_SERVICE_ROLE_KEY,
        "db_url": _ensure_sslmode(SUPABASE_DB_URL)
    }

# PostgreSQL connection pool
_connection_pool = None

async def get_db_pool():
    """Get or create PostgreSQL connection pool"""
    global _connection_pool
    if _connection_pool is None:
        if not SUPABASE_DB_URL:
            raise RuntimeError("SUPABASE_DB_URL environment variable is required")
            
        try:
            db_url = _ensure_sslmode(SUPABASE_DB_URL)
            print(f"Attempting to connect to: {db_url}")
            # Ensure SSL is used for Supabase connections
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            _connection_pool = await asyncpg.create_pool(
                db_url,
                min_size=1,
                max_size=10,
                ssl=ssl_context,
                server_settings={
                    'search_path': 'public'  # Start with public schema for now
                }
            )
            print("✅ PostgreSQL connection pool created successfully!")
            
            # Test the connection
            async with _connection_pool.acquire() as connection:
                await connection.fetchval('SELECT 1')
                print("✅ Database connection test successful!")
                
        except Exception as e:
            print(f"❌ Failed to create PostgreSQL connection pool: {e}")
            raise RuntimeError(f"Failed to connect to Supabase database: {e}")
    return _connection_pool

async def execute_query(query: str, *args):
    """Execute a query with the connection pool"""
    pool = await get_db_pool()
    async with pool.acquire() as connection:
        return await connection.fetch(query, *args)

async def execute_query_one(query: str, *args):
    """Execute a query and return one row"""
    pool = await get_db_pool()
    async with pool.acquire() as connection:
        return await connection.fetchrow(query, *args)

class UserService:
    """Service for managing users in PostgreSQL"""
    
    @staticmethod
    async def create_or_get_user(user_id: str, email: str = None, name: str = None) -> Dict[str, Any]:
        """Create a new user or get existing user"""
        try:
            # First try to get existing user from turfmapp_agent.users
            query = "SELECT * FROM turfmapp_agent.users WHERE id = $1"
            result = await execute_query_one(query, user_id)
            
            if result:
                return dict(result)
            
            # Check if user exists in auth.users (required for foreign key)
            auth_query = "SELECT id, email FROM auth.users WHERE id = $1"
            auth_user = await execute_query_one(auth_query, user_id)
            
            if not auth_user:
                # User doesn't exist in auth.users, we can't create profile
                print(f"User {user_id} not found in auth.users - user must authenticate first")
                return None
            
            # Create user profile using auth user data
            auth_email = auth_user["email"] if auth_user["email"] else email
            query = """
                INSERT INTO turfmapp_agent.users (id, email, name, created_at, updated_at)
                VALUES ($1, $2, $3, NOW(), NOW())
                RETURNING id, email, name, created_at, updated_at
            """
            result = await execute_query_one(query, user_id, auth_email, name)
            return dict(result) if result else None
        except Exception as e:
            print(f"Error creating/getting user: {e}")
            return None
    
    @staticmethod
    async def get_user(user_id: str) -> Optional[Dict[str, Any]]:
        """Get a user by ID"""
        try:
            query = "SELECT * FROM turfmapp_agent.users WHERE id = $1"
            result = await execute_query_one(query, user_id)
            return dict(result) if result else None
        except Exception as e:
            print(f"Error getting user: {e}")
            return None

class ConversationService:
    """Service for managing conversations and messages in PostgreSQL"""
    
    @staticmethod
    async def create_conversation(user_id: str, title: str = None, model: str = "gpt-4o", system_prompt: str = None) -> Dict[str, Any]:
        """Create a new conversation"""
        try:
            # Ensure user exists before creating conversation
            user = await UserService.create_or_get_user(user_id)
            if not user:
                print(f"Failed to create/get user {user_id}")
                return None
            
            conversation_id = str(uuid.uuid4())
            query = """
                INSERT INTO turfmapp_agent.conversations (id, user_id, title, model, system_prompt, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
                RETURNING id, user_id, title, model, system_prompt, created_at, updated_at
            """
            result = await execute_query_one(
                query, 
                conversation_id, 
                user_id, 
                title or "New Conversation", 
                model, 
                system_prompt
            )
            return dict(result) if result else None
        except Exception as e:
            print(f"Error creating conversation: {e}")
            return None
    
    @staticmethod
    async def get_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get a conversation by ID"""
        try:
            query = "SELECT * FROM turfmapp_agent.conversations WHERE id = $1"
            result = await execute_query_one(query, conversation_id)
            return dict(result) if result else None
        except Exception as e:
            print(f"Error getting conversation: {e}")
            return None
    
    @staticmethod
    async def get_user_conversations(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user's recent conversations"""
        try:
            query = """
                SELECT * FROM turfmapp_agent.conversations 
                WHERE user_id = $1 
                ORDER BY updated_at DESC 
                LIMIT $2
            """
            results = await execute_query(query, user_id, limit)
            return [dict(row) for row in results] if results else []
        except Exception as e:
            print(f"Error getting user conversations: {e}")
            return []
    
    @staticmethod
    async def update_conversation_title(conversation_id: str, title: str) -> bool:
        """Update conversation title"""
        try:
            query = """
                UPDATE turfmapp_agent.conversations 
                SET title = $1, updated_at = NOW() 
                WHERE id = $2
            """
            pool = await get_db_pool()
            async with pool.acquire() as connection:
                await connection.execute(query, title, conversation_id)
            return True
        except Exception as e:
            print(f"Error updating conversation title: {e}")
            return False
    
    @staticmethod
    async def add_message(conversation_id: str, role: str, content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Add a message to a conversation"""
        try:
            import json
            message_id = str(uuid.uuid4())
            query = """
                INSERT INTO turfmapp_agent.messages (id, conversation_id, role, content, metadata, created_at)
                VALUES ($1, $2, $3, $4, $5, NOW())
                RETURNING id, conversation_id, role, content, metadata, created_at
            """
            result = await execute_query_one(
                query, 
                message_id, 
                conversation_id, 
                role, 
                content, 
                json.dumps(metadata or {})
            )
            
            if result:
                # Update conversation's updated_at timestamp
                update_query = "UPDATE turfmapp_agent.conversations SET updated_at = NOW() WHERE id = $1"
                pool = await get_db_pool()
                async with pool.acquire() as connection:
                    await connection.execute(update_query, conversation_id)
                return dict(result)
            return None
        except Exception as e:
            print(f"Error adding message: {e}")
            return None
    
    @staticmethod
    async def get_conversation_messages(conversation_id: str) -> List[Dict[str, Any]]:
        """Get all messages in a conversation"""
        try:
            query = """
                SELECT * FROM turfmapp_agent.messages 
                WHERE conversation_id = $1 
                ORDER BY created_at ASC
            """
            results = await execute_query(query, conversation_id)
            return [dict(row) for row in results] if results else []
        except Exception as e:
            print(f"Error getting conversation messages: {e}")
            return []
    
    @staticmethod
    async def delete_conversation(conversation_id: str) -> bool:
        """Delete a conversation and all its messages"""
        try:
            # Delete conversation (messages will be deleted automatically due to CASCADE)
            query = "DELETE FROM turfmapp_agent.conversations WHERE id = $1"
            pool = await get_db_pool()
            async with pool.acquire() as connection:
                await connection.execute(query, conversation_id)
            return True
        except Exception as e:
            print(f"Error deleting conversation: {e}")
            return False
    
    @staticmethod
    def generate_conversation_title(first_message: str) -> str:
        """Generate a title from the first message"""
        # Take first 50 characters and add ellipsis if longer
        title = first_message.strip()[:50]
        if len(first_message) > 50:
            title += "..."
        return title



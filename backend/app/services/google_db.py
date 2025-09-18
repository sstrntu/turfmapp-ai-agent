"""
Google Accounts Database Service

Handles database operations for Google OAuth accounts and tokens.
Replaces in-memory storage with persistent Supabase storage.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import asyncpg
import logging

from ..core.config import get_settings
from .google_oauth import GoogleTokens, GoogleAccount
from .encryption import encryption_service

logger = logging.getLogger(__name__)
settings = get_settings()


class GoogleAccountsDB:
    """Database service for managing Google accounts and tokens."""
    
    def __init__(self):
        self.connection_string = settings.database_url
        
    async def get_connection(self):
        """Get database connection."""
        return await asyncpg.connect(self.connection_string)
    
    async def save_google_account(
        self, 
        user_id: str, 
        account_data: GoogleAccount
    ) -> str:
        """Save or update a Google account and its tokens."""
        conn = await self.get_connection()
        try:
            async with conn.transaction():
                # Insert or update the Google account
                account_id = await conn.fetchval("""
                    INSERT INTO google_accounts (
                        user_id, email, name, picture, nickname, is_primary, connected_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (user_id, email) 
                    DO UPDATE SET 
                        name = EXCLUDED.name,
                        picture = EXCLUDED.picture,
                        nickname = COALESCE(EXCLUDED.nickname, google_accounts.nickname),
                        is_primary = EXCLUDED.is_primary,
                        updated_at = NOW()
                    RETURNING id
                """, 
                user_id, 
                account_data.email, 
                account_data.name,
                account_data.picture,
                account_data.nickname,
                account_data.is_primary,
                datetime.fromtimestamp(account_data.connected_at, tz=timezone.utc)
                )
                
                # Delete existing tokens for this account
                await conn.execute("""
                    DELETE FROM google_tokens WHERE account_id = $1
                """, account_id)
                
                # Encrypt tokens before storing
                encrypted_access_token = encryption_service.encrypt_token(account_data.tokens.access_token)
                encrypted_refresh_token = encryption_service.encrypt_token(account_data.tokens.refresh_token) if account_data.tokens.refresh_token else None
                
                if not encrypted_access_token:
                    raise Exception("Failed to encrypt access token")
                
                # Insert new encrypted tokens
                await conn.execute("""
                    INSERT INTO google_tokens (
                        account_id, access_token_encrypted, refresh_token_encrypted, expires_at, scope
                    ) VALUES ($1, $2, $3, $4, $5)
                """,
                account_id,
                encrypted_access_token,
                encrypted_refresh_token,
                datetime.fromtimestamp(account_data.tokens.expires_at, tz=timezone.utc) if account_data.tokens.expires_at else None,
                'https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/drive.readonly https://www.googleapis.com/auth/calendar.readonly'
                )
                
                logger.info(f"Saved Google account {account_data.email} for user {user_id}")
                return str(account_id)
                
        except Exception as e:
            logger.error(f"Error saving Google account: {e}")
            raise
        finally:
            await conn.close()
    
    async def get_user_google_accounts(self, user_id: str) -> Dict[str, GoogleAccount]:
        """Get all Google accounts for a user."""
        conn = await self.get_connection()
        try:
            rows = await conn.fetch("""
                SELECT 
                    ga.id, ga.email, ga.name, ga.picture, ga.nickname, 
                    ga.is_primary, ga.connected_at,
                    gt.access_token_encrypted, gt.refresh_token_encrypted, gt.expires_at,
                    gt.access_token, gt.refresh_token
                FROM google_accounts ga
                LEFT JOIN google_tokens gt ON ga.id = gt.account_id
                WHERE ga.user_id = $1
                ORDER BY ga.is_primary DESC, ga.connected_at DESC
            """, user_id)
            
            accounts = {}
            for row in rows:
                # Convert timestamps
                connected_at = row['connected_at'].timestamp() if row['connected_at'] else datetime.now().timestamp()
                expires_at = row['expires_at'].timestamp() if row['expires_at'] else None
                
                # Decrypt tokens - prefer encrypted versions, fallback to plaintext
                access_token = None
                refresh_token = None
                
                if row['access_token_encrypted']:
                    # Try to decrypt encrypted tokens
                    access_token = encryption_service.decrypt_token(row['access_token_encrypted'])
                    if not access_token:
                        logger.error(f"Failed to decrypt access token for account {row['email']}")
                        continue  # Skip this account if decryption fails
                
                if row['refresh_token_encrypted']:
                    refresh_token = encryption_service.decrypt_token(row['refresh_token_encrypted'])
                
                # Fallback to plaintext tokens (for migration compatibility)
                if not access_token and row['access_token']:
                    access_token = row['access_token']
                    logger.warning(f"Using plaintext access token for account {row['email']} - consider re-authenticating")
                
                if not refresh_token and row['refresh_token']:
                    refresh_token = row['refresh_token']
                
                if not access_token:
                    logger.error(f"No valid access token found for account {row['email']}")
                    continue  # Skip accounts without valid tokens
                
                # Create tokens object
                tokens = GoogleTokens(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_at=expires_at
                )
                
                # Create account object
                account = GoogleAccount(
                    email=row['email'],
                    name=row['name'] or '',
                    picture=row['picture'],
                    tokens=tokens,
                    nickname=row['nickname'],
                    is_primary=row['is_primary'] or False,
                    connected_at=connected_at
                )
                
                accounts[row['email']] = account
            
            logger.info(f"Retrieved {len(accounts)} Google accounts for user {user_id}")
            return accounts
            
        except Exception as e:
            logger.error(f"Error getting Google accounts: {e}")
            raise
        finally:
            await conn.close()
    
    async def get_primary_account(self, user_id: str) -> Optional[GoogleAccount]:
        """Get the primary Google account for a user."""
        accounts = await self.get_user_google_accounts(user_id)
        for account in accounts.values():
            if account.is_primary:
                return account
        # If no primary account, return the first one
        return next(iter(accounts.values())) if accounts else None
    
    async def set_primary_account(self, user_id: str, email: str) -> bool:
        """Set an account as primary for a user."""
        conn = await self.get_connection()
        try:
            async with conn.transaction():
                # First, unset all primary accounts for this user
                await conn.execute("""
                    UPDATE google_accounts 
                    SET is_primary = FALSE 
                    WHERE user_id = $1
                """, user_id)
                
                # Then set the specified account as primary
                result = await conn.execute("""
                    UPDATE google_accounts 
                    SET is_primary = TRUE 
                    WHERE user_id = $1 AND email = $2
                """, user_id, email)
                
                success = result == 'UPDATE 1'
                if success:
                    logger.info(f"Set {email} as primary account for user {user_id}")
                return success
                
        except Exception as e:
            logger.error(f"Error setting primary account: {e}")
            raise
        finally:
            await conn.close()
    
    async def update_account_nickname(self, user_id: str, email: str, nickname: str) -> bool:
        """Update the nickname for a Google account."""
        conn = await self.get_connection()
        try:
            result = await conn.execute("""
                UPDATE google_accounts 
                SET nickname = $1, updated_at = NOW()
                WHERE user_id = $2 AND email = $3
            """, nickname, user_id, email)
            
            success = result == 'UPDATE 1'
            if success:
                logger.info(f"Updated nickname for {email} to '{nickname}' for user {user_id}")
            return success
            
        except Exception as e:
            logger.error(f"Error updating account nickname: {e}")
            raise
        finally:
            await conn.close()
    
    async def delete_google_account(self, user_id: str, email: str) -> bool:
        """Delete a Google account and its tokens."""
        conn = await self.get_connection()
        try:
            async with conn.transaction():
                # Get account ID first
                account_id = await conn.fetchval("""
                    SELECT id FROM google_accounts 
                    WHERE user_id = $1 AND email = $2
                """, user_id, email)
                
                if not account_id:
                    return False
                
                # Delete tokens first (due to foreign key)
                await conn.execute("""
                    DELETE FROM google_tokens WHERE account_id = $1
                """, account_id)
                
                # Delete account
                result = await conn.execute("""
                    DELETE FROM google_accounts 
                    WHERE user_id = $1 AND email = $2
                """, user_id, email)
                
                success = result == 'DELETE 1'
                if success:
                    logger.info(f"Deleted Google account {email} for user {user_id}")
                return success
                
        except Exception as e:
            logger.error(f"Error deleting Google account: {e}")
            raise
        finally:
            await conn.close()
    
    async def update_tokens(self, user_id: str, email: str, tokens: GoogleTokens) -> bool:
        """Update tokens for a Google account."""
        conn = await self.get_connection()
        try:
            # Get account ID
            account_id = await conn.fetchval("""
                SELECT id FROM google_accounts 
                WHERE user_id = $1 AND email = $2
            """, user_id, email)
            
            if not account_id:
                return False
            
            # Encrypt tokens before updating
            encrypted_access_token = encryption_service.encrypt_token(tokens.access_token)
            encrypted_refresh_token = encryption_service.encrypt_token(tokens.refresh_token) if tokens.refresh_token else None
            
            if not encrypted_access_token:
                raise Exception("Failed to encrypt access token during update")
            
            # Update encrypted tokens
            result = await conn.execute("""
                UPDATE google_tokens 
                SET access_token_encrypted = $1, 
                    refresh_token_encrypted = $2, 
                    expires_at = $3,
                    updated_at = NOW()
                WHERE account_id = $4
            """, 
            encrypted_access_token,
            encrypted_refresh_token,
            datetime.fromtimestamp(tokens.expires_at, tz=timezone.utc) if tokens.expires_at else None,
            account_id
            )
            
            success = result == 'UPDATE 1'
            if success:
                logger.info(f"Updated tokens for {email} for user {user_id}")
            return success
            
        except Exception as e:
            logger.error(f"Error updating tokens: {e}")
            raise
        finally:
            await conn.close()
    
    async def get_account_by_email(self, user_id: str, email: str) -> Optional[GoogleAccount]:
        """Get a specific Google account by email."""
        accounts = await self.get_user_google_accounts(user_id)
        return accounts.get(email)
    
    async def cleanup_expired_tokens(self) -> int:
        """Clean up expired tokens (maintenance function)."""
        conn = await self.get_connection()
        try:
            result = await conn.execute("""
                DELETE FROM google_tokens 
                WHERE expires_at < NOW() - INTERVAL '1 day'
            """)
            
            # Extract number of deleted rows
            deleted_count = int(result.split()[-1]) if result.startswith('DELETE ') else 0
            logger.info(f"Cleaned up {deleted_count} expired tokens")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired tokens: {e}")
            raise
        finally:
            await conn.close()


# Global instance
google_accounts_db = GoogleAccountsDB()
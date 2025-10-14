from __future__ import annotations

import os
import logging
from typing import Optional, Annotated, Dict, Any
from datetime import datetime, timedelta, timezone
from collections import defaultdict

import httpx
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..database import execute_query_one

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()

# Simple rate limiting for authentication attempts
_auth_attempts = defaultdict(list)
_MAX_AUTH_ATTEMPTS = 100  # Max attempts per IP (increased for development)
_AUTH_WINDOW_MINUTES = 1  # Time window in minutes (reduced for development)


def _check_rate_limit(ip_address: str) -> bool:
    """Check if IP has exceeded authentication rate limit"""
    now = datetime.now(timezone.utc)
    cutoff_time = now - timedelta(minutes=_AUTH_WINDOW_MINUTES)

    # Clean old attempts
    _auth_attempts[ip_address] = [
        attempt_time for attempt_time in _auth_attempts[ip_address]
        if attempt_time > cutoff_time
    ]

    # Check if over limit
    if len(_auth_attempts[ip_address]) >= _MAX_AUTH_ATTEMPTS:
        return False

    # Record this attempt
    _auth_attempts[ip_address].append(now)
    return True


async def verify_supabase_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify Supabase JWT token and return user info with enhanced validation"""
    supabase_url = os.getenv("SUPABASE_URL")
    if not supabase_url:
        logger.error("❌ [AUTH] No Supabase URL configured")
        return None

    # Basic token validation
    if not token or len(token) < 10:
        logger.error("❌ [AUTH] Invalid token format")
        return None

    # Check for suspicious token patterns
    if token.startswith('fake_') or 'test' in token.lower() or len(token) > 2000:
        logger.error("❌ [AUTH] Suspicious token pattern detected")
        return None

    headers = {
        "Authorization": f"Bearer {token}",
        "apikey": os.getenv("SUPABASE_ANON_KEY", "")
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Get user from Supabase auth
            resp = await client.get(f"{supabase_url}/auth/v1/user", headers=headers)

            if resp.status_code == 401:
                logger.error("❌ [AUTH] Token expired or invalid")
                return None
            elif resp.status_code == 429:
                logger.error("❌ [AUTH] Rate limited by Supabase")
                return None
            elif resp.status_code != 200:
                logger.error(f"❌ [AUTH] Supabase auth failed with status: {resp.status_code}")
                return None

            data = resp.json()

            # Enhanced data validation
            user_id = data.get("id")
            email = data.get("email")

            if not user_id or not email:
                logger.error("❌ [AUTH] Invalid user data from Supabase")
                return None

            # Validate email format
            if "@" not in email or "." not in email.split("@")[-1]:
                logger.error("❌ [AUTH] Invalid email format")
                return None

            # Check for email verification (optional but recommended)
            if not data.get("email_confirmed_at"):
                logger.warning("⚠️ [AUTH] Email not confirmed, proceeding anyway")

            return {
                "id": user_id,
                "email": email,
                "name": (data.get("user_metadata", {}) or {}).get("full_name"),
                "avatar_url": (data.get("user_metadata", {}) or {}).get("avatar_url"),
                "email_confirmed": bool(data.get("email_confirmed_at")),
                "last_sign_in": data.get("last_sign_in_at")
            }

    except httpx.TimeoutException:
        logger.error("❌ [AUTH] Timeout connecting to Supabase")
        return None
    except httpx.RequestError as e:
        logger.error(f"❌ [AUTH] Request error: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ [AUTH] Unexpected error: {e}")
        return None


async def get_current_user_supabase(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    request: Request = None
) -> Dict[str, Any]:
    """Get current authenticated user using Supabase directly"""
    # Check rate limit if request is available
    if request:
        client_ip = request.client.host if request.client else "unknown"
        if not _check_rate_limit(client_ip):
            logger.warning(f"❌ [AUTH] Rate limit exceeded for IP: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many authentication attempts. Please try again later."
            )

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token"
        )

    # Verify token with Supabase
    public_user = await verify_supabase_token(credentials.credentials)
    if not public_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )

    # Get user from our database
    query = """
        SELECT id, email, name, avatar_url, role, status, created_at, updated_at, last_login_at
        FROM turfmapp_agent.users 
        WHERE id = $1
    """
    user = await execute_query_one(query, public_user["id"])
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user_dict = dict(user)

    # Check if user is active
    if user_dict.get("status") != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active"
        )

    # Update last login time
    update_query = "UPDATE turfmapp_agent.users SET last_login_at = NOW() WHERE id = $1"
    await execute_query_one(update_query, user_dict["id"])
    user_dict["last_login_at"] = datetime.now(timezone.utc)

    return user_dict


async def get_current_admin_user_supabase(
    current_user: Annotated[Dict[str, Any], Depends(get_current_user_supabase)]
) -> Dict[str, Any]:
    """Get current user and verify admin privileges"""
    if current_user.get("role") not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


async def get_current_super_admin_user_supabase(
    current_user: Annotated[Dict[str, Any], Depends(get_current_user_supabase)]
) -> Dict[str, Any]:
    """Get current user and verify super admin privileges"""
    if current_user.get("role") != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin privileges required"
        )
    return current_user


# Optional user dependency (doesn't raise error if not authenticated)
async def get_current_user_optional_supabase(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[Dict[str, Any]]:
    """Get current user if authenticated, otherwise return None"""
    if not credentials:
        return None

    try:
        public_user = await verify_supabase_token(credentials.credentials)
        if not public_user:
            return None

        query = """
            SELECT id, email, name, avatar_url, role, status, created_at, updated_at, last_login_at
            FROM turfmapp_agent.users 
            WHERE id = $1
        """
        user = await execute_query_one(query, public_user["id"])
        
        if user and dict(user).get("status") == "active":
            return dict(user)
    except Exception:
        pass

    return None
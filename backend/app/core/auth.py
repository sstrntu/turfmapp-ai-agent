from __future__ import annotations

import os
from typing import Optional, Annotated, Dict, Any
from datetime import datetime

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..database import execute_query_one

# Security scheme
security = HTTPBearer()


async def verify_supabase_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify Supabase JWT token and return user info"""
    supabase_url = os.getenv("SUPABASE_URL")
    if not supabase_url:
        return None

    headers = {
        "Authorization": f"Bearer {token}",
        "apikey": os.getenv("SUPABASE_ANON_KEY", "")
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Get user from Supabase auth
            resp = await client.get(f"{supabase_url}/auth/v1/user", headers=headers)
            if resp.status_code != 200:
                return None
                
            data = resp.json()
            return {
                "id": data.get("id", ""),
                "email": data.get("email", ""),
                "name": (data.get("user_metadata", {}) or {}).get("full_name"),
                "avatar_url": (data.get("user_metadata", {}) or {}).get("avatar_url"),
            }
    except Exception:
        return None


async def get_current_user_supabase(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> Dict[str, Any]:
    """Get current authenticated user using Supabase directly"""
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
    user_dict["last_login_at"] = datetime.utcnow()

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
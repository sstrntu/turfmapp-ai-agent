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
    print(f"🔐 [DEBUG] verify_supabase_token called")
    print(f"🎫 [DEBUG] Token: {token[:20]}..." if token else "🎫 [DEBUG] Token: None")

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY", "")

    print(f"🌐 [DEBUG] SUPABASE_URL: {supabase_url}")
    print(f"🔑 [DEBUG] SUPABASE_ANON_KEY exists: {bool(supabase_anon_key)}")

    if not supabase_url:
        print(f"❌ [DEBUG] No SUPABASE_URL configured")
        return None

    headers = {
        "Authorization": f"Bearer {token}",
        "apikey": supabase_anon_key
    }

    print(f"📤 [DEBUG] Making request to: {supabase_url}/auth/v1/user")
    print(f"📤 [DEBUG] Headers: Authorization=Bearer {token[:20]}..., apikey={supabase_anon_key[:10]}...")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Get user from Supabase auth
            resp = await client.get(f"{supabase_url}/auth/v1/user", headers=headers)
            print(f"📡 [DEBUG] Supabase response status: {resp.status_code}")

            if resp.status_code != 200:
                error_text = resp.text if hasattr(resp, 'text') else 'No error text'
                print(f"❌ [DEBUG] Supabase auth failed: {error_text}")
                return None

            data = resp.json()
            print(f"✅ [DEBUG] Supabase user data: {data.get('email', 'No email')} (ID: {data.get('id', 'No ID')})")

            user_info = {
                "id": data.get("id", ""),
                "email": data.get("email", ""),
                "name": (data.get("user_metadata", {}) or {}).get("full_name"),
                "avatar_url": (data.get("user_metadata", {}) or {}).get("avatar_url"),
            }
            print(f"🔄 [DEBUG] Returning user info: {user_info}")
            return user_info

    except Exception as e:
        print(f"💥 [DEBUG] Exception in verify_supabase_token: {str(e)}")
        import traceback
        print(f"💥 [DEBUG] Traceback: {traceback.format_exc()}")
        return None


async def get_current_user_supabase(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> Dict[str, Any]:
    """Get current authenticated user using Supabase directly"""
    print(f"🚪 [DEBUG] get_current_user_supabase called")

    if not credentials:
        print(f"❌ [DEBUG] No credentials provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token"
        )

    print(f"🎫 [DEBUG] Credentials token: {credentials.credentials[:20]}...")

    # Verify token with Supabase
    print(f"🔍 [DEBUG] Verifying token with Supabase...")
    public_user = await verify_supabase_token(credentials.credentials)
    if not public_user:
        print(f"❌ [DEBUG] Token verification failed with Supabase")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )

    print(f"✅ [DEBUG] Token verified. User ID: {public_user['id']}, Email: {public_user['email']}")

    # Get user from our database
    print(f"🗄️ [DEBUG] Looking up user in local database...")
    query = """
        SELECT id, email, name, avatar_url, role, status, created_at, updated_at, last_login_at
        FROM turfmapp_agent.users
        WHERE id = $1
    """

    try:
        user = await execute_query_one(query, public_user["id"])
        print(f"📋 [DEBUG] Database query result: {user}")
    except Exception as db_error:
        print(f"💥 [DEBUG] Database query failed: {str(db_error)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(db_error)}"
        )

    if not user:
        print(f"❌ [DEBUG] User not found in local database for ID: {public_user['id']}")
        print(f"🔧 [DEBUG] This user exists in Supabase but not in local turfmapp_agent.users table")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in local database. Please contact administrator."
        )

    user_dict = dict(user)
    print(f"👤 [DEBUG] User found: {user_dict.get('email')} (Status: {user_dict.get('status')})")

    # Check if user is active
    if user_dict.get("status") != "active":
        print(f"🚫 [DEBUG] User account is not active: {user_dict.get('status')}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account status is '{user_dict.get('status')}' - must be 'active'"
        )

    # Update last login time
    print(f"🕐 [DEBUG] Updating last login time...")
    try:
        update_query = "UPDATE turfmapp_agent.users SET last_login_at = NOW() WHERE id = $1"
        await execute_query_one(update_query, user_dict["id"])
        user_dict["last_login_at"] = datetime.utcnow()
        print(f"✅ [DEBUG] Authentication successful for user: {user_dict['email']}")
    except Exception as update_error:
        print(f"⚠️ [DEBUG] Failed to update last login time: {str(update_error)}")
        # Don't fail auth just because we can't update login time

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
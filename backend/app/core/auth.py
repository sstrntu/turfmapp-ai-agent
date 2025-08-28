from __future__ import annotations

import os
from typing import Optional, Annotated
from datetime import datetime

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User, UserRole
from ..models.auth import PublicUser

# Security scheme
security = HTTPBearer()


async def verify_supabase_token(token: str) -> Optional[PublicUser]:
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
            return PublicUser(
                id=data.get("id", ""),
                email=data.get("email", ""),
                name=(data.get("user_metadata", {}) or {}).get("full_name"),
                avatar_url=(data.get("user_metadata", {}) or {}).get("avatar_url"),
            )
    except Exception:
        return None


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[Session, Depends(get_db)]
) -> User:
    """Get current authenticated user"""
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

    # Get user from database
    user = db.query(User).filter(User.id == public_user.id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if user is active
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active"
        )

    # Update last login time
    user.last_login_at = datetime.utcnow()
    db.commit()

    return user


async def get_current_admin_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Get current user and verify admin privileges"""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


async def get_current_super_admin_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Get current user and verify super admin privileges"""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin privileges required"
        )
    return current_user


# Optional user dependency (doesn't raise error if not authenticated)
async def get_current_user_optional(
    db: Annotated[Session, Depends(get_db)],
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[User]:
    """Get current user if authenticated, otherwise return None"""
    if not credentials:
        return None

    try:
        public_user = await verify_supabase_token(credentials.credentials)
        if not public_user:
            return None

        user = db.query(User).filter(User.id == public_user.id).first()
        if user and user.status == "active":
            return user
    except Exception:
        pass

    return None
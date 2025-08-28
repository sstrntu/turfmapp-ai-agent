from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, status, Header

from ...models.auth import ExchangeRequest, PublicUser
from ...services.supabase_auth import fetch_user_with_access_token

router = APIRouter()


@router.post("/exchange", response_model=PublicUser)
async def exchange_tokens(request: ExchangeRequest):
    """Exchange Supabase access token for user info (no ORM)."""
    try:
        user = await fetch_user_with_access_token(request.access_token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid access token"
            )
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication error: {str(e)}"
        )


@router.get("/me", response_model=PublicUser)
async def get_authenticated_user(authorization: Optional[str] = Header(default=None, alias="Authorization")):
    """Return the current Supabase user from the bearer token (no ORM)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    access_token = authorization.replace("Bearer ", "", 1).strip()
    user = await fetch_user_with_access_token(access_token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user


@router.post("/logout")
async def logout():
    """Logout endpoint (client handles Supabase logout)"""
    # Client-side will handle Supabase logout
    # This endpoint is mainly for consistency
    return {"message": "Logout successful"}


@router.get("/status")
async def auth_status(authorization: Optional[str] = Header(default=None, alias="Authorization")):
    """Return a minimal auth status using only Supabase token verification."""
    if not authorization or not authorization.startswith("Bearer "):
        return {"authenticated": False, "user": None, "status": None, "role": None}
    access_token = authorization.replace("Bearer ", "", 1).strip()
    user = await fetch_user_with_access_token(access_token)
    if not user:
        return {"authenticated": False, "user": None, "status": None, "role": None}
    return {
        "authenticated": True,
        "user": user,
        "status": "active",
        "role": "user"
    }
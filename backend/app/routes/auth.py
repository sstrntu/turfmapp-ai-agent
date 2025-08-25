from __future__ import annotations

import os
import secrets
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from ..models.auth import ExchangeRequest, PublicUser
from ..services.supabase_auth import fetch_user_with_access_token
from ..services.user_store import upsert_user, get_public_user_by_id
from ..utils.sessions import (
    clear_session_cookie,
    get_session_from_request,
    get_state_from_cookie,
    set_session_cookie,
    set_state_cookie,
)
from ..database import get_db
from sqlalchemy.orm import Session


router = APIRouter()


@router.get("/login")
def begin_login(response: Response) -> Response:
    """Initiate Google OAuth via Supabase by redirecting to authorize endpoint.

    Sets a CSRF `state` cookie and redirects to Supabase hosted auth.
    """
    supabase_url = os.getenv("SUPABASE_URL")
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3005")

    if not supabase_url:
        raise HTTPException(status_code=500, detail="SUPABASE_URL not configured")

    state = secrets.token_urlsafe(32)
    set_state_cookie(response, state)

    authorize_url = (
        f"{supabase_url}/auth/v1/authorize?provider=google"
        f"&redirect_to={frontend_url}/auth/callback"
        f"&scopes=openid%20email%20profile"
        f"&response_type=token"
        f"&state={state}"
    )

    response.status_code = status.HTTP_307_TEMPORARY_REDIRECT
    response.headers["Location"] = authorize_url
    return response


@router.post("/exchange")
async def exchange_tokens(
    request: Request,
    payload: ExchangeRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Validate state and access token, then create a server session cookie."""
    expected_state = get_state_from_cookie(request)
    if not expected_state or expected_state != payload.state:
        raise HTTPException(status_code=400, detail="Invalid state")

    user = await fetch_user_with_access_token(payload.access_token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid access token")

    # Ensure user is persisted locally
    public_user = upsert_user(
        db,
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
    )

    set_session_cookie(
        response,
        session_data={
            "user_id": public_user.id,
            "email": public_user.email,
            "access_token": payload.access_token,
        },
    )

    return {"ok": True, "user": public_user.model_dump()}


@router.get("/me")
async def get_me(request: Request, db: Session = Depends(get_db)) -> PublicUser:
    """Return current user as read from the session cookie by validating token with Supabase."""
    session = get_session_from_request(request)
    if not session or "access_token" not in session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Prefer local DB for user info; fall back to Supabase validation if needed
    user = get_public_user_by_id(db, session.get("user_id"))
    if user:
        return user
    remote_user = await fetch_user_with_access_token(session["access_token"])
    if not remote_user:
        raise HTTPException(status_code=401, detail="Session invalid")
    return remote_user


@router.post("/logout")
def logout(response: Response) -> Dict[str, bool]:
    clear_session_cookie(response)
    return {"ok": True}




from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import Request, Response
from itsdangerous import URLSafeSerializer


SESSION_COOKIE_NAME = "tm_session"
STATE_COOKIE_NAME = "tm_oauth_state"


def _get_serializer() -> URLSafeSerializer:
    secret = os.getenv("SESSION_SECRET", "dev-secret-please-change")
    return URLSafeSerializer(secret_key=secret, salt="tm-session")


def set_state_cookie(response: Response, state: str) -> None:
    response.set_cookie(
        key=STATE_COOKIE_NAME,
        value=state,
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
        max_age=600,
    )


def get_state_from_cookie(request: Request) -> Optional[str]:
    return request.cookies.get(STATE_COOKIE_NAME)


def set_session_cookie(response: Response, session_data: Dict[str, Any]) -> None:
    serializer = _get_serializer()
    token = serializer.dumps(session_data)
    expires = datetime.now(timezone.utc) + timedelta(days=7)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
        expires=expires,
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    response.delete_cookie(STATE_COOKIE_NAME, path="/")


def get_session_from_request(request: Request) -> Optional[Dict[str, Any]]:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None
    serializer = _get_serializer()
    try:
        session = serializer.loads(token)
        if not isinstance(session, dict):
            return None
        return session
    except Exception:
        return None




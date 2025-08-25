from __future__ import annotations

import os
from typing import Optional

import httpx

from ..models.auth import PublicUser


async def fetch_user_with_access_token(access_token: str) -> Optional[PublicUser]:
    """Fetch user info from Supabase using the provided access token.

    Args:
        access_token: Supabase access token from Google OAuth via Supabase.

    Returns:
        PublicUser if valid, else None.
    """
    supabase_url = os.getenv("SUPABASE_URL")
    if not supabase_url:
        return None

    url = f"{supabase_url}/auth/v1/user"
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            return None
        data = resp.json()
        return PublicUser(
            id=data.get("id", ""),
            email=data.get("email", ""),
            name=(data.get("user_metadata", {}) or {}).get("full_name"),
            avatar_url=(data.get("user_metadata", {}) or {}).get("avatar_url"),
        )




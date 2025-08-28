from __future__ import annotations

from pydantic import BaseModel, EmailStr
from datetime import datetime


class ExchangeRequest(BaseModel):
    access_token: str
    refresh_token: str | None = None
    state: str


class PublicUser(BaseModel):
    id: str
    email: EmailStr
    name: str | None = None
    avatar_url: str | None = None
    last_login_at: datetime | None = None




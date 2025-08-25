from __future__ import annotations

from pydantic import BaseModel, EmailStr
from datetime import datetime
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base


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


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)




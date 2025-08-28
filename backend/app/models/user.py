from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr
from sqlalchemy import String, DateTime, Enum, Boolean, JSON, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..database import Base


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class UserStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"


class User(Base):
    __tablename__ = "users"
    __table_args__ = {'schema': 'turfmapp_agent'}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    email: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER)
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus), default=UserStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    preferences: Mapped["UserPreferences"] = relationship("UserPreferences", back_populates="user", uselist=False)
    conversations: Mapped[list["Conversation"]] = relationship("Conversation", back_populates="user")
    uploads: Mapped[list["Upload"]] = relationship("Upload", back_populates="user")
    admin_permissions: Mapped[list["AdminPermission"]] = relationship("AdminPermission", back_populates="user", foreign_keys="AdminPermission.user_id")


class UserPreferences(Base):
    __tablename__ = "user_preferences"
    __table_args__ = {'schema': 'turfmapp_agent'}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid())
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("turfmapp_agent.users.id", ondelete="CASCADE"), nullable=False, unique=True)
    system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    default_model: Mapped[str] = mapped_column(String, default="gpt-4o-mini")
    settings: Mapped[dict] = mapped_column(JSON, default={})
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="preferences")


class AdminPermission(Base):
    __tablename__ = "admin_permissions"
    __table_args__ = {'schema': 'turfmapp_agent'}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid())
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("turfmapp_agent.users.id", ondelete="CASCADE"), nullable=False)
    permission: Mapped[str] = mapped_column(String, nullable=False)
    granted_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("turfmapp_agent.users.id"), nullable=True)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="admin_permissions", foreign_keys=[user_id])
    granted_by_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[granted_by])


# Pydantic models for API
class UserCreate(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    avatar_url: Optional[str] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    status: Optional[UserStatus] = None
    role: Optional[UserRole] = None


class UserPreferencesUpdate(BaseModel):
    system_prompt: Optional[str] = None
    default_model: Optional[str] = None
    settings: Optional[dict] = None


class PublicUser(BaseModel):
    id: str
    email: EmailStr
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    role: UserRole
    status: UserStatus
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserPreferencesResponse(BaseModel):
    id: str
    system_prompt: Optional[str] = None
    default_model: str
    settings: dict
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
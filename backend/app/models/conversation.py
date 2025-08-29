from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel
from sqlalchemy import String, DateTime, Text, ForeignKey, JSON, Integer, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..database import Base


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = {'schema': 'turfmapp_agent'}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid())
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("turfmapp_agent.users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    model: Mapped[str] = mapped_column(String, default="gpt-4o")
    system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Snapshot of user's system prompt at conversation start
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = {'schema': 'turfmapp_agent'}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid())
    conversation_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("turfmapp_agent.conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[MessageRole] = mapped_column(String, nullable=False, index=True)  # Using String instead of Enum for SQLite compatibility
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_metadata: Mapped[dict] = mapped_column(JSON, default={})  # attachments, sources, tool calls, etc.
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")

    # Add constraint for rating
    __table_args__ = (
        CheckConstraint('rating >= 1 AND rating <= 5', name='check_rating_range'),
    )


# Pydantic models for API
class ConversationCreate(BaseModel):
    title: Optional[str] = None
    model: str = "gpt-4o"
    system_prompt: Optional[str] = None


class ConversationUpdate(BaseModel):
    title: Optional[str] = None


class MessageCreate(BaseModel):
    role: MessageRole
    content: str
    message_metadata: Optional[dict] = None


class MessageUpdate(BaseModel):
    rating: Optional[int] = None
    feedback: Optional[str] = None


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: MessageRole
    content: str
    message_metadata: dict
    rating: Optional[int] = None
    feedback: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    id: str
    user_id: str
    title: Optional[str] = None
    model: str
    system_prompt: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse] = []

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    id: str
    title: Optional[str] = None
    model: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    last_message_at: Optional[datetime] = None

    class Config:
        from_attributes = True
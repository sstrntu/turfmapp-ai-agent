from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel
from sqlalchemy import String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    # Fallback for when pgvector is not available (SQLite mode)
    from sqlalchemy import Text
    def Vector(size):
        return Text  # Store as text in SQLite

from ..database import Base


class DocumentCollection(Base):
    __tablename__ = "document_collections"
    __table_args__ = {'schema': 'turfmapp_agent'}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid())
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("turfmapp_agent.users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    created_by_user: Mapped["User"] = relationship("User")
    documents: Mapped[list["Document"]] = relationship("Document", back_populates="collection", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = {'schema': 'turfmapp_agent'}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid())
    collection_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("turfmapp_agent.document_collections.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(1536), nullable=True)  # OpenAI embedding dimension
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    collection: Mapped["DocumentCollection"] = relationship("DocumentCollection", back_populates="documents")


# Pydantic models for API
class DocumentCollectionCreate(BaseModel):
    name: str
    description: Optional[str] = None


class DocumentCollectionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class DocumentCreate(BaseModel):
    collection_id: str
    title: str
    content: str
    source_url: Optional[str] = None


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    source_url: Optional[str] = None


class DocumentResponse(BaseModel):
    id: str
    collection_id: str
    title: str
    content: str
    source_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentCollectionResponse(BaseModel):
    id: str
    created_by: str
    name: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    document_count: int = 0

    class Config:
        from_attributes = True


class DocumentSearchResult(BaseModel):
    id: str
    title: str
    content: str
    source_url: Optional[str] = None
    similarity: float
    collection_name: str

    class Config:
        from_attributes = True
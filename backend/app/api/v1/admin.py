from __future__ import annotations

from typing import List, Annotated, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...database import get_db
from ...core.auth import get_current_admin_user
from ...models.user import User
from ...models.announcement import (
    Announcement, AnnouncementCreate, AnnouncementUpdate, AnnouncementResponse
)
from ...services.user_service import UserService
from ...core.exceptions import turfmapp_exception_to_http_exception, TurfmappException

router = APIRouter()


# Announcement management
@router.get("/announcements", response_model=List[AnnouncementResponse])
async def get_announcements(
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    include_inactive: bool = False
):
    """Get all announcements (admin only)"""
    try:
        query = db.query(Announcement)
        if not include_inactive:
            query = query.filter(Announcement.is_active == True)
        
        announcements = query.order_by(Announcement.created_at.desc()).all()
        return [AnnouncementResponse.from_orm(ann) for ann in announcements]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching announcements: {str(e)}"
        )


@router.get("/announcements/active", response_model=List[AnnouncementResponse])
async def get_active_announcements(
    db: Annotated[Session, Depends(get_db)]
):
    """Get active announcements (public endpoint)"""
    try:
        now = datetime.utcnow()
        announcements = (
            db.query(Announcement)
            .filter(
                Announcement.is_active == True,
                (Announcement.expires_at.is_(None) | (Announcement.expires_at > now))
            )
            .order_by(Announcement.created_at.desc())
            .all()
        )
        return [AnnouncementResponse.from_orm(ann) for ann in announcements]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching active announcements: {str(e)}"
        )


@router.post("/announcements", response_model=AnnouncementResponse)
async def create_announcement(
    announcement_data: AnnouncementCreate,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Create new announcement (admin only)"""
    try:
        announcement = Announcement(
            created_by=current_admin.id,
            content=announcement_data.content,
            expires_at=announcement_data.expires_at
        )
        
        db.add(announcement)
        db.commit()
        db.refresh(announcement)
        
        return AnnouncementResponse.from_orm(announcement)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating announcement: {str(e)}"
        )


@router.put("/announcements/{announcement_id}", response_model=AnnouncementResponse)
async def update_announcement(
    announcement_id: str,
    announcement_data: AnnouncementUpdate,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Update announcement (admin only)"""
    try:
        announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
        if not announcement:
            raise HTTPException(status_code=404, detail="Announcement not found")
        
        # Update fields
        for field, value in announcement_data.dict(exclude_unset=True).items():
            setattr(announcement, field, value)
        
        db.commit()
        db.refresh(announcement)
        
        return AnnouncementResponse.from_orm(announcement)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating announcement: {str(e)}"
        )


@router.delete("/announcements/{announcement_id}")
async def delete_announcement(
    announcement_id: str,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Delete announcement (admin only)"""
    try:
        announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
        if not announcement:
            raise HTTPException(status_code=404, detail="Announcement not found")
        
        db.delete(announcement)
        db.commit()
        
        return {"message": "Announcement deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting announcement: {str(e)}"
        )


# System stats
@router.get("/stats")
async def get_admin_stats(
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Get system statistics (admin only)"""
    try:
        from ...models.conversation import Conversation, Message
        from ...models.upload import Upload
        
        # Get counts
        total_users = db.query(User).count()
        pending_users = db.query(User).filter(User.status == "pending").count()
        active_users = db.query(User).filter(User.status == "active").count()
        total_conversations = db.query(Conversation).count()
        total_messages = db.query(Message).count()
        total_uploads = db.query(Upload).count()
        
        # Get recent activity (last 30 days)
        from datetime import timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        recent_users = db.query(User).filter(User.created_at >= thirty_days_ago).count()
        recent_conversations = db.query(Conversation).filter(Conversation.created_at >= thirty_days_ago).count()
        recent_messages = db.query(Message).filter(Message.created_at >= thirty_days_ago).count()
        
        return {
            "users": {
                "total": total_users,
                "pending": pending_users,
                "active": active_users,
                "recent": recent_users
            },
            "conversations": {
                "total": total_conversations,
                "recent": recent_conversations
            },
            "messages": {
                "total": total_messages,
                "recent": recent_messages
            },
            "uploads": {
                "total": total_uploads
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching admin stats: {str(e)}"
        )
from __future__ import annotations

from typing import List, Annotated, Optional, Dict, Any
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
import httpx
import os

from ...database import execute_query, execute_query_one
from ...core.auth import get_current_admin_user_supabase

router = APIRouter()


# Announcement management
@router.get("/announcements")
async def get_announcements(
    current_admin: Annotated[Dict[str, Any], Depends(get_current_admin_user_supabase)],
    include_inactive: bool = False
):
    """Get all announcements (admin only)"""
    try:
        query = """
            SELECT id, created_by, content, expires_at, is_active, created_at
            FROM turfmapp_agent.announcements
        """
        params = []
        
        if not include_inactive:
            query += " WHERE is_active = true"
        
        query += " ORDER BY created_at DESC"
        
        announcements = await execute_query(query, *params)
        return [dict(ann) for ann in announcements]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching announcements: {str(e)}"
        )


@router.get("/announcements/active")
async def get_active_announcements():
    """Get active announcements (public endpoint)"""
    try:
        now = datetime.now(timezone.utc)
        query = """
            SELECT id, created_by, content, expires_at, is_active, created_at
            FROM turfmapp_agent.announcements
            WHERE is_active = true 
            AND (expires_at IS NULL OR expires_at > $1)
            ORDER BY created_at DESC
        """
        announcements = await execute_query(query, now)
        return [dict(ann) for ann in announcements]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching active announcements: {str(e)}"
        )


@router.post("/announcements")
async def create_announcement(
    announcement_data: Dict[str, Any],
    current_admin: Annotated[Dict[str, Any], Depends(get_current_admin_user_supabase)]
):
    """Create new announcement (admin only)"""
    try:
        import uuid
        announcement_id = str(uuid.uuid4())
        
        query = """
            INSERT INTO turfmapp_agent.announcements (id, created_by, content, expires_at, created_at, updated_at)
            VALUES ($1, $2, $3, $4, NOW(), NOW())
            RETURNING id, created_by, content, expires_at, is_active, created_at, updated_at
        """
        
        result = await execute_query_one(
            query,
            announcement_id,
            current_admin["id"],
            announcement_data.get("content"),
            announcement_data.get("expires_at")
        )
        
        return dict(result) if result else None
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating announcement: {str(e)}"
        )


@router.put("/announcements/{announcement_id}")
async def update_announcement(
    announcement_id: str,
    announcement_data: Dict[str, Any],
    current_admin: Annotated[Dict[str, Any], Depends(get_current_admin_user_supabase)]
):
    """Update announcement (admin only)"""
    try:
        # Check if announcement exists
        check_query = "SELECT id FROM turfmapp_agent.announcements WHERE id = $1"
        existing = await execute_query_one(check_query, announcement_id)
        
        if not existing:
            raise HTTPException(status_code=404, detail="Announcement not found")
        
        # Build update query dynamically based on provided fields
        update_fields = []
        params = []
        param_count = 1
        
        for field, value in announcement_data.items():
            if field in ["content", "expires_at", "is_active"]:
                update_fields.append(f"{field} = ${param_count}")
                params.append(value)
                param_count += 1
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="No valid fields to update")
        
        update_fields.append(f"updated_at = NOW()")
        params.append(announcement_id)
        
        query = f"""
            UPDATE turfmapp_agent.announcements 
            SET {', '.join(update_fields)}
            WHERE id = ${param_count}
            RETURNING id, created_by, content, expires_at, is_active, created_at, updated_at
        """
        
        result = await execute_query_one(query, *params)
        return dict(result) if result else None
        
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
    current_admin: Annotated[Dict[str, Any], Depends(get_current_admin_user_supabase)]
):
    """Delete announcement (admin only)"""
    try:
        query = "DELETE FROM turfmapp_agent.announcements WHERE id = $1"
        await execute_query(query, announcement_id)
        return {"message": "Announcement deleted successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting announcement: {str(e)}"
        )


# System stats
@router.get("/stats")
async def get_admin_stats(
    current_admin: Annotated[Dict[str, Any], Depends(get_current_admin_user_supabase)]
):
    """Get system statistics (admin only)"""
    try:
        # Get counts
        total_users = await execute_query_one("SELECT COUNT(*) as count FROM turfmapp_agent.users")
        pending_users = await execute_query_one("SELECT COUNT(*) as count FROM turfmapp_agent.users WHERE status = 'pending'")
        active_users = await execute_query_one("SELECT COUNT(*) as count FROM turfmapp_agent.users WHERE status = 'active'")
        total_conversations = await execute_query_one("SELECT COUNT(*) as count FROM turfmapp_agent.conversations")
        total_messages = await execute_query_one("SELECT COUNT(*) as count FROM turfmapp_agent.messages")
        total_uploads = await execute_query_one("SELECT COUNT(*) as count FROM turfmapp_agent.uploads")
        
        # Get recent activity (last 30 days)
        from datetime import timedelta
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        
        recent_users = await execute_query_one("SELECT COUNT(*) as count FROM turfmapp_agent.users WHERE created_at >= $1", thirty_days_ago)
        recent_conversations = await execute_query_one("SELECT COUNT(*) as count FROM turfmapp_agent.conversations WHERE created_at >= $1", thirty_days_ago)
        recent_messages = await execute_query_one("SELECT COUNT(*) as count FROM turfmapp_agent.messages WHERE created_at >= $1", thirty_days_ago)
        
        return {
            "users": {
                "total": total_users["count"] if total_users else 0,
                "pending": pending_users["count"] if pending_users else 0,
                "active": active_users["count"] if active_users else 0,
                "recent": recent_users["count"] if recent_users else 0
            },
            "conversations": {
                "total": total_conversations["count"] if total_conversations else 0,
                "recent": recent_conversations["count"] if recent_conversations else 0
            },
            "messages": {
                "total": total_messages["count"] if total_messages else 0,
                "recent": recent_messages["count"] if recent_messages else 0
            },
            "uploads": {
                "total": total_uploads["count"] if total_uploads else 0
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching admin stats: {str(e)}"
        )


# User Management Endpoints
@router.get("/users")
async def get_users(
    current_admin: Annotated[Dict[str, Any], Depends(get_current_admin_user_supabase)],
    skip: int = 0,
    limit: int = 50,
    role: Optional[str] = None,
    status: Optional[str] = None
):
    """Get list of users (admin only)"""
    try:
        query = "SELECT id, email, name, avatar_url, role, status, created_at, updated_at, last_login_at FROM turfmapp_agent.users"
        params = []
        conditions = []
        
        if role:
            conditions.append(f"role = ${len(params) + 1}")
            params.append(role)
        
        if status:
            conditions.append(f"status = ${len(params) + 1}")
            params.append(status)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += f" ORDER BY created_at DESC OFFSET ${len(params) + 1} LIMIT ${len(params) + 2}"
        params.extend([skip, limit])
        
        users = await execute_query(query, *params)
        return [dict(user) for user in users]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching users: {str(e)}"
        )


@router.get("/users/pending")
async def get_pending_users(
    current_admin: Annotated[Dict[str, Any], Depends(get_current_admin_user_supabase)]
):
    """Get users pending approval (admin only)"""
    try:
        query = """
            SELECT id, email, name, avatar_url, role, status, created_at, updated_at, last_login_at 
            FROM turfmapp_agent.users 
            WHERE status = 'pending'
            ORDER BY created_at DESC
        """
        users = await execute_query(query)
        return [dict(user) for user in users]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching pending users: {str(e)}"
        )


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    user_data: Dict[str, Any],
    current_admin: Annotated[Dict[str, Any], Depends(get_current_admin_user_supabase)]
):
    """Update user (admin only)"""
    try:
        # Prevent non-super-admin from setting super admin role
        if (user_data.get("role") == "super_admin" and 
            current_admin.get("role") != "super_admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super admins can assign super admin role"
            )
        
        # Build update query dynamically
        update_fields = []
        params = []
        param_count = 1
        
        for field, value in user_data.items():
            if field in ["name", "avatar_url", "role", "status"]:
                update_fields.append(f"{field} = ${param_count}")
                params.append(value)
                param_count += 1
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="No valid fields to update")
        
        update_fields.append("updated_at = NOW()")
        params.append(user_id)
        
        query = f"""
            UPDATE turfmapp_agent.users 
            SET {', '.join(update_fields)}
            WHERE id = ${param_count}
            RETURNING id, email, name, avatar_url, role, status, created_at, updated_at, last_login_at
        """
        
        result = await execute_query_one(query, *params)
        
        if not result:
            raise HTTPException(status_code=404, detail="User not found")
            
        return dict(result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user: {str(e)}"
        )


@router.post("/users/{user_id}/approve")
async def approve_user(
    user_id: str,
    current_admin: Annotated[Dict[str, Any], Depends(get_current_admin_user_supabase)]
):
    """Approve user account (admin only)"""
    try:
        query = """
            UPDATE turfmapp_agent.users 
            SET status = 'active', updated_at = NOW()
            WHERE id = $1
            RETURNING id, email, name, avatar_url, role, status, created_at, updated_at, last_login_at
        """
        result = await execute_query_one(query, user_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="User not found")
            
        return dict(result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error approving user: {str(e)}"
        )


@router.post("/users/{user_id}/suspend")
async def suspend_user(
    user_id: str,
    current_admin: Annotated[Dict[str, Any], Depends(get_current_admin_user_supabase)]
):
    """Suspend user account (admin only)"""
    try:
        query = """
            UPDATE turfmapp_agent.users 
            SET status = 'suspended', updated_at = NOW()
            WHERE id = $1
            RETURNING id, email, name, avatar_url, role, status, created_at, updated_at, last_login_at
        """
        result = await execute_query_one(query, user_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="User not found")
            
        return dict(result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error suspending user: {str(e)}"
        )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_admin: Annotated[Dict[str, Any], Depends(get_current_admin_user_supabase)]
):
    """Delete user account (admin only)"""
    try:
        # Prevent admins from deleting themselves
        if user_id == current_admin["id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account"
            )
        
        query = "DELETE FROM turfmapp_agent.users WHERE id = $1"
        await execute_query(query, user_id)
        return {"message": "User deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting user: {str(e)}"
        )
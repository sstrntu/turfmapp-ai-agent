from __future__ import annotations

from typing import List, Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...database import get_db
from ...core.auth import get_current_user, get_current_admin_user
from ...models.user import (
    User, UserUpdate, UserPreferencesUpdate, PublicUser, UserPreferencesResponse,
    UserRole, UserStatus
)
from ...services.user_service import UserService
from ...core.exceptions import turfmapp_exception_to_http_exception, TurfmappException

router = APIRouter()


@router.get("/me", response_model=PublicUser)
async def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_user)]
):
    """Get current user's profile"""
    return PublicUser.from_orm(current_user)


@router.put("/me", response_model=PublicUser)
async def update_current_user_profile(
    user_data: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Update current user's profile"""
    try:
        # Users can only update their name and avatar, not role/status
        allowed_data = UserUpdate(
            name=user_data.name,
            avatar_url=user_data.avatar_url
        )
        
        updated_user = UserService.update_user(db, current_user.id, allowed_data)
        return PublicUser.from_orm(updated_user)
        
    except TurfmappException as e:
        raise turfmapp_exception_to_http_exception(e)


@router.get("/me/preferences", response_model=UserPreferencesResponse)
async def get_user_preferences(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Get user preferences (including system prompt)"""
    try:
        preferences = UserService.get_user_preferences(db, current_user.id)
        if not preferences:
            # Create default preferences
            preferences = UserService.update_user_preferences(
                db, current_user.id, UserPreferencesUpdate()
            )
        return UserPreferencesResponse.from_orm(preferences)
        
    except TurfmappException as e:
        raise turfmapp_exception_to_http_exception(e)


@router.put("/me/preferences", response_model=UserPreferencesResponse)
async def update_user_preferences(
    preferences_data: UserPreferencesUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Update user preferences (including system prompt)"""
    try:
        updated_preferences = UserService.update_user_preferences(
            db, current_user.id, preferences_data
        )
        return UserPreferencesResponse.from_orm(updated_preferences)
        
    except TurfmappException as e:
        raise turfmapp_exception_to_http_exception(e)


# Admin-only routes
@router.get("/", response_model=List[PublicUser])
async def get_users_list(
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = 0,
    limit: int = 50,
    role: Optional[UserRole] = None,
    status: Optional[UserStatus] = None
):
    """Get list of users (admin only)"""
    try:
        users = UserService.get_users_list(db, skip, limit, role, status)
        return [PublicUser.from_orm(user) for user in users]
        
    except TurfmappException as e:
        raise turfmapp_exception_to_http_exception(e)


@router.get("/pending", response_model=List[PublicUser])
async def get_pending_users(
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Get users pending approval (admin only)"""
    try:
        users = UserService.get_pending_users(db)
        return [PublicUser.from_orm(user) for user in users]
        
    except TurfmappException as e:
        raise turfmapp_exception_to_http_exception(e)


@router.post("/users/{user_id}/approve")
async def approve_user(
    user_id: str,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Approve user account (admin only)"""
    try:
        user = UserService.approve_user(db, user_id, current_admin.id)
        return {
            "message": "User approved successfully",
            "user": PublicUser.from_orm(user)
        }
        
    except TurfmappException as e:
        raise turfmapp_exception_to_http_exception(e)


@router.post("/users/{user_id}/suspend")
async def suspend_user(
    user_id: str,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Suspend user account (admin only)"""
    try:
        user = UserService.suspend_user(db, user_id, current_admin.id)
        return {
            "message": "User suspended successfully",
            "user": PublicUser.from_orm(user)
        }
        
    except TurfmappException as e:
        raise turfmapp_exception_to_http_exception(e)


@router.put("/users/{user_id}/role")
async def set_user_role(
    user_id: str,
    request: dict,  # {"role": "admin"}
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Set user role (admin only)"""
    try:
        role_str = request.get("role")
        if not role_str:
            raise HTTPException(status_code=400, detail="Role is required")
        
        try:
            role = UserRole(role_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid role")
        
        # Only super admins can create other super admins
        if role == UserRole.SUPER_ADMIN and current_admin.role != UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=403, 
                detail="Only super admins can grant super admin privileges"
            )
        
        user = UserService.set_user_role(db, user_id, role, current_admin.id)
        return {
            "message": "User role updated successfully",
            "user": PublicUser.from_orm(user)
        }
        
    except TurfmappException as e:
        raise turfmapp_exception_to_http_exception(e)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Delete user account (admin only)"""
    try:
        # Prevent admins from deleting themselves
        if user_id == current_admin.id:
            raise HTTPException(status_code=400, detail="Cannot delete your own account")
        
        success = UserService.delete_user(db, user_id)
        if success:
            return {"message": "User deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="User not found")
            
    except TurfmappException as e:
        raise turfmapp_exception_to_http_exception(e)


@router.get("/search")
async def search_users(
    q: str,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = 20
):
    """Search users by name or email (admin only)"""
    try:
        if len(q.strip()) < 2:
            raise HTTPException(status_code=400, detail="Search query must be at least 2 characters")
        
        users = UserService.search_users(db, q, limit)
        return [PublicUser.from_orm(user) for user in users]
        
    except TurfmappException as e:
        raise turfmapp_exception_to_http_exception(e)
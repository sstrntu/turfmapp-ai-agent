from __future__ import annotations

from typing import Optional, List
from datetime import datetime, timezone

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from ..models.user import (
    User, UserPreferences, AdminPermission, 
    UserCreate, UserUpdate, UserPreferencesUpdate,
    PublicUser, UserPreferencesResponse, UserRole, UserStatus
)
from ..core.exceptions import NotFoundError, ConflictError


class UserService:
    """Service for user management operations"""

    @staticmethod
    def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return db.query(User).options(joinedload(User.preferences)).filter(User.id == user_id).first()

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def create_user(db: Session, user_data: UserCreate) -> User:
        """Create new user (called from Supabase trigger)"""
        # Check if user already exists
        existing = UserService.get_user_by_email(db, user_data.email)
        if existing:
            raise ConflictError(f"User with email {user_data.email} already exists")

        # Create user
        user = User(
            email=user_data.email,
            name=user_data.name,
            avatar_url=user_data.avatar_url,
            status=UserStatus.PENDING  # Requires admin approval
        )
        db.add(user)
        db.flush()  # Get the ID

        # Create default preferences
        preferences = UserPreferences(user_id=user.id)
        db.add(preferences)
        
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def update_user(db: Session, user_id: str, user_data: UserUpdate) -> User:
        """Update user information"""
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found")

        # Update fields
        for field, value in user_data.dict(exclude_unset=True).items():
            setattr(user, field, value)

        user.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_user_preferences(db: Session, user_id: str) -> Optional[UserPreferences]:
        """Get user preferences"""
        return db.query(UserPreferences).filter(UserPreferences.user_id == user_id).first()

    @staticmethod
    def update_user_preferences(db: Session, user_id: str, preferences_data: UserPreferencesUpdate) -> UserPreferences:
        """Update user preferences"""
        preferences = UserService.get_user_preferences(db, user_id)
        
        if not preferences:
            # Create new preferences if they don't exist
            preferences = UserPreferences(
                user_id=user_id,
                **preferences_data.dict(exclude_unset=True)
            )
            db.add(preferences)
        else:
            # Update existing preferences
            for field, value in preferences_data.dict(exclude_unset=True).items():
                setattr(preferences, field, value)
            preferences.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(preferences)
        return preferences

    @staticmethod
    def get_users_list(
        db: Session, 
        skip: int = 0, 
        limit: int = 50,
        role: Optional[UserRole] = None,
        status: Optional[UserStatus] = None
    ) -> List[User]:
        """Get list of users with filtering"""
        query = db.query(User).options(joinedload(User.preferences))
        
        if role:
            query = query.filter(User.role == role)
        if status:
            query = query.filter(User.status == status)
            
        return query.offset(skip).limit(limit).all()

    @staticmethod
    def get_pending_users(db: Session) -> List[User]:
        """Get users pending approval"""
        return db.query(User).filter(User.status == UserStatus.PENDING).all()

    @staticmethod
    def approve_user(db: Session, user_id: str, approved_by: str) -> User:
        """Approve user account"""
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found")

        user.status = UserStatus.ACTIVE
        user.updated_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def suspend_user(db: Session, user_id: str, suspended_by: str) -> User:
        """Suspend user account"""
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found")

        user.status = UserStatus.SUSPENDED
        user.updated_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def set_user_role(db: Session, user_id: str, role: UserRole, granted_by: str) -> User:
        """Set user role"""
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found")

        old_role = user.role
        user.role = role
        user.updated_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def delete_user(db: Session, user_id: str) -> bool:
        """Delete user account"""
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found")

        db.delete(user)
        db.commit()
        return True

    @staticmethod
    def search_users(db: Session, query: str, limit: int = 20) -> List[User]:
        """Search users by name or email"""
        search_term = f"%{query.lower()}%"
        return (
            db.query(User)
            .filter(
                (func.lower(User.name).contains(search_term)) |
                (func.lower(User.email).contains(search_term))
            )
            .limit(limit)
            .all()
        )
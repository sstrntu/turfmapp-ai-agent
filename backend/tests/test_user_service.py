"""
Comprehensive tests for UserService - User Management Operations

This module provides complete test coverage for the UserService
that handles user CRUD operations, preferences, and admin functions.
"""
from __future__ import annotations

import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session
from datetime import datetime

from app.services.user_service import UserService
from app.models.user import (
    UserCreate, UserUpdate, UserPreferencesUpdate, 
    UserRole, UserStatus
)
from app.core.exceptions import NotFoundError, ConflictError


# Mock models for testing
class MockUser:
    def __init__(self, id="user-123", email="test@example.com", name="Test User", 
                 status=UserStatus.ACTIVE, role=UserRole.USER, avatar_url=None):
        self.id = id
        self.email = email
        self.name = name
        self.status = status
        self.role = role
        self.avatar_url = avatar_url
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.approved_at = None
        self.approved_by = None
        self.suspended_at = None
        self.suspended_by = None
        self.preferences = None


class MockUserPreferences:
    def __init__(self, user_id="user-123", system_prompt=None, model="gpt-4", temperature=0.7):
        self.user_id = user_id
        self.system_prompt = system_prompt
        self.model = model
        self.temperature = temperature
        self.max_tokens = 2000
        self.created_at = datetime.now()
        self.updated_at = datetime.now()


class TestUserRetrieval:
    """Test user retrieval operations."""
    
    def test_get_user_by_id_success(self):
        """Test successful user retrieval by ID."""
        mock_db = Mock(spec=Session)
        mock_user = MockUser()
        
        # Mock the query chain
        mock_query = mock_db.query.return_value
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_user
        
        result = UserService.get_user_by_id(mock_db, "user-123")
        
        assert result == mock_user
        mock_db.query.assert_called_once()
    
    def test_get_user_by_id_not_found(self):
        """Test user retrieval when user doesn't exist."""
        mock_db = Mock(spec=Session)
        
        mock_query = mock_db.query.return_value
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        result = UserService.get_user_by_id(mock_db, "nonexistent")
        
        assert result is None
    
    def test_get_user_by_email_success(self):
        """Test successful user retrieval by email."""
        mock_db = Mock(spec=Session)
        mock_user = MockUser(email="test@example.com")
        
        mock_query = mock_db.query.return_value
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_user
        
        result = UserService.get_user_by_email(mock_db, "test@example.com")
        
        assert result == mock_user
        assert result.email == "test@example.com"
    
    def test_get_user_by_email_not_found(self):
        """Test user retrieval by email when not found."""
        mock_db = Mock(spec=Session)
        
        mock_query = mock_db.query.return_value
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        result = UserService.get_user_by_email(mock_db, "notfound@example.com")
        
        assert result is None


class TestUserCreation:
    """Test user creation operations."""
    
    def test_create_user_success(self):
        """Test successful user creation."""
        mock_db = Mock(spec=Session)
        mock_user = MockUser(status=UserStatus.PENDING)
        mock_preferences = MockUserPreferences()
        
        with patch.object(UserService, 'get_user_by_email') as mock_get, \
             patch('app.services.user_service.User') as mock_user_class, \
             patch('app.services.user_service.UserPreferences') as mock_prefs_class:
            
            mock_get.return_value = None  # User doesn't exist
            mock_user_class.return_value = mock_user
            mock_prefs_class.return_value = mock_preferences
            mock_user.id = "user-123"  # Set ID after flush
            
            user_data = UserCreate(
                email="new@example.com",
                name="New User",
                avatar_url="https://example.com/avatar.jpg"
            )
            
            result = UserService.create_user(mock_db, user_data)
            
            assert result == mock_user
            assert result.status == UserStatus.PENDING
            mock_db.add.assert_called()
            mock_db.flush.assert_called_once()
            mock_db.commit.assert_called_once()
    
    def test_create_user_already_exists(self):
        """Test user creation when user already exists."""
        mock_db = Mock(spec=Session)
        existing_user = MockUser(email="existing@example.com")
        
        with patch.object(UserService, 'get_user_by_email') as mock_get:
            mock_get.return_value = existing_user
            
            user_data = UserCreate(
                email="existing@example.com",
                name="Existing User"
            )
            
            with pytest.raises(ConflictError, match="already exists"):
                UserService.create_user(mock_db, user_data)
    
    def test_create_user_minimal_data(self):
        """Test user creation with minimal required data."""
        mock_db = Mock(spec=Session)
        mock_user = MockUser()
        mock_preferences = MockUserPreferences()
        
        with patch.object(UserService, 'get_user_by_email') as mock_get, \
             patch('app.services.user_service.User') as mock_user_class, \
             patch('app.services.user_service.UserPreferences') as mock_prefs_class:
            
            mock_get.return_value = None
            mock_user_class.return_value = mock_user
            mock_prefs_class.return_value = mock_preferences
            mock_user.id = "user-123"
            
            user_data = UserCreate(email="minimal@example.com", name="Minimal User")
            
            result = UserService.create_user(mock_db, user_data)
            
            assert result == mock_user
            mock_user_class.assert_called_once()


class TestUserUpdates:
    """Test user update operations."""
    
    def test_update_user_success(self):
        """Test successful user update."""
        mock_db = Mock(spec=Session)
        mock_user = MockUser(name="Old Name")
        
        with patch.object(UserService, 'get_user_by_id') as mock_get:
            mock_get.return_value = mock_user
            
            user_data = UserUpdate(name="New Name", avatar_url="https://example.com/new.jpg")
            
            result = UserService.update_user(mock_db, "user-123", user_data)
            
            assert result == mock_user
            assert mock_user.name == "New Name"
            assert mock_user.avatar_url == "https://example.com/new.jpg"
            mock_db.commit.assert_called_once()
    
    def test_update_user_not_found(self):
        """Test updating non-existent user."""
        mock_db = Mock(spec=Session)
        
        with patch.object(UserService, 'get_user_by_id') as mock_get:
            mock_get.return_value = None
            
            user_data = UserUpdate(name="New Name")
            
            with pytest.raises(NotFoundError):
                UserService.update_user(mock_db, "nonexistent", user_data)
    
    def test_update_user_partial_data(self):
        """Test updating user with partial data."""
        mock_db = Mock(spec=Session)
        mock_user = MockUser(name="Original Name", avatar_url="original.jpg")
        
        with patch.object(UserService, 'get_user_by_id') as mock_get:
            mock_get.return_value = mock_user
            
            # Only update name, leave avatar_url unchanged
            user_data = UserUpdate(name="Updated Name")
            
            result = UserService.update_user(mock_db, "user-123", user_data)
            
            assert result.name == "Updated Name"
            assert result.avatar_url == "original.jpg"  # Unchanged


class TestUserPreferences:
    """Test user preferences operations."""
    
    def test_get_user_preferences_success(self):
        """Test successful preferences retrieval."""
        mock_db = Mock(spec=Session)
        mock_preferences = MockUserPreferences()
        
        mock_query = mock_db.query.return_value
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_preferences
        
        result = UserService.get_user_preferences(mock_db, "user-123")
        
        assert result == mock_preferences
    
    def test_get_user_preferences_not_found(self):
        """Test preferences retrieval when none exist."""
        mock_db = Mock(spec=Session)
        
        mock_query = mock_db.query.return_value
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        result = UserService.get_user_preferences(mock_db, "user-123")
        
        assert result is None
    
    def test_update_user_preferences_existing(self):
        """Test updating existing user preferences."""
        mock_db = Mock(spec=Session)
        mock_preferences = MockUserPreferences(system_prompt="Old prompt")
        
        with patch.object(UserService, 'get_user_preferences') as mock_get:
            mock_get.return_value = mock_preferences
            
            prefs_data = UserPreferencesUpdate(
                system_prompt="New system prompt",
                model="gpt-4-turbo",
                temperature=0.8
            )
            
            result = UserService.update_user_preferences(mock_db, "user-123", prefs_data)
            
            assert result == mock_preferences
            assert mock_preferences.system_prompt == "New system prompt"
            assert mock_preferences.model == "gpt-4-turbo"
            assert mock_preferences.temperature == 0.8
            mock_db.commit.assert_called_once()
    
    def test_update_user_preferences_create_new(self):
        """Test creating new preferences when none exist."""
        mock_db = Mock(spec=Session)
        mock_preferences = MockUserPreferences()
        
        with patch.object(UserService, 'get_user_preferences') as mock_get, \
             patch('app.services.user_service.UserPreferences') as mock_prefs_class:
            
            mock_get.return_value = None
            mock_prefs_class.return_value = mock_preferences
            
            prefs_data = UserPreferencesUpdate(system_prompt="New prompt")
            
            result = UserService.update_user_preferences(mock_db, "user-123", prefs_data)
            
            assert result == mock_preferences
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()


class TestUserListing:
    """Test user listing and search operations."""
    
    def test_get_users_list_success(self):
        """Test successful user listing with pagination."""
        mock_db = Mock(spec=Session)
        users = [
            MockUser(id="user-1", name="User One"),
            MockUser(id="user-2", name="User Two")
        ]
        
        mock_query = mock_db.query.return_value
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = users
        
        result = UserService.get_users_list(mock_db, skip=0, limit=10)
        
        assert result == users
        mock_query.offset.assert_called_with(0)
        mock_query.limit.assert_called_with(10)
    
    def test_get_users_list_with_status_filter(self):
        """Test user listing with status filter."""
        mock_db = Mock(spec=Session)
        active_users = [MockUser(status=UserStatus.ACTIVE)]
        
        mock_query = mock_db.query.return_value
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = active_users
        
        result = UserService.get_users_list(mock_db, status=UserStatus.ACTIVE)
        
        assert result == active_users
        mock_query.filter.assert_called_once()
    
    def test_get_pending_users(self):
        """Test getting users pending approval."""
        mock_db = Mock(spec=Session)
        pending_users = [
            MockUser(status=UserStatus.PENDING, name="Pending User 1"),
            MockUser(status=UserStatus.PENDING, name="Pending User 2")
        ]
        
        mock_query = mock_db.query.return_value
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = pending_users
        
        result = UserService.get_pending_users(mock_db)
        
        assert result == pending_users
        assert all(user.status == UserStatus.PENDING for user in result)
    
    def test_search_users_success(self):
        """Test user search functionality."""
        mock_db = Mock(spec=Session)
        matching_users = [
            MockUser(name="John Smith", email="john@example.com"),
            MockUser(name="John Doe", email="john.doe@example.com")
        ]
        
        mock_query = mock_db.query.return_value
        mock_query.filter.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = matching_users
        
        result = UserService.search_users(mock_db, "john", limit=10)
        
        assert result == matching_users
        mock_query.limit.assert_called_with(10)
    
    def test_search_users_empty_query(self):
        """Test user search with empty query."""
        mock_db = Mock(spec=Session)
        
        result = UserService.search_users(mock_db, "")
        
        assert result == []
        mock_db.query.assert_not_called()


class TestUserAdministration:
    """Test user administration operations."""
    
    def test_approve_user_success(self):
        """Test successful user approval."""
        mock_db = Mock(spec=Session)
        mock_user = MockUser(status=UserStatus.PENDING)
        
        with patch.object(UserService, 'get_user_by_id') as mock_get:
            mock_get.return_value = mock_user
            
            result = UserService.approve_user(mock_db, "user-123", "admin-456")
            
            assert result == mock_user
            assert mock_user.status == UserStatus.ACTIVE
            assert mock_user.approved_by == "admin-456"
            assert mock_user.approved_at is not None
            mock_db.commit.assert_called_once()
    
    def test_approve_user_not_found(self):
        """Test approving non-existent user."""
        mock_db = Mock(spec=Session)
        
        with patch.object(UserService, 'get_user_by_id') as mock_get:
            mock_get.return_value = None
            
            with pytest.raises(NotFoundError):
                UserService.approve_user(mock_db, "nonexistent", "admin-456")
    
    def test_suspend_user_success(self):
        """Test successful user suspension."""
        mock_db = Mock(spec=Session)
        mock_user = MockUser(status=UserStatus.ACTIVE)
        
        with patch.object(UserService, 'get_user_by_id') as mock_get:
            mock_get.return_value = mock_user
            
            result = UserService.suspend_user(mock_db, "user-123", "admin-456")
            
            assert result == mock_user
            assert mock_user.status == UserStatus.SUSPENDED
            assert mock_user.suspended_by == "admin-456"
            assert mock_user.suspended_at is not None
            mock_db.commit.assert_called_once()
    
    def test_suspend_user_not_found(self):
        """Test suspending non-existent user."""
        mock_db = Mock(spec=Session)
        
        with patch.object(UserService, 'get_user_by_id') as mock_get:
            mock_get.return_value = None
            
            with pytest.raises(NotFoundError):
                UserService.suspend_user(mock_db, "nonexistent", "admin-456")
    
    def test_set_user_role_success(self):
        """Test successful user role change."""
        mock_db = Mock(spec=Session)
        mock_user = MockUser(role=UserRole.USER)
        
        with patch.object(UserService, 'get_user_by_id') as mock_get:
            mock_get.return_value = mock_user
            
            result = UserService.set_user_role(mock_db, "user-123", UserRole.ADMIN, "super-admin")
            
            assert result == mock_user
            assert mock_user.role == UserRole.ADMIN
            mock_db.commit.assert_called_once()
    
    def test_set_user_role_not_found(self):
        """Test setting role for non-existent user."""
        mock_db = Mock(spec=Session)
        
        with patch.object(UserService, 'get_user_by_id') as mock_get:
            mock_get.return_value = None
            
            with pytest.raises(NotFoundError):
                UserService.set_user_role(mock_db, "nonexistent", UserRole.ADMIN, "admin")
    
    def test_delete_user_success(self):
        """Test successful user deletion."""
        mock_db = Mock(spec=Session)
        mock_user = MockUser()
        
        with patch.object(UserService, 'get_user_by_id') as mock_get:
            mock_get.return_value = mock_user
            
            result = UserService.delete_user(mock_db, "user-123")
            
            assert result is True
            mock_db.delete.assert_called_once_with(mock_user)
            mock_db.commit.assert_called_once()
    
    def test_delete_user_not_found(self):
        """Test deleting non-existent user."""
        mock_db = Mock(spec=Session)
        
        with patch.object(UserService, 'get_user_by_id') as mock_get:
            mock_get.return_value = None
            
            result = UserService.delete_user(mock_db, "nonexistent")
            
            assert result is False
            mock_db.delete.assert_not_called()


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_database_error_during_creation(self):
        """Test handling database errors during user creation."""
        mock_db = Mock(spec=Session)
        mock_db.commit.side_effect = Exception("Database error")
        
        with patch.object(UserService, 'get_user_by_email') as mock_get, \
             patch('app.services.user_service.User') as mock_user_class, \
             patch('app.services.user_service.UserPreferences') as mock_prefs_class:
            
            mock_get.return_value = None
            mock_user_class.return_value = MockUser()
            mock_prefs_class.return_value = MockUserPreferences()
            
            user_data = UserCreate(email="test@example.com", name="Test User")
            
            with pytest.raises(Exception, match="Database error"):
                UserService.create_user(mock_db, user_data)
    
    def test_concurrent_user_creation(self):
        """Test handling concurrent user creation attempts."""
        mock_db = Mock(spec=Session)
        
        # First check returns None (user doesn't exist)
        # But by the time we try to create, user exists (race condition)
        with patch.object(UserService, 'get_user_by_email') as mock_get:
            mock_get.return_value = None
            
            with patch('app.services.user_service.User') as mock_user_class:
                mock_user_class.side_effect = Exception("Unique constraint violation")
                
                user_data = UserCreate(email="concurrent@example.com", name="Concurrent User")
                
                with pytest.raises(Exception):
                    UserService.create_user(mock_db, user_data)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_preferences_update_with_none_values(self):
        """Test updating preferences with None values."""
        mock_db = Mock(spec=Session)
        mock_preferences = MockUserPreferences(system_prompt="Original")
        
        with patch.object(UserService, 'get_user_preferences') as mock_get:
            mock_get.return_value = mock_preferences
            
            # Update with None should not change the value
            prefs_data = UserPreferencesUpdate(system_prompt=None, temperature=0.9)
            
            result = UserService.update_user_preferences(mock_db, "user-123", prefs_data)
            
            # system_prompt should remain unchanged, temperature should update
            assert result.system_prompt == "Original"
            assert result.temperature == 0.9
    
    def test_search_users_with_special_characters(self):
        """Test user search with special characters."""
        mock_db = Mock(spec=Session)
        
        # Search with special characters should be handled gracefully
        result = UserService.search_users(mock_db, "user@domain.com")
        
        # Should not crash and should attempt the query
        mock_db.query.assert_called_once()
    
    def test_pagination_boundary_conditions(self):
        """Test pagination with boundary conditions."""
        mock_db = Mock(spec=Session)
        
        mock_query = mock_db.query.return_value
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        
        # Test with zero values
        result = UserService.get_users_list(mock_db, skip=0, limit=0)
        assert result == []
        
        # Test with large values
        result = UserService.get_users_list(mock_db, skip=1000000, limit=1000000)
        mock_query.offset.assert_called_with(1000000)
        mock_query.limit.assert_called_with(1000000)


class TestIntegrationScenarios:
    """Test complete user management workflows."""
    
    def test_complete_user_lifecycle(self):
        """Test complete user lifecycle from creation to deletion."""
        mock_db = Mock(spec=Session)
        mock_user = MockUser(status=UserStatus.PENDING)
        mock_preferences = MockUserPreferences()
        
        # Step 1: Create user
        with patch.object(UserService, 'get_user_by_email') as mock_get_email, \
             patch('app.services.user_service.User') as mock_user_class, \
             patch('app.services.user_service.UserPreferences') as mock_prefs_class:
            
            mock_get_email.return_value = None
            mock_user_class.return_value = mock_user
            mock_prefs_class.return_value = mock_preferences
            mock_user.id = "user-123"
            
            user_data = UserCreate(email="lifecycle@example.com", name="Lifecycle User")
            created_user = UserService.create_user(mock_db, user_data)
            
            assert created_user.status == UserStatus.PENDING
        
        # Step 2: Approve user
        with patch.object(UserService, 'get_user_by_id') as mock_get_id:
            mock_get_id.return_value = mock_user
            
            approved_user = UserService.approve_user(mock_db, "user-123", "admin-456")
            
            assert approved_user.status == UserStatus.ACTIVE
        
        # Step 3: Update preferences
        with patch.object(UserService, 'get_user_preferences') as mock_get_prefs:
            mock_get_prefs.return_value = mock_preferences
            
            prefs_data = UserPreferencesUpdate(system_prompt="Custom prompt")
            updated_prefs = UserService.update_user_preferences(mock_db, "user-123", prefs_data)
            
            assert updated_prefs.system_prompt == "Custom prompt"
        
        # Step 4: Delete user
        with patch.object(UserService, 'get_user_by_id') as mock_get_id:
            mock_get_id.return_value = mock_user
            
            deleted = UserService.delete_user(mock_db, "user-123")
            
            assert deleted is True
    
    def test_admin_user_management_workflow(self):
        """Test admin operations workflow."""
        mock_db = Mock(spec=Session)
        
        # Get pending users
        pending_users = [MockUser(status=UserStatus.PENDING) for _ in range(3)]
        with patch.object(UserService, 'get_pending_users') as mock_pending:
            mock_pending.return_value = pending_users
            
            users_to_approve = UserService.get_pending_users(mock_db)
            assert len(users_to_approve) == 3
        
        # Approve each user
        for i, user in enumerate(pending_users):
            with patch.object(UserService, 'get_user_by_id') as mock_get:
                mock_get.return_value = user
                
                approved = UserService.approve_user(mock_db, f"user-{i}", "admin")
                assert approved.status == UserStatus.ACTIVE
        
        # Search for users
        with patch.object(UserService, 'search_users') as mock_search:
            mock_search.return_value = pending_users[:2]
            
            search_results = UserService.search_users(mock_db, "test")
            assert len(search_results) == 2
"""
Tests for Settings API endpoints
"""
import pytest
import uuid
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app

client = TestClient(app)

# Mock data
MOCK_USER = {
    "id": str(uuid.uuid4()),
    "email": "user@turfmapp.com",
    "name": "Test User",
    "role": "user", 
    "status": "active",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
    "last_login_at": "2024-01-01T00:00:00Z"
}

MOCK_PREFERENCES = {
    "id": str(uuid.uuid4()),
    "user_id": MOCK_USER["id"],
    "system_prompt": "You are a helpful assistant",
    "default_model": "gpt-4o",
    "settings": {"theme": "dark"},
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
}

@pytest.fixture
def auth_headers():
    """Mock headers for user authentication"""
    return {"Authorization": "Bearer mock_user_token"}


class TestUserProfile:
    """Test user profile endpoints"""
    
    @patch('app.api.v1.settings.get_current_user_supabase')
    def test_get_profile(self, mock_auth, auth_headers):
        """Test getting user profile"""
        mock_auth.return_value = MOCK_USER
        
        response = client.get("/api/v1/settings/profile", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "user@turfmapp.com"
        assert data["name"] == "Test User"
        assert data["role"] == "user"
        
    @patch('app.api.v1.settings.get_current_user_supabase')
    @patch('app.api.v1.settings.execute_query_one')
    def test_update_profile(self, mock_execute, mock_auth, auth_headers):
        """Test updating user profile"""
        updated_user = {**MOCK_USER, "name": "Updated Name"}
        mock_auth.return_value = MOCK_USER
        mock_execute.return_value = updated_user
        
        response = client.put(
            "/api/v1/settings/profile",
            headers=auth_headers,
            json={"name": "Updated Name"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        
    @patch('app.api.v1.settings.get_current_user_supabase')  
    def test_update_profile_filtered_fields(self, mock_auth, auth_headers):
        """Test that only allowed fields can be updated"""
        mock_auth.return_value = MOCK_USER
        
        # Try to update role (should be ignored)
        response = client.put(
            "/api/v1/settings/profile", 
            headers=auth_headers,
            json={"role": "admin", "name": "Valid Update"}
        )
        
        # Should still succeed but role change ignored
        assert response.status_code == 200


class TestUserPreferences:
    """Test user preferences endpoints"""
    
    @patch('app.api.v1.settings.get_current_user_supabase')
    @patch('app.api.v1.settings.execute_query_one')
    def test_get_preferences_existing(self, mock_execute, mock_auth, auth_headers):
        """Test getting existing user preferences"""
        mock_auth.return_value = MOCK_USER
        mock_execute.return_value = MOCK_PREFERENCES
        
        response = client.get("/api/v1/settings/preferences", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["system_prompt"] == "You are a helpful assistant"
        assert data["default_model"] == "gpt-4o"
        
    @patch('app.api.v1.settings.get_current_user_supabase')
    @patch('app.api.v1.settings.execute_query_one')
    def test_get_preferences_create_default(self, mock_execute, mock_auth, auth_headers):
        """Test creating default preferences when none exist"""
        mock_auth.return_value = MOCK_USER
        # First call returns None (no existing preferences)
        # Second call returns newly created preferences
        mock_execute.side_effect = [None, MOCK_PREFERENCES]
        
        response = client.get("/api/v1/settings/preferences", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "default_model" in data
        
    @patch('app.api.v1.settings.get_current_user_supabase')
    @patch('app.api.v1.settings.execute_query_one')
    def test_update_preferences_existing(self, mock_execute, mock_auth, auth_headers):
        """Test updating existing preferences"""
        mock_auth.return_value = MOCK_USER
        updated_preferences = {**MOCK_PREFERENCES, "system_prompt": "New prompt"}
        # First call checks existence, second call returns updated preferences  
        mock_execute.side_effect = [{"id": "existing"}, updated_preferences]
        
        response = client.put(
            "/api/v1/settings/preferences",
            headers=auth_headers,
            json={
                "system_prompt": "New prompt",
                "default_model": "gpt-5-mini"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["system_prompt"] == "New prompt"
        
    @patch('app.api.v1.settings.get_current_user_supabase')
    @patch('app.api.v1.settings.execute_query_one')
    def test_update_preferences_create_new(self, mock_execute, mock_auth, auth_headers):
        """Test creating new preferences when none exist"""
        mock_auth.return_value = MOCK_USER
        # First call returns None (no existing), second call returns new preferences
        mock_execute.side_effect = [None, MOCK_PREFERENCES]
        
        response = client.put(
            "/api/v1/settings/preferences",
            headers=auth_headers,
            json={
                "system_prompt": "You are a helpful assistant", 
                "default_model": "gpt-4o"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["system_prompt"] == "You are a helpful assistant"


class TestAccountDeletion:
    """Test account deletion endpoint"""
    
    @patch('app.api.v1.settings.get_current_user_supabase')
    @patch('app.api.v1.settings.execute_query')
    def test_delete_account(self, mock_execute, mock_auth, auth_headers):
        """Test deleting user account"""
        mock_auth.return_value = MOCK_USER
        mock_execute.return_value = None
        
        response = client.delete("/api/v1/settings/account", headers=auth_headers)
        
        assert response.status_code == 200
        assert response.json()["message"] == "Account deleted successfully"
        
    def test_delete_account_unauthenticated(self):
        """Test account deletion without authentication"""
        response = client.delete("/api/v1/settings/account")
        
        assert response.status_code == 403  # Should require authentication


class TestAuthenticationRequired:
    """Test that all settings endpoints require authentication"""
    
    def test_profile_requires_auth(self):
        """Test profile endpoint requires authentication"""
        response = client.get("/api/v1/settings/profile")
        assert response.status_code == 403
        
    def test_preferences_requires_auth(self):
        """Test preferences endpoint requires authentication"""
        response = client.get("/api/v1/settings/preferences")
        assert response.status_code == 403
        
    def test_update_profile_requires_auth(self):
        """Test profile update requires authentication"""
        response = client.put("/api/v1/settings/profile", json={"name": "Test"})
        assert response.status_code == 403


class TestErrorHandling:
    """Test error handling scenarios"""
    
    @patch('app.api.v1.settings.get_current_user_supabase')
    @patch('app.api.v1.settings.execute_query_one')
    def test_database_error_handling(self, mock_execute, mock_auth, auth_headers):
        """Test handling of database errors"""
        mock_auth.return_value = MOCK_USER
        mock_execute.side_effect = Exception("Database connection failed")
        
        response = client.get("/api/v1/settings/preferences", headers=auth_headers)
        
        assert response.status_code == 500
        assert "error" in response.json()["detail"].lower()


if __name__ == "__main__":
    pytest.main([__file__])
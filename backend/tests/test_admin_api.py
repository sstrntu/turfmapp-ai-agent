"""
Tests for Admin API endpoints
"""
import pytest
import uuid
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app

client = TestClient(app)

# Mock data
MOCK_ADMIN_USER = {
    "id": str(uuid.uuid4()),
    "email": "admin@turfmapp.com", 
    "name": "Admin User",
    "role": "super_admin",
    "status": "active",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
    "last_login_at": "2024-01-01T00:00:00Z"
}

MOCK_REGULAR_USER = {
    "id": str(uuid.uuid4()),
    "email": "user@turfmapp.com",
    "name": "Regular User", 
    "role": "user",
    "status": "active",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
    "last_login_at": "2024-01-01T00:00:00Z"
}

MOCK_USERS_LIST = [MOCK_ADMIN_USER, MOCK_REGULAR_USER]

@pytest.fixture
def admin_headers():
    """Mock headers for admin authentication"""
    return {"Authorization": "Bearer mock_admin_token"}

@pytest.fixture  
def user_headers():
    """Mock headers for regular user authentication"""
    return {"Authorization": "Bearer mock_user_token"}

class TestAdminStats:
    """Test admin statistics endpoints"""
    
    @patch('app.api.v1.admin.get_current_admin_user_supabase')
    @patch('app.api.v1.admin.execute_query_one')
    def test_get_admin_stats_success(self, mock_execute, mock_auth, admin_headers):
        """Test successful retrieval of admin statistics"""
        mock_auth.return_value = MOCK_ADMIN_USER
        
        # Mock database responses
        mock_execute.side_effect = [
            {"count": 150},  # total_users
            {"count": 5},    # pending_users
            {"count": 145},  # active_users
            {"count": 500},  # total_conversations
            {"count": 2500}, # total_messages
            {"count": 75},   # total_uploads
            {"count": 25},   # recent_users
            {"count": 120},  # recent_conversations
            {"count": 800},  # recent_messages
        ]
        
        response = client.get("/api/v1/admin/stats", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["users"]["total"] == 150
        assert data["users"]["pending"] == 5
        assert data["users"]["active"] == 145
        assert data["conversations"]["total"] == 500
        assert data["messages"]["total"] == 2500
        
    @patch('app.api.v1.admin.get_current_admin_user_supabase')
    def test_get_admin_stats_unauthorized(self, mock_auth, user_headers):
        """Test admin stats access denied for regular user"""
        mock_auth.side_effect = Exception("Admin privileges required")
        
        response = client.get("/api/v1/admin/stats", headers=user_headers)
        
        assert response.status_code == 403


class TestUserManagement:
    """Test user management endpoints"""
    
    @patch('app.api.v1.admin.get_current_admin_user_supabase')
    @patch('app.api.v1.admin.execute_query')
    def test_get_users_list(self, mock_execute, mock_auth, admin_headers):
        """Test getting list of users"""
        mock_auth.return_value = MOCK_ADMIN_USER
        mock_execute.return_value = [MOCK_ADMIN_USER, MOCK_REGULAR_USER]
        
        response = client.get("/api/v1/admin/users", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["email"] == "admin@turfmapp.com"
        assert data[1]["email"] == "user@turfmapp.com"
        
    @patch('app.api.v1.admin.get_current_admin_user_supabase') 
    @patch('app.api.v1.admin.execute_query')
    def test_get_pending_users(self, mock_execute, mock_auth, admin_headers):
        """Test getting pending users"""
        pending_user = {**MOCK_REGULAR_USER, "status": "pending"}
        mock_auth.return_value = MOCK_ADMIN_USER
        mock_execute.return_value = [pending_user]
        
        response = client.get("/api/v1/admin/users/pending", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "pending"
        
    @patch('app.api.v1.admin.get_current_admin_user_supabase')
    @patch('app.api.v1.admin.execute_query_one')  
    def test_update_user_role(self, mock_execute, mock_auth, admin_headers):
        """Test updating user role"""
        updated_user = {**MOCK_REGULAR_USER, "role": "admin"}
        mock_auth.return_value = MOCK_ADMIN_USER
        mock_execute.return_value = updated_user
        
        response = client.put(
            f"/api/v1/admin/users/{MOCK_REGULAR_USER['id']}", 
            headers=admin_headers,
            json={"role": "admin"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "admin"
        
    @patch('app.api.v1.admin.get_current_admin_user_supabase')
    def test_prevent_super_admin_by_regular_admin(self, mock_auth, admin_headers):
        """Test that regular admin cannot assign super_admin role"""
        regular_admin = {**MOCK_ADMIN_USER, "role": "admin"}
        mock_auth.return_value = regular_admin
        
        response = client.put(
            f"/api/v1/admin/users/{MOCK_REGULAR_USER['id']}", 
            headers=admin_headers,
            json={"role": "super_admin"}
        )
        
        assert response.status_code == 403
        assert "super admin" in response.json()["detail"].lower()
        
    @patch('app.api.v1.admin.get_current_admin_user_supabase')
    @patch('app.api.v1.admin.execute_query_one')
    def test_approve_user(self, mock_execute, mock_auth, admin_headers):
        """Test approving a pending user"""
        approved_user = {**MOCK_REGULAR_USER, "status": "active"}
        mock_auth.return_value = MOCK_ADMIN_USER
        mock_execute.return_value = approved_user
        
        response = client.post(
            f"/api/v1/admin/users/{MOCK_REGULAR_USER['id']}/approve",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"
        
    @patch('app.api.v1.admin.get_current_admin_user_supabase')
    def test_prevent_self_deletion(self, mock_auth, admin_headers):
        """Test that admin cannot delete their own account"""
        mock_auth.return_value = MOCK_ADMIN_USER
        
        response = client.delete(
            f"/api/v1/admin/users/{MOCK_ADMIN_USER['id']}",
            headers=admin_headers
        )
        
        assert response.status_code == 400
        assert "own account" in response.json()["detail"].lower()


class TestAnnouncementManagement:
    """Test announcement management endpoints"""
    
    @patch('app.api.v1.admin.execute_query')
    def test_get_active_announcements_public(self, mock_execute):
        """Test public access to active announcements"""
        mock_announcement = {
            "id": str(uuid.uuid4()),
            "created_by": MOCK_ADMIN_USER["id"],
            "content": "Welcome to TURFMAPP!",
            "expires_at": None,
            "is_active": True,
            "created_at": "2024-01-01T00:00:00Z"
        }
        mock_execute.return_value = [mock_announcement]
        
        # No authentication headers needed for public endpoint
        response = client.get("/api/v1/admin/announcements/active")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["content"] == "Welcome to TURFMAPP!"
        
    @patch('app.api.v1.admin.get_current_admin_user_supabase')
    @patch('app.api.v1.admin.execute_query_one')
    def test_create_announcement(self, mock_execute, mock_auth, admin_headers):
        """Test creating new announcement"""
        mock_auth.return_value = MOCK_ADMIN_USER
        new_announcement = {
            "id": str(uuid.uuid4()),
            "created_by": MOCK_ADMIN_USER["id"],
            "content": "System maintenance tonight",
            "expires_at": "2024-12-31T23:59:59Z",
            "is_active": True,
            "created_at": "2024-01-01T00:00:00Z"
        }
        mock_execute.return_value = new_announcement
        
        response = client.post(
            "/api/v1/admin/announcements",
            headers=admin_headers,
            json={
                "content": "System maintenance tonight",
                "expires_at": "2024-12-31T23:59:59Z"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "System maintenance tonight"
        
    @patch('app.api.v1.admin.get_current_admin_user_supabase')
    @patch('app.api.v1.admin.execute_query')
    def test_delete_announcement(self, mock_execute, mock_auth, admin_headers):
        """Test deleting announcement"""
        mock_auth.return_value = MOCK_ADMIN_USER
        mock_execute.return_value = None
        
        announcement_id = str(uuid.uuid4())
        response = client.delete(
            f"/api/v1/admin/announcements/{announcement_id}",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        assert response.json()["message"] == "Announcement deleted successfully"


if __name__ == "__main__":
    pytest.main([__file__])
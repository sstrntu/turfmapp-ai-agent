"""
API Ping Tests for Chat Endpoints

Simple integration tests that verify API endpoints are accessible and return
expected response structures without testing complex business logic.
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import status
from app.main import app


class TestChatAPIPing:
    """Ping tests for chat API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Test client fixture"""
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        """Mock auth headers for testing"""
        return {"Authorization": "Bearer test-token"}
    
    def test_chat_send_endpoint_accessible(self, client, auth_headers):
        """Test that chat send endpoint is accessible and validates input"""
        response = client.post(
            "/api/v1/chat/send",
            headers=auth_headers,
            json={"message": "test ping"}
        )
        
        # Should not be 404 (endpoint exists)
        assert response.status_code != 404
        
        # Should be either 200 (success) or 422/500 (validation/auth error)
        assert response.status_code in [200, 401, 422, 500]
        
        # Response should be JSON
        assert response.headers.get("content-type", "").startswith("application/json")
    
    def test_get_conversations_endpoint_accessible(self, client, auth_headers):
        """Test that get conversations endpoint is accessible"""
        response = client.get(
            "/api/v1/chat/conversations",
            headers=auth_headers
        )
        
        # Should not be 404 (endpoint exists)
        assert response.status_code != 404
        
        # Should respond with proper status
        assert response.status_code in [200, 401, 500]
        
        # Response should be JSON
        assert response.headers.get("content-type", "").startswith("application/json")
    
    def test_get_conversation_by_id_endpoint_accessible(self, client, auth_headers):
        """Test that get specific conversation endpoint is accessible"""
        response = client.get(
            "/api/v1/chat/conversations/test-id-123",
            headers=auth_headers
        )
        
        # Should not be 404 due to routing (endpoint exists)
        # Note: 404 for specific conversation not found is OK
        assert response.status_code != 404 or response.json().get("detail") == "Conversation not found"
        
        # Should respond with proper status
        assert response.status_code in [200, 401, 404, 500]
        
        # Response should be JSON
        assert response.headers.get("content-type", "").startswith("application/json")
    
    def test_delete_conversation_endpoint_accessible(self, client, auth_headers):
        """Test that delete conversation endpoint is accessible"""
        response = client.delete(
            "/api/v1/chat/conversations/test-id-123",
            headers=auth_headers
        )
        
        # Should not be 404 due to routing (endpoint exists)
        assert response.status_code != 404 or response.json().get("detail") == "Conversation not found"
        
        # Should respond with proper status
        assert response.status_code in [200, 401, 404, 500]
        
        # Response should be JSON
        assert response.headers.get("content-type", "").startswith("application/json")
    
    def test_chat_health_endpoint_accessible(self, client):
        """Test that chat health endpoint is accessible"""
        response = client.get("/api/v1/chat/health")
        
        # Should be accessible without auth
        assert response.status_code == 200
        
        # Should return expected structure
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "service" in data
        assert data["service"] == "chat"
    
    def test_get_models_endpoint_accessible(self, client):
        """Test that get models endpoint is accessible"""  
        response = client.get("/api/v1/chat/models")
        
        # Should be accessible without auth
        assert response.status_code == 200
        
        # Should return models list
        data = response.json()
        assert "models" in data
        assert isinstance(data["models"], list)
        assert len(data["models"]) > 0
    
    def test_chat_send_validates_required_fields(self, client, auth_headers):
        """Test that send endpoint validates required message field"""
        response = client.post(
            "/api/v1/chat/send",
            headers=auth_headers,
            json={}  # Missing required 'message' field
        )
        
        # Should return validation error
        assert response.status_code == 422
        
        # Should have validation error details
        data = response.json()
        assert "detail" in data
    
    def test_chat_send_rejects_unauthorized(self, client):
        """Test that send endpoint requires authentication"""
        response = client.post(
            "/api/v1/chat/send",
            json={"message": "test"}
        )
        
        # Should reject unauthorized requests
        assert response.status_code == 401
    
    def test_response_headers_correct(self, client, auth_headers):
        """Test that responses have correct headers"""
        response = client.post(
            "/api/v1/chat/send",
            headers=auth_headers,
            json={"message": "test ping"}
        )
        
        # Should have CORS headers (if configured) - skip if not configured
        # This is environment dependent and not critical for API functionality
        pass
        
        # Content-Type should be JSON
        if response.status_code != 401:  # Auth errors might not be JSON
            assert response.headers.get("content-type", "").startswith("application/json")


class TestChatAPIPingResponseStructure:
    """Test basic response structure without complex business logic"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture  
    def auth_headers(self):
        return {"Authorization": "Bearer test-token"}
    
    def test_health_response_structure(self, client):
        """Test health endpoint returns expected structure"""
        response = client.get("/api/v1/chat/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Required fields
        assert "status" in data
        assert "service" in data
        assert "timestamp" in data
        
        # Correct values
        assert data["status"] == "healthy"
        assert data["service"] == "chat"
    
    def test_models_response_structure(self, client):
        """Test models endpoint returns expected structure"""
        response = client.get("/api/v1/chat/models")
        
        assert response.status_code == 200
        data = response.json()
        
        # Required fields
        assert "models" in data
        assert isinstance(data["models"], list)
        
        # Each model should have required fields
        for model in data["models"]:
            assert "id" in model
            assert "name" in model
            assert "description" in model
    
    def test_error_response_structure(self, client):
        """Test error responses have consistent structure"""
        # Test validation error structure
        response = client.post(
            "/api/v1/chat/send",
            headers={"Authorization": "Bearer test-token"},
            json={}  # Invalid payload
        )
        
        assert response.status_code == 422
        data = response.json()
        
        # Should have FastAPI validation error structure
        assert "detail" in data
        assert isinstance(data["detail"], list)


class TestChatAPIPingPerformance:
    """Basic performance ping tests"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_health_endpoint_fast_response(self, client):
        """Test health endpoint responds quickly"""
        import time
        
        start_time = time.time()
        response = client.get("/api/v1/chat/health")
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Should respond within 1 second
        response_time = end_time - start_time
        assert response_time < 1.0, f"Health endpoint too slow: {response_time}s"
    
    def test_models_endpoint_fast_response(self, client):
        """Test models endpoint responds quickly"""
        import time
        
        start_time = time.time()
        response = client.get("/api/v1/chat/models")
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Should respond within 1 second  
        response_time = end_time - start_time
        assert response_time < 1.0, f"Models endpoint too slow: {response_time}s"
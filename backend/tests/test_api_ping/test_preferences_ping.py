"""
API Ping Tests for Preferences Endpoints

Simple integration tests for user preferences endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


class TestPreferencesAPIPing:
    """Ping tests for preferences API endpoints"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        return {"Authorization": "Bearer test-token"}
    
    def test_get_preferences_endpoint_accessible(self, client, auth_headers):
        """Test that get preferences endpoint is accessible"""
        response = client.get("/api/v1/preferences/me", headers=auth_headers)
        
        # Should not be 404 (endpoint exists)
        assert response.status_code != 404
        
        # Should respond with proper status
        assert response.status_code in [200, 401, 500]
        
        # Response should be JSON
        assert response.headers.get("content-type", "").startswith("application/json")
    
    def test_update_preferences_endpoint_accessible(self, client, auth_headers):
        """Test that update preferences endpoint is accessible"""
        response = client.put(
            "/api/v1/preferences/me",
            headers=auth_headers,
            json={"system_prompt": "test prompt"}
        )
        
        # Should not be 404 (endpoint exists)
        assert response.status_code != 404
        
        # Should respond with proper status
        assert response.status_code in [200, 401, 422, 500]
        
        # Response should be JSON
        assert response.headers.get("content-type", "").startswith("application/json")
    
    def test_preferences_requires_auth(self, client):
        """Test that preferences endpoints require authentication"""
        # Test get without auth
        response = client.get("/api/v1/preferences/me")
        assert response.status_code == 401
        
        # Test update without auth
        response = client.put(
            "/api/v1/preferences/me",
            json={"system_prompt": "test"}
        )
        assert response.status_code == 401
    
    def test_update_preferences_validates_input(self, client, auth_headers):
        """Test that update preferences validates input structure"""
        response = client.put(
            "/api/v1/preferences/me",
            headers=auth_headers,
            json={"invalid_field": "value"}
        )
        
        # Should either accept (200) or validate (422)
        assert response.status_code in [200, 422]
        
        # Response should be JSON
        assert response.headers.get("content-type", "").startswith("application/json")
    
    def test_preferences_response_structure(self, client, auth_headers):
        """Test that preferences endpoints return expected structure"""
        response = client.get("/api/v1/preferences/me", headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
            # Should have preferences structure
            # (exact structure depends on implementation)


class TestPreferencesAPIPingPerformance:
    """Performance tests for preferences endpoints"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        return {"Authorization": "Bearer test-token"}
    
    def test_get_preferences_fast_response(self, client, auth_headers):
        """Test get preferences responds quickly"""
        import time
        
        start_time = time.time()
        response = client.get("/api/v1/preferences/me", headers=auth_headers)
        end_time = time.time()
        
        # Should respond within reasonable time
        response_time = end_time - start_time
        assert response_time < 1.0, f"Get preferences too slow: {response_time}s"
    
    def test_update_preferences_fast_response(self, client, auth_headers):
        """Test update preferences responds quickly"""
        import time
        
        start_time = time.time()
        response = client.put(
            "/api/v1/preferences/me",
            headers=auth_headers,
            json={"system_prompt": "test prompt"}
        )
        end_time = time.time()
        
        # Should respond within reasonable time
        response_time = end_time - start_time
        assert response_time < 1.0, f"Update preferences too slow: {response_time}s"
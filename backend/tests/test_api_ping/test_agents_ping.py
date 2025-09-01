"""
API Ping Tests for Agent Endpoints

Simple integration tests for the agent routing system endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import status
from app.main import app


class TestAgentAPIPing:
    """Ping tests for agent API endpoints"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        return {"Authorization": "Bearer test-token"}
    
    def test_agent_health_endpoint_accessible(self, client):
        """Test agent health endpoint is accessible"""
        response = client.get("/api/v1/agents/health")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "service" in data
        assert data["service"] == "agent_routing"
    
    def test_routing_config_endpoint_accessible(self, client, auth_headers):
        """Test routing config endpoint is accessible"""
        response = client.get("/api/v1/agents/config", headers=auth_headers)
        
        # Should not be 404 (endpoint exists)
        assert response.status_code != 404
        
        # Should respond with proper status
        assert response.status_code in [200, 401, 500]
        
        # Response should be JSON
        assert response.headers.get("content-type", "").startswith("application/json")
    
    def test_agent_stats_endpoint_accessible(self, client, auth_headers):
        """Test agent stats endpoint is accessible"""
        response = client.get("/api/v1/agents/stats", headers=auth_headers)
        
        # Should not be 404 (endpoint exists)
        assert response.status_code != 404
        
        # Should respond with proper status  
        assert response.status_code in [200, 401, 500]
        
        # Response should be JSON
        assert response.headers.get("content-type", "").startswith("application/json")
    
    def test_routing_analyze_endpoint_accessible(self, client, auth_headers):
        """Test routing analysis endpoint is accessible"""
        response = client.post(
            "/api/v1/agents/routing/analyze",
            headers=auth_headers,
            json={"question": "What is the weather today?"}
        )
        
        # Should not be 404 (endpoint exists)
        assert response.status_code != 404
        
        # Should respond with proper status
        assert response.status_code in [200, 401, 422, 500]
        
        # Response should be JSON
        assert response.headers.get("content-type", "").startswith("application/json")
    
    def test_routing_analyze_validates_input(self, client, auth_headers):
        """Test routing analysis validates required fields"""
        response = client.post(
            "/api/v1/agents/routing/analyze",
            headers=auth_headers,
            json={}  # Missing required 'question' field
        )
        
        # Should return validation error
        assert response.status_code == 422
        
        # Should have validation error details
        data = response.json()
        assert "detail" in data
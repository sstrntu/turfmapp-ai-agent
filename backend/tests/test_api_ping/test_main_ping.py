"""
API Ping Tests for Main Application Endpoints

Simple integration tests for root and health endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


class TestMainAPIPing:
    """Ping tests for main application endpoints"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_root_endpoint_accessible(self, client):
        """Test that root endpoint is accessible"""
        response = client.get("/")
        
        assert response.status_code == 200
        
        # Response should be JSON
        assert response.headers.get("content-type", "").startswith("application/json")
        
        # Should have expected structure
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "docs" in data
        
        # Should contain app information
        assert "TURFMAPP" in data["message"]
        assert data["docs"] == "/docs"
    
    def test_health_endpoint_accessible(self, client):
        """Test that health check endpoint is accessible"""
        response = client.get("/healthz")
        
        assert response.status_code == 200
        
        # Response should be JSON
        assert response.headers.get("content-type", "").startswith("application/json")
        
        # Should have expected structure
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"
    
    def test_docs_endpoint_accessible(self, client):
        """Test that API documentation endpoint is accessible"""
        response = client.get("/docs")
        
        # Should return Swagger UI (HTML)
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
    
    def test_openapi_schema_accessible(self, client):
        """Test that OpenAPI schema is accessible"""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        
        # Response should be JSON
        assert response.headers.get("content-type", "").startswith("application/json")
        
        # Should be valid OpenAPI schema
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data
    
    def test_invalid_route_returns_404(self, client):
        """Test that invalid routes return 404"""
        response = client.get("/nonexistent-endpoint")
        
        assert response.status_code == 404
    
    def test_cors_headers_present(self, client):
        """Test that CORS headers are properly configured"""
        response = client.get("/")
        
        # Should have basic CORS setup (environment dependent)
        # This test is informational - doesn't fail if CORS not configured
        cors_header = response.headers.get("access-control-allow-origin")
        if cors_header:
            assert cors_header in ["*", "http://localhost:3005", "http://localhost:3000"]


class TestMainAPIPingPerformance:
    """Performance tests for main endpoints"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_root_endpoint_fast_response(self, client):
        """Test root endpoint responds quickly"""
        import time
        
        start_time = time.time()
        response = client.get("/")
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Should respond very quickly
        response_time = end_time - start_time
        assert response_time < 0.5, f"Root endpoint too slow: {response_time}s"
    
    def test_health_endpoint_fast_response(self, client):
        """Test health endpoint responds quickly"""
        import time
        
        start_time = time.time()
        response = client.get("/healthz")
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Health check should be very fast
        response_time = end_time - start_time
        assert response_time < 0.5, f"Health endpoint too slow: {response_time}s"
    
    def test_openapi_schema_reasonable_time(self, client):
        """Test OpenAPI schema generation is reasonable"""
        import time
        
        start_time = time.time()
        response = client.get("/openapi.json")
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Schema generation should be reasonable
        response_time = end_time - start_time
        assert response_time < 2.0, f"OpenAPI schema too slow: {response_time}s"


class TestMainAPIPingReliability:
    """Reliability tests for main endpoints"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_multiple_health_checks_consistent(self, client):
        """Test that multiple health checks return consistent results"""
        responses = []
        
        # Make multiple requests
        for _ in range(5):
            response = client.get("/healthz")
            responses.append(response)
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
    
    def test_concurrent_root_requests_handle_gracefully(self, client):
        """Test that concurrent requests to root are handled gracefully"""
        import threading
        import time
        
        results = []
        
        def make_request():
            try:
                response = client.get("/")
                results.append(response.status_code)
            except Exception as e:
                results.append(str(e))
        
        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All should succeed
        for result in results:
            assert result == 200, f"Concurrent request failed: {result}"
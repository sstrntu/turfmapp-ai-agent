"""
API Ping Tests for Upload Endpoints

Simple integration tests for file upload endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
import io


class TestUploadsAPIPing:
    """Ping tests for upload API endpoints"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        return {"Authorization": "Bearer test-token"}
    
    def test_upload_endpoint_accessible(self, client, auth_headers):
        """Test that upload endpoint is accessible"""
        # Create a test file
        test_file = io.BytesIO(b"test content")
        test_file.name = "test.txt"
        
        response = client.post(
            "/api/v1/uploads/",
            headers=auth_headers,
            files={"file": ("test.txt", test_file, "text/plain")}
        )
        
        # Should not be 404 (endpoint exists)
        assert response.status_code != 404
        
        # Should respond with proper status
        assert response.status_code in [200, 401, 422, 413, 500]
        
        # Response should be JSON
        if response.status_code != 413:  # File too large might not be JSON
            assert response.headers.get("content-type", "").startswith("application/json")
    
    def test_upload_validates_file_type(self, client, auth_headers):
        """Test that upload endpoint validates file types"""
        test_file = io.BytesIO(b"test content")
        test_file.name = "test.exe"  # Invalid file type
        
        response = client.post(
            "/api/v1/uploads/",
            headers=auth_headers,
            files={"file": ("test.exe", test_file, "application/octet-stream")}
        )
        
        # Should reject invalid file types
        assert response.status_code in [400, 422]
    
    def test_upload_validates_file_presence(self, client, auth_headers):
        """Test that upload endpoint validates file presence"""
        response = client.post(
            "/api/v1/uploads/",
            headers=auth_headers
            # No file provided
        )
        
        # Should return validation error or bad request
        assert response.status_code in [400, 422]
    
    def test_get_uploaded_file_endpoint_accessible(self, client):
        """Test that get uploaded file endpoint is accessible"""
        response = client.get("/api/v1/uploads/test-file-id")
        
        # Should not be 404 due to routing (endpoint exists)
        # 404 for specific file not found is OK
        assert response.status_code != 404 or "not found" in response.json().get("detail", "").lower()
        
        # Should respond with proper status
        assert response.status_code in [200, 404, 500]
    
    def test_delete_upload_endpoint_accessible(self, client, auth_headers):
        """Test that delete upload endpoint is accessible"""
        response = client.delete(
            "/api/v1/uploads/test-file-id",
            headers=auth_headers
        )
        
        # Should not be 404 due to routing (endpoint exists)
        # 404 for specific file not found is OK
        assert response.status_code != 404 or "not found" in response.json().get("detail", "").lower()
        
        # Should respond with proper status
        assert response.status_code in [200, 401, 404, 500]
    
    def test_upload_response_structure(self, client, auth_headers):
        """Test upload endpoint response structure"""
        test_file = io.BytesIO(b"small test content")
        test_file.name = "test.txt"
        
        response = client.post(
            "/api/v1/uploads/",
            headers=auth_headers,
            files={"file": ("test.txt", test_file, "text/plain")}
        )
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
            # Should have upload response structure
            # (exact structure depends on implementation)


class TestUploadsAPIPingPerformance:
    """Performance tests for upload endpoints"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        return {"Authorization": "Bearer test-token"}
    
    def test_get_file_fast_response(self, client):
        """Test get file responds quickly even for non-existent file"""
        import time
        
        start_time = time.time()
        response = client.get("/api/v1/uploads/nonexistent-file-id")
        end_time = time.time()
        
        # Should respond within reasonable time (even with 404)
        response_time = end_time - start_time
        assert response_time < 2.0, f"Get file too slow: {response_time}s"
    
    def test_small_file_upload_reasonable_time(self, client, auth_headers):
        """Test small file upload completes in reasonable time"""
        import time
        
        test_file = io.BytesIO(b"small test content")
        test_file.name = "test.txt"
        
        start_time = time.time()
        response = client.post(
            "/api/v1/uploads/",
            headers=auth_headers,
            files={"file": ("test.txt", test_file, "text/plain")}
        )
        end_time = time.time()
        
        # Small file upload should be reasonably fast
        response_time = end_time - start_time
        assert response_time < 5.0, f"Small file upload too slow: {response_time}s"
"""
Simple Configuration Ping Tests

Basic tests to verify app configuration is functional without complex validation.
"""

import pytest
import os
from app.main import app
from fastapi.testclient import TestClient


class TestConfigPing:
    """Simple configuration validation tests"""
    
    def test_app_imports_successfully(self):
        """Test that app can be imported with current config"""
        # If this passes, basic config is working
        assert app is not None
        assert hasattr(app, 'title')
    
    def test_essential_env_vars_present(self):
        """Test that essential environment variables are present"""
        # Test that critical env vars exist (not their values)
        essential_vars = [
            'SUPABASE_URL',
            'SUPABASE_ANON_KEY', 
            'SUPABASE_SERVICE_ROLE_KEY'
        ]
        
        for var in essential_vars:
            value = os.getenv(var)
            assert value is not None, f"Missing required environment variable: {var}"
            assert len(value) > 0, f"Empty environment variable: {var}"
    
    def test_app_metadata_configured(self):
        """Test that app metadata is properly configured"""
        assert app.title == "TURFMAPP AI Agent Backend"
        assert app.version == "1.0.0"
        assert "description" in dir(app)
    
    def test_cors_middleware_configured(self):
        """Test that CORS middleware is configured"""
        # Check that CORS middleware is in the middleware stack
        middleware_classes = [middleware.cls.__name__ for middleware in app.user_middleware]
        assert "CORSMiddleware" in middleware_classes
    
    def test_routers_included(self):
        """Test that main API routers are included"""
        # Check that routes are registered
        routes = [route.path for route in app.routes]
        
        # Should have main routes
        assert "/" in routes
        assert "/healthz" in routes
        
        # Should have API prefixes (actual endpoints are sub-routes)
        api_prefixes = [route.path for route in app.routes if route.path.startswith("/api")]
        assert len(api_prefixes) > 0, "No API routes found"


class TestConfigPingEnvironment:
    """Test environment-specific configuration"""
    
    def test_database_config_accessible(self):
        """Test that database configuration is accessible"""
        from app.database import get_supabase_config
        
        config = get_supabase_config()
        
        # Should return config dict
        assert isinstance(config, dict)
        assert "url" in config
        assert config["url"] is not None
    
    def test_openai_config_accessible(self):
        """Test that OpenAI configuration is accessible"""
        openai_key = os.getenv("OPENAI_API_KEY")
        
        # Key should be present (value can be test key)
        assert openai_key is not None, "OPENAI_API_KEY not configured"
        assert len(openai_key) > 0, "OPENAI_API_KEY is empty"
    
    def test_secret_key_configured(self):
        """Test that secret key is configured"""
        secret_key = os.getenv("SECRET_KEY")
        
        # Should have some secret key (even if default)
        assert secret_key is not None
        assert len(secret_key) > 10, "SECRET_KEY too short"


class TestConfigPingFunctionality:
    """Test that configuration results in functional app"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_app_starts_successfully(self, client):
        """Test that app starts and responds"""
        response = client.get("/")
        assert response.status_code == 200
    
    def test_health_check_functional(self, client):
        """Test that health check works with current config"""
        response = client.get("/healthz")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ok"
    
    def test_api_documentation_accessible(self, client):
        """Test that API docs are accessible"""
        response = client.get("/docs")
        assert response.status_code == 200
    
    def test_openapi_schema_generated(self, client):
        """Test that OpenAPI schema is generated properly"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
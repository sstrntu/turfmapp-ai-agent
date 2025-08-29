"""
TURFMAPP Test Configuration and Fixtures

Provides common test fixtures and configuration for comprehensive test coverage.
Following code.md standards with proper type hints and docstrings.
"""

from __future__ import annotations

import os
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import Generator, Dict, Any, List
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import app as main_app


@pytest.fixture
def app() -> FastAPI:
    """Get FastAPI application instance for testing."""
    return main_app


@pytest.fixture
def client(app: FastAPI) -> Generator[TestClient, None, None]:
    """Get test client for FastAPI application."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_supabase_client() -> Mock:
    """Mock Supabase client for testing."""
    mock_client = Mock()
    mock_client.auth = Mock()
    mock_client.table = Mock()
    return mock_client


@pytest.fixture
def mock_user_data() -> Dict[str, Any]:
    """Create mock user data for testing."""
    return {
        "id": "test-user-id",
        "email": "test@example.com",
        "name": "Test User",
        "role": "user",
        "status": "active",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "last_login_at": datetime.utcnow().isoformat()
    }


@pytest.fixture
def mock_admin_user_data() -> Dict[str, Any]:
    """Create mock admin user data for testing."""
    return {
        "id": "admin-user-id",
        "email": "admin@example.com", 
        "name": "Admin User",
        "role": "admin",
        "status": "active",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "last_login_at": datetime.utcnow().isoformat()
    }


@pytest.fixture
def mock_conversation_data() -> Dict[str, Any]:
    """Create mock conversation data for testing."""
    return {
        "id": "test-conversation-id",
        "user_id": "test-user-id",
        "title": "Test Conversation",
        "system_prompt": "You are a helpful assistant.",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }


@pytest.fixture
def mock_message_data() -> Dict[str, Any]:
    """Create mock message data for testing."""
    return {
        "id": "test-message-id",
        "conversation_id": "test-conversation-id",
        "role": "user",
        "content": "Test message content",
        "metadata": {},
        "created_at": datetime.utcnow().isoformat()
    }


@pytest.fixture
def mock_public_user_data() -> Dict[str, Any]:
    """Create mock public user data for testing."""
    return {
        "id": "test-user-id",
        "email": "test@example.com",
        "name": "Test User",
        "avatar_url": "https://example.com/avatar.jpg"
    }


@pytest.fixture
def mock_env_vars(monkeypatch: pytest.MonkeyPatch) -> Dict[str, str]:
    """Set up mock environment variables for testing."""
    env_vars = {
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_ANON_KEY": "test-anon-key",
        "SUPABASE_SERVICE_ROLE_KEY": "test-service-key",
        "OPENAI_API_KEY": "test-openai-key",
        "OPENAI_MODEL": "gpt-4o-mini",
        "DATABASE_URL": "postgresql://test:test@localhost:5432/test_db",
        "SECRET_KEY": "test-secret-key-for-sessions",
        "FAL_API_KEY": "test-fal-key"
    }
    
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    
    return env_vars


@pytest.fixture
def mock_httpx_client() -> Mock:
    """Mock httpx AsyncClient for HTTP requests."""
    mock_client = AsyncMock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"success": True}
    mock_response.text = "Success response"
    mock_client.get.return_value = mock_response
    mock_client.post.return_value = mock_response
    mock_client.put.return_value = mock_response
    mock_client.delete.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    return mock_client


@pytest.fixture
def mock_openai_response() -> Dict[str, Any]:
    """Mock OpenAI API response."""
    return {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": "This is a test response from the AI assistant."
            }
        }],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 12,
            "total_tokens": 22
        }
    }


@pytest.fixture
def mock_supabase_user_response() -> Dict[str, Any]:
    """Mock Supabase user response."""
    return {
        "id": "test-user-id",
        "email": "test@example.com",
        "user_metadata": {
            "full_name": "Test User",
            "avatar_url": "https://example.com/avatar.jpg"
        }
    }


@pytest.fixture
def mock_auth_header() -> Dict[str, str]:
    """Mock authorization header for authenticated requests."""
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
def sample_conversations() -> List[Dict[str, Any]]:
    """Sample conversations data for testing."""
    return [
        {
            "id": "conv-1",
            "user_id": "test-user-id",
            "title": "First Conversation",
            "created_at": datetime.utcnow() - timedelta(days=1),
            "updated_at": datetime.utcnow() - timedelta(hours=2),
            "message_count": 5
        },
        {
            "id": "conv-2", 
            "user_id": "test-user-id",
            "title": "Second Conversation",
            "created_at": datetime.utcnow() - timedelta(hours=12),
            "updated_at": datetime.utcnow() - timedelta(hours=1),
            "message_count": 3
        }
    ]


@pytest.fixture
def sample_messages() -> List[Dict[str, Any]]:
    """Sample messages data for testing."""
    return [
        {
            "id": "msg-1",
            "conversation_id": "test-conversation-id",
            "role": "user",
            "content": "Hello, how are you?",
            "created_at": datetime.utcnow() - timedelta(minutes=10)
        },
        {
            "id": "msg-2",
            "conversation_id": "test-conversation-id", 
            "role": "assistant",
            "content": "I'm doing well, thank you! How can I help you today?",
            "created_at": datetime.utcnow() - timedelta(minutes=9)
        },
        {
            "id": "msg-3",
            "conversation_id": "test-conversation-id",
            "role": "user", 
            "content": "Can you help me with Python programming?",
            "created_at": datetime.utcnow() - timedelta(minutes=8)
        }
    ]


# Auto-use fixtures for common setup
@pytest.fixture(autouse=True)
def setup_test_environment(mock_env_vars: Dict[str, str], monkeypatch: pytest.MonkeyPatch) -> None:
    """Automatically set up test environment for all tests."""
    # Set testing flag to prevent database connections
    monkeypatch.setenv("TESTING", "true")
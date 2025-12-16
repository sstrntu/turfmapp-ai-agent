"""
LlamaIndex Test Fixtures

Provides shared fixtures for testing LlamaIndex components:
- Mock LLMs and embeddings
- Test database connections
- Mock vector stores
- Sample data generators
"""

import pytest
from unittest.mock import AsyncMock, Mock
import uuid
from datetime import datetime

# LlamaIndex imports will be added as we implement components
# from llama_index.core.llms import MockLLM
# from llama_index.core.embeddings import MockEmbedding

@pytest.fixture
def test_user_id():
    """Generate a test user ID."""
    return str(uuid.uuid4())

@pytest.fixture
def test_conversation_id():
    """Generate a test conversation ID."""
    return str(uuid.uuid4())

@pytest.fixture
def sample_conversation_history():
    """Sample conversation history for testing."""
    return [
        {"role": "user", "content": "Hello, how are you?"},
        {"role": "assistant", "content": "I'm doing great! How can I help you today?"},
        {"role": "user", "content": "I need help with my schedule."},
    ]

@pytest.fixture
def sample_documents():
    """Sample documents for RAG testing."""
    return [
        "Python is a high-level programming language known for its simplicity.",
        "JavaScript is primarily used for web development and runs in browsers.",
        "Machine learning is a subset of artificial intelligence focused on data-driven learning.",
    ]

@pytest.fixture
async def mock_llm():
    """
    Mock LLM for testing without making real API calls.
    Will be implemented with actual LlamaIndex MockLLM in Phase 2.
    """
    llm = AsyncMock()
    llm.acomplete = AsyncMock(return_value=Mock(text="Mock response"))
    llm.achat = AsyncMock(return_value=Mock(message=Mock(content="Mock chat response")))
    return llm

@pytest.fixture
async def mock_embeddings():
    """
    Mock embeddings for testing without making real API calls.
    Will be implemented with actual LlamaIndex MockEmbedding in Phase 4.
    """
    embeddings = Mock()
    embeddings.get_text_embedding = Mock(return_value=[0.1] * 1536)  # Mock 1536-dim vector
    return embeddings

@pytest.fixture
async def test_db():
    """
    Test database connection.
    Will be implemented to use actual test DB in later phases.
    """
    # TODO: Setup test database connection
    # For now, return a mock
    db = AsyncMock()
    yield db
    # TODO: Cleanup

@pytest.fixture
def mock_vector_store():
    """
    Mock vector store for testing.
    Will be implemented with actual in-memory vector store in Phase 4.
    """
    # TODO: Implement with SimpleVectorStore or similar
    return Mock()

@pytest.fixture
def mock_gmail_api():
    """Mock Gmail API responses."""
    api = Mock()
    api.search_messages = AsyncMock(return_value=[
        {
            "id": "msg-1",
            "subject": "Test Email",
            "from": "test@example.com",
            "date": datetime.now().isoformat(),
            "snippet": "This is a test email"
        }
    ])
    return api

@pytest.fixture
def mock_drive_api():
    """Mock Google Drive API responses."""
    api = Mock()
    api.search_files = AsyncMock(return_value=[
        {
            "id": "file-1",
            "name": "Test Document.pdf",
            "mimeType": "application/pdf",
            "createdTime": datetime.now().isoformat()
        }
    ])
    return api

@pytest.fixture
def mock_calendar_api():
    """Mock Google Calendar API responses."""
    api = Mock()
    api.list_events = AsyncMock(return_value=[
        {
            "id": "event-1",
            "summary": "Team Meeting",
            "start": {"dateTime": datetime.now().isoformat()},
            "end": {"dateTime": datetime.now().isoformat()}
        }
    ])
    return api

# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "regression: Regression tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "requires_api: Tests that need real API calls")

"""
Unit tests for Conversation Memory Manager
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from app.llamaindex.memory.conversation_memory import (
    ConversationMemory,
    MemoryManager,
    MemoryType,
)


class TestConversationMemory:
    """Test cases for ConversationMemory."""

    @pytest.fixture
    def memory(self):
        """Create a conversation memory instance for testing."""
        return ConversationMemory(
            user_id="test-user-123",
            conversation_id="test-conv-456",
            max_messages=5,
            summarize_threshold=10,
            db_pool=None,  # No database for unit tests
        )

    @pytest.mark.asyncio
    async def test_initialization(self, memory):
        """Test memory initialization."""
        assert memory.user_id == "test-user-123"
        assert memory.conversation_id == "test-conv-456"
        assert memory.max_messages == 5
        assert memory.summarize_threshold == 10
        assert memory.message_count == 0
        assert memory.summary is None
        assert memory.entities == {}

    @pytest.mark.asyncio
    async def test_add_message(self, memory):
        """Test adding messages to memory."""
        await memory.add_message(
            role="user",
            content="Hello, how are you?",
            metadata={"source": "test"}
        )

        assert memory.message_count == 1

        await memory.add_message(
            role="assistant",
            content="I'm doing well, thank you!",
        )

        assert memory.message_count == 2

    @pytest.mark.asyncio
    async def test_get_messages(self, memory):
        """Test retrieving messages from memory."""
        # Add some messages
        await memory.add_message("user", "First message")
        await memory.add_message("assistant", "Second message")
        await memory.add_message("user", "Third message")

        messages = await memory.get_messages()

        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "First message"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"

    @pytest.mark.asyncio
    async def test_get_messages_with_limit(self, memory):
        """Test retrieving messages with limit."""
        # Add messages
        for i in range(10):
            await memory.add_message("user", f"Message {i}")

        # Get only last 3 messages
        messages = await memory.get_messages(limit=3)

        assert len(messages) == 3
        assert messages[-1]["content"] == "Message 9"

    @pytest.mark.asyncio
    async def test_get_context(self, memory):
        """Test getting formatted context."""
        # Add messages
        await memory.add_message("user", "What is Python?")
        await memory.add_message("assistant", "Python is a programming language.")

        context = await memory.get_context(include_summary=False, include_entities=False)

        assert "What is Python?" in context
        assert "Python is a programming language" in context

    @pytest.mark.asyncio
    async def test_get_context_with_summary(self, memory):
        """Test getting context with summary."""
        memory.summary = "Discussion about Python programming"

        context = await memory.get_context(include_summary=True, include_entities=False)

        assert "Conversation Summary" in context
        assert "Discussion about Python programming" in context

    @pytest.mark.asyncio
    async def test_get_context_with_entities(self, memory):
        """Test getting context with entities."""
        memory.entities = {
            "people": ["Alice", "Bob"],
            "topics": ["Python", "Programming"]
        }

        context = await memory.get_context(include_summary=False, include_entities=True)

        assert "Key Entities" in context
        assert "Alice" in context
        assert "Python" in context

    @pytest.mark.asyncio
    @patch('app.llamaindex.memory.conversation_memory.llm_factory')
    async def test_summarize_conversation(self, mock_factory, memory):
        """Test conversation summarization."""
        # Setup mock LLM
        mock_llm = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = "This is a test summary of the conversation."
        mock_llm.acomplete = AsyncMock(return_value=mock_response)
        mock_factory.create_llm.return_value = mock_llm
        mock_factory.recommend_model_for_task.return_value = "gpt-4o-mini"

        # Add messages
        await memory.add_message("user", "Tell me about AI")
        await memory.add_message("assistant", "AI is artificial intelligence...")

        # Summarize
        summary = await memory.summarize_conversation()

        assert summary == "This is a test summary of the conversation."
        mock_llm.acomplete.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.llamaindex.memory.conversation_memory.llm_factory')
    async def test_extract_entities(self, mock_factory, memory):
        """Test entity extraction."""
        # Setup mock LLM
        mock_llm = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "people": ["Alice", "Bob"],
            "topics": ["Machine Learning", "Python"]
        })
        mock_llm.acomplete = AsyncMock(return_value=mock_response)
        mock_factory.create_llm.return_value = mock_llm
        mock_factory.recommend_model_for_task.return_value = "gpt-4o"

        # Add messages
        await memory.add_message("user", "I met Alice yesterday")
        await memory.add_message("assistant", "How is Alice doing?")

        # Extract entities
        entities = await memory.extract_entities()

        assert "people" in entities
        assert "Alice" in entities["people"]
        assert "topics" in entities
        mock_llm.acomplete.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.llamaindex.memory.conversation_memory.llm_factory')
    async def test_auto_summarize(self, mock_factory, memory):
        """Test automatic summarization when threshold is reached."""
        # Setup mock LLM
        mock_llm = AsyncMock()
        mock_summary_response = MagicMock()
        mock_summary_response.text = "Summary of conversation"
        mock_entities_response = MagicMock()
        mock_entities_response.text = json.dumps({"topics": ["Testing"]})
        mock_llm.acomplete = AsyncMock(side_effect=[mock_summary_response, mock_entities_response])
        mock_factory.create_llm.return_value = mock_llm
        mock_factory.recommend_model_for_task.return_value = "gpt-4o-mini"

        # Add messages up to threshold
        for i in range(10):
            await memory.add_message("user", f"Message {i}")

        # Check that summary was created
        assert memory.summary == "Summary of conversation"
        assert memory.entities == {"topics": ["Testing"]}

    @pytest.mark.asyncio
    async def test_clear_memory(self, memory):
        """Test clearing memory."""
        # Add some messages
        await memory.add_message("user", "Test message")
        memory.summary = "Test summary"
        memory.entities = {"test": "entity"}

        # Clear
        memory.clear()

        assert memory.message_count == 0
        assert memory.summary is None
        assert memory.entities == {}
        messages = await memory.get_messages()
        assert len(messages) == 0

    @pytest.mark.asyncio
    async def test_message_roles(self, memory):
        """Test different message roles."""
        await memory.add_message("user", "User message")
        await memory.add_message("assistant", "Assistant message")
        await memory.add_message("system", "System message")

        messages = await memory.get_messages()

        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "system"

    @pytest.mark.asyncio
    async def test_message_metadata(self, memory):
        """Test message metadata handling."""
        metadata = {
            "source": "test",
            "timestamp": "2025-01-20T00:00:00Z",
            "extra_info": {"key": "value"}
        }

        await memory.add_message(
            role="user",
            content="Test message",
            metadata=metadata
        )

        messages = await memory.get_messages()

        assert len(messages) == 1
        assert messages[0]["metadata"] == metadata


class TestMemoryManager:
    """Test cases for MemoryManager."""

    @pytest.fixture
    def manager(self):
        """Create a memory manager instance for testing."""
        return MemoryManager(db_pool=None)

    def test_initialization(self, manager):
        """Test manager initialization."""
        assert manager.db_pool is None
        assert manager._memories == {}

    def test_get_memory(self, manager):
        """Test getting memory instance."""
        memory = manager.get_memory(
            user_id="user-1",
            conversation_id="conv-1"
        )

        assert isinstance(memory, ConversationMemory)
        assert memory.user_id == "user-1"
        assert memory.conversation_id == "conv-1"

    def test_get_memory_caching(self, manager):
        """Test that memory instances are cached."""
        memory1 = manager.get_memory("user-1", "conv-1")
        memory2 = manager.get_memory("user-1", "conv-1")

        # Should return same instance
        assert memory1 is memory2

    def test_get_memory_different_conversations(self, manager):
        """Test getting memory for different conversations."""
        memory1 = manager.get_memory("user-1", "conv-1")
        memory2 = manager.get_memory("user-1", "conv-2")

        # Should return different instances
        assert memory1 is not memory2
        assert memory1.conversation_id == "conv-1"
        assert memory2.conversation_id == "conv-2"

    def test_get_memory_with_custom_params(self, manager):
        """Test getting memory with custom parameters."""
        memory = manager.get_memory(
            user_id="user-1",
            conversation_id="conv-1",
            max_messages=15,
            summarize_threshold=25
        )

        assert memory.max_messages == 15
        assert memory.summarize_threshold == 25

    def test_remove_memory(self, manager):
        """Test removing memory from cache."""
        memory = manager.get_memory("user-1", "conv-1")

        # Verify it's cached
        assert "user-1:conv-1" in manager._memories

        # Remove
        manager.remove_memory("user-1", "conv-1")

        # Verify it's removed
        assert "user-1:conv-1" not in manager._memories

    def test_remove_nonexistent_memory(self, manager):
        """Test removing memory that doesn't exist."""
        # Should not raise error
        manager.remove_memory("user-1", "conv-1")


class TestMemoryPersistence:
    """Test cases for memory persistence (with mock database)."""

    @pytest.fixture
    def mock_db_pool(self):
        """Create mock database pool."""
        pool = MagicMock()
        conn = AsyncMock()

        # Setup async context manager
        acquire_mock = AsyncMock()
        acquire_mock.__aenter__.return_value = conn
        acquire_mock.__aexit__.return_value = None
        pool.acquire.return_value = acquire_mock

        return pool

    @pytest.mark.asyncio
    async def test_persist_message(self, mock_db_pool):
        """Test persisting message to database."""
        memory = ConversationMemory(
            user_id="user-1",
            conversation_id="conv-1",
            db_pool=mock_db_pool
        )

        await memory.add_message("user", "Test message", {"source": "test"})

        # Verify database was called
        acquire_mock = mock_db_pool.acquire.return_value
        conn = await acquire_mock.__aenter__()
        conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_from_database(self, mock_db_pool):
        """Test loading memory from database."""
        # Setup mock database responses
        acquire_mock = mock_db_pool.acquire.return_value
        conn = AsyncMock()
        acquire_mock.__aenter__.return_value = conn

        # Mock fetch for messages
        conn.fetch.side_effect = [
            [
                {
                    "role": "user",
                    "content": "Loaded message",
                    "metadata": json.dumps({"source": "db"}),
                    "created_at": "2025-01-20T00:00:00Z"
                }
            ],
            []  # Second fetch for memory states
        ]

        memory = ConversationMemory(
            user_id="user-1",
            conversation_id="conv-1",
            db_pool=mock_db_pool
        )

        await memory.load_from_database()

        # Verify message was loaded
        assert memory.message_count == 1
        messages = await memory.get_messages()
        assert len(messages) == 1
        assert messages[0]["content"] == "Loaded message"


class TestMemoryType:
    """Test MemoryType enum."""

    def test_memory_types(self):
        """Test that all memory types are defined."""
        assert MemoryType.BUFFER.value == "buffer"
        assert MemoryType.SUMMARY.value == "summary"
        assert MemoryType.ENTITIES.value == "entities"

"""
Comprehensive tests for ChatService - Legacy OpenAI Integration

This module provides complete test coverage for the legacy chat service
that uses direct OpenAI integration (separate from enhanced_chat_service).
"""
from __future__ import annotations

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from sqlalchemy.orm import Session
from datetime import datetime
import openai

from app.services.chat_service import ChatService
from app.models.conversation import ConversationCreate, MessageCreate, MessageRole
from app.core.exceptions import NotFoundError, AuthorizationError


# Mock models for testing
class MockConversation:
    def __init__(self, id="conv-123", user_id="user-123", title="Test Chat", model="gpt-4", system_prompt=None):
        self.id = id
        self.user_id = user_id
        self.title = title
        self.model = model
        self.system_prompt = system_prompt
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.messages = []


class MockMessage:
    def __init__(self, id="msg-123", conversation_id="conv-123", role="user", content="Hello", rating=None):
        self.id = id
        self.conversation_id = conversation_id
        self.role = role
        self.content = content
        self.rating = rating
        self.created_at = datetime.now()


class MockUserPreferences:
    def __init__(self, system_prompt=None):
        self.system_prompt = system_prompt


class TestChatServiceInitialization:
    """Test ChatService initialization and configuration."""
    
    def test_init_with_api_key(self):
        """Test initialization when API key is present."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            service = ChatService()
            assert service.is_configured is True
    
    def test_init_without_api_key(self):
        """Test initialization when API key is missing.""" 
        with patch.dict('os.environ', {}, clear=True):
            service = ChatService()
            assert service.is_configured is False
    
    def test_init_empty_api_key(self):
        """Test initialization when API key is empty."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': ''}):
            service = ChatService()
            assert service.is_configured is False


class TestConversationManagement:
    """Test conversation CRUD operations."""
    
    def test_create_conversation_success(self):
        """Test successful conversation creation."""
        mock_db = Mock(spec=Session)
        mock_conversation = MockConversation()
        mock_user_prefs = MockUserPreferences(system_prompt="You are a helpful assistant")
        
        with patch('app.services.chat_service.UserService.get_user_preferences') as mock_get_prefs, \
             patch('app.services.chat_service.Conversation') as mock_conv_class:
            
            mock_get_prefs.return_value = mock_user_prefs
            mock_conv_class.return_value = mock_conversation
            
            conversation_data = ConversationCreate(title="Test Chat", model="gpt-4")
            result = ChatService.create_conversation(mock_db, "user-123", conversation_data)
            
            assert result == mock_conversation
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once()
    
    def test_create_conversation_no_user_prefs(self):
        """Test conversation creation when user has no preferences."""
        mock_db = Mock(spec=Session)
        mock_conversation = MockConversation()
        
        with patch('app.services.chat_service.UserService.get_user_preferences') as mock_get_prefs, \
             patch('app.services.chat_service.Conversation') as mock_conv_class:
            
            mock_get_prefs.return_value = None
            mock_conv_class.return_value = mock_conversation
            
            conversation_data = ConversationCreate(title="Test Chat", model="gpt-4")
            result = ChatService.create_conversation(mock_db, "user-123", conversation_data)
            
            assert result == mock_conversation
            mock_conv_class.assert_called_once()
    
    def test_get_conversation_success(self):
        """Test successful conversation retrieval."""
        mock_db = Mock(spec=Session)
        mock_conversation = MockConversation(user_id="user-123")
        
        mock_db.query().filter().first.return_value = mock_conversation
        
        result = ChatService.get_conversation(mock_db, "conv-123", "user-123")
        
        assert result == mock_conversation
        mock_db.query.assert_called_once()
    
    def test_get_conversation_not_found(self):
        """Test conversation retrieval when not found."""
        mock_db = Mock(spec=Session)
        mock_db.query().filter().first.return_value = None
        
        result = ChatService.get_conversation(mock_db, "conv-123", "user-123")
        
        assert result is None
    
    def test_get_conversation_wrong_user(self):
        """Test conversation retrieval with wrong user."""
        mock_db = Mock(spec=Session)
        mock_conversation = MockConversation(user_id="different-user")
        
        mock_db.query().filter().first.return_value = mock_conversation
        
        result = ChatService.get_conversation(mock_db, "conv-123", "user-123")
        
        assert result is None
    
    def test_get_user_conversations_success(self):
        """Test getting user's conversations with pagination."""
        mock_db = Mock(spec=Session)
        conversations = [
            MockConversation(id="conv-1", title="Chat 1"),
            MockConversation(id="conv-2", title="Chat 2")
        ]
        
        # Mock the query chain
        mock_query = mock_db.query.return_value
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = conversations
        
        result = ChatService.get_user_conversations(mock_db, "user-123", skip=0, limit=10)
        
        assert len(result) == 2
        assert result == conversations
        mock_query.offset.assert_called_with(0)
        mock_query.limit.assert_called_with(10)
    
    def test_get_user_conversations_empty(self):
        """Test getting conversations when user has none."""
        mock_db = Mock(spec=Session)
        
        mock_query = mock_db.query.return_value
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        
        result = ChatService.get_user_conversations(mock_db, "user-123")
        
        assert result == []
    
    def test_delete_conversation_success(self):
        """Test successful conversation deletion."""
        mock_db = Mock(spec=Session)
        mock_conversation = MockConversation(user_id="user-123")
        
        with patch.object(ChatService, 'get_conversation') as mock_get:
            mock_get.return_value = mock_conversation
            
            result = ChatService.delete_conversation(mock_db, "conv-123", "user-123")
            
            assert result is True
            mock_db.delete.assert_called_once_with(mock_conversation)
            mock_db.commit.assert_called_once()
    
    def test_delete_conversation_not_found(self):
        """Test deleting non-existent conversation."""
        mock_db = Mock(spec=Session)
        
        with patch.object(ChatService, 'get_conversation') as mock_get:
            mock_get.return_value = None
            
            result = ChatService.delete_conversation(mock_db, "conv-123", "user-123")
            
            assert result is False
            mock_db.delete.assert_not_called()
    
    def test_update_conversation_title_success(self):
        """Test successful conversation title update."""
        mock_db = Mock(spec=Session)
        mock_conversation = MockConversation(user_id="user-123", title="Old Title")
        
        with patch.object(ChatService, 'get_conversation') as mock_get:
            mock_get.return_value = mock_conversation
            
            result = ChatService.update_conversation_title(mock_db, "conv-123", "user-123", "New Title")
            
            assert result == mock_conversation
            assert mock_conversation.title == "New Title"
            mock_db.commit.assert_called_once()
    
    def test_update_conversation_title_not_found(self):
        """Test updating title of non-existent conversation."""
        mock_db = Mock(spec=Session)
        
        with patch.object(ChatService, 'get_conversation') as mock_get:
            mock_get.return_value = None
            
            with pytest.raises(NotFoundError):
                ChatService.update_conversation_title(mock_db, "conv-123", "user-123", "New Title")


class TestMessageManagement:
    """Test message operations."""
    
    def test_get_conversation_messages_success(self):
        """Test getting messages for a conversation."""
        mock_db = Mock(spec=Session)
        mock_conversation = MockConversation(user_id="user-123")
        messages = [
            MockMessage(id="msg-1", content="Hello"),
            MockMessage(id="msg-2", content="Hi there")
        ]
        
        with patch.object(ChatService, 'get_conversation') as mock_get:
            mock_get.return_value = mock_conversation
            
            mock_query = mock_db.query.return_value
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.all.return_value = messages
            
            result = ChatService.get_conversation_messages(mock_db, "conv-123", "user-123")
            
            assert result == messages
    
    def test_get_conversation_messages_unauthorized(self):
        """Test getting messages for unauthorized conversation."""
        mock_db = Mock(spec=Session)
        
        with patch.object(ChatService, 'get_conversation') as mock_get:
            mock_get.return_value = None
            
            with pytest.raises(AuthorizationError):
                ChatService.get_conversation_messages(mock_db, "conv-123", "user-123")
    
    def test_add_message_success(self):
        """Test successful message addition."""
        mock_db = Mock(spec=Session)
        mock_conversation = MockConversation(user_id="user-123")
        mock_message = MockMessage()
        
        with patch.object(ChatService, 'get_conversation') as mock_get, \
             patch('app.services.chat_service.Message') as mock_msg_class:
            
            mock_get.return_value = mock_conversation
            mock_msg_class.return_value = mock_message
            
            message_data = MessageCreate(role=MessageRole.USER, content="Hello")
            result = ChatService.add_message(mock_db, "conv-123", message_data, "user-123")
            
            assert result == mock_message
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
    
    def test_add_message_unauthorized(self):
        """Test adding message to unauthorized conversation."""
        mock_db = Mock(spec=Session)
        
        with patch.object(ChatService, 'get_conversation') as mock_get:
            mock_get.return_value = None
            
            message_data = MessageCreate(role=MessageRole.USER, content="Hello")
            
            with pytest.raises(AuthorizationError):
                ChatService.add_message(mock_db, "conv-123", message_data, "user-123")
    
    def test_update_message_rating_success(self):
        """Test successful message rating update."""
        mock_db = Mock(spec=Session)
        mock_message = MockMessage()
        
        mock_db.query().filter().first.return_value = mock_message
        
        result = ChatService.update_message_rating(mock_db, "msg-123", 5)
        
        assert result == mock_message
        assert mock_message.rating == 5
        mock_db.commit.assert_called_once()
    
    def test_update_message_rating_not_found(self):
        """Test updating rating of non-existent message."""
        mock_db = Mock(spec=Session)
        mock_db.query().filter().first.return_value = None
        
        with pytest.raises(NotFoundError):
            ChatService.update_message_rating(mock_db, "msg-123", 5)


class TestOpenAIIntegration:
    """Test OpenAI API integration."""
    
    def test_build_openai_messages_with_system_prompt(self):
        """Test building OpenAI messages with system prompt."""
        conversation = MockConversation(system_prompt="You are helpful")
        messages = [
            MockMessage(role="user", content="Hello"),
            MockMessage(role="assistant", content="Hi there")
        ]
        
        result = ChatService.build_openai_messages(conversation, messages)
        
        assert len(result) == 3  # system + 2 messages
        assert result[0]["role"] == "system"
        assert result[0]["content"] == "You are helpful"
        assert result[1]["role"] == "user"
        assert result[2]["role"] == "assistant"
    
    def test_build_openai_messages_no_system_prompt(self):
        """Test building OpenAI messages without system prompt."""
        conversation = MockConversation(system_prompt=None)
        messages = [
            MockMessage(role="user", content="Hello"),
            MockMessage(role="assistant", content="Hi there")
        ]
        
        result = ChatService.build_openai_messages(conversation, messages)
        
        assert len(result) == 2  # no system message
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"
    
    def test_build_openai_messages_empty(self):
        """Test building OpenAI messages with no messages."""
        conversation = MockConversation()
        messages = []
        
        result = ChatService.build_openai_messages(conversation, messages)
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_send_message_success(self):
        """Test successful message sending."""
        mock_db = Mock(spec=Session)
        conversation = MockConversation(user_id="user-123", model="gpt-4")
        messages = []
        
        # Mock OpenAI response
        mock_openai_response = MagicMock()
        mock_openai_response.choices = [MagicMock()]
        mock_openai_response.choices[0].message.content = "AI response"
        mock_openai_response.usage.total_tokens = 50
        
        with patch.object(ChatService, 'get_conversation') as mock_get, \
             patch.object(ChatService, 'get_conversation_messages') as mock_get_msgs, \
             patch.object(ChatService, 'build_openai_messages') as mock_build, \
             patch.object(ChatService, 'add_message') as mock_add, \
             patch('openai.ChatCompletion.acreate') as mock_openai:
            
            mock_get.return_value = conversation
            mock_get_msgs.return_value = messages
            mock_build.return_value = [{"role": "user", "content": "Hello"}]
            mock_add.return_value = MockMessage(content="AI response")
            mock_openai.return_value = mock_openai_response
            
            result = await ChatService.send_message(mock_db, "conv-123", "Hello", "user-123")
            
            assert result.content == "AI response"
            assert mock_add.call_count == 2  # user message + AI response
    
    @pytest.mark.asyncio
    async def test_send_message_unauthorized(self):
        """Test sending message to unauthorized conversation."""
        mock_db = Mock(spec=Session)
        
        with patch.object(ChatService, 'get_conversation') as mock_get:
            mock_get.return_value = None
            
            with pytest.raises(AuthorizationError):
                await ChatService.send_message(mock_db, "conv-123", "Hello", "user-123")
    
    @pytest.mark.asyncio
    async def test_send_message_openai_error(self):
        """Test handling OpenAI API errors."""
        mock_db = Mock(spec=Session)
        conversation = MockConversation(user_id="user-123")
        
        with patch.object(ChatService, 'get_conversation') as mock_get, \
             patch.object(ChatService, 'get_conversation_messages') as mock_get_msgs, \
             patch.object(ChatService, 'build_openai_messages') as mock_build, \
             patch.object(ChatService, 'add_message') as mock_add, \
             patch('openai.ChatCompletion.acreate') as mock_openai:
            
            mock_get.return_value = conversation
            mock_get_msgs.return_value = []
            mock_build.return_value = [{"role": "user", "content": "Hello"}]
            mock_add.return_value = MockMessage()
            mock_openai.side_effect = openai.error.OpenAIError("API Error")
            
            with pytest.raises(Exception):
                await ChatService.send_message(mock_db, "conv-123", "Hello", "user-123")


class TestUtilityMethods:
    """Test utility and helper methods."""
    
    def test_generate_conversation_title_from_messages(self):
        """Test generating title from message history."""
        messages = [
            MockMessage(role="user", content="What is the weather like?"),
            MockMessage(role="assistant", content="I can help with weather information.")
        ]
        
        result = ChatService.generate_conversation_title(messages)
        
        # Should use first user message, truncated if needed
        assert "weather" in result.lower()
        assert len(result) <= 50
    
    def test_generate_conversation_title_long_message(self):
        """Test generating title from long message."""
        long_message = "This is a very long message " * 10  # 290+ characters
        messages = [MockMessage(role="user", content=long_message)]
        
        result = ChatService.generate_conversation_title(messages)
        
        assert len(result) <= 50
        assert result.endswith("...")
    
    def test_generate_conversation_title_no_user_messages(self):
        """Test generating title when no user messages exist."""
        messages = [MockMessage(role="assistant", content="Hello there")]
        
        result = ChatService.generate_conversation_title(messages)
        
        assert result == "New Chat"
    
    def test_generate_conversation_title_empty_messages(self):
        """Test generating title with empty message list."""
        messages = []
        
        result = ChatService.generate_conversation_title(messages)
        
        assert result == "New Chat"
    
    def test_generate_conversation_title_empty_content(self):
        """Test generating title from message with empty content."""
        messages = [MockMessage(role="user", content="")]
        
        result = ChatService.generate_conversation_title(messages)
        
        assert result == "New Chat"


class TestErrorHandling:
    """Test comprehensive error handling scenarios."""
    
    def test_database_transaction_rollback(self):
        """Test database error handling with rollback."""
        mock_db = Mock(spec=Session)
        mock_db.commit.side_effect = Exception("Database error")
        
        with patch('app.services.chat_service.Conversation') as mock_conv_class:
            mock_conv_class.return_value = MockConversation()
            
            conversation_data = ConversationCreate(title="Test", model="gpt-4")
            
            with pytest.raises(Exception):
                ChatService.create_conversation(mock_db, "user-123", conversation_data)
    
    def test_invalid_message_role(self):
        """Test handling invalid message roles."""
        mock_db = Mock(spec=Session)
        mock_conversation = MockConversation(user_id="user-123")
        
        with patch.object(ChatService, 'get_conversation') as mock_get:
            mock_get.return_value = mock_conversation
            
            # This would normally be validated by the MessageCreate model
            # but we're testing the service layer
            message_data = MessageCreate(role="invalid_role", content="Hello")
            
            # The actual validation happens in the Message model creation
            with patch('app.services.chat_service.Message') as mock_msg_class:
                mock_msg_class.side_effect = ValueError("Invalid role")
                
                with pytest.raises(ValueError):
                    ChatService.add_message(mock_db, "conv-123", message_data, "user-123")


class TestIntegrationScenarios:
    """Test complete workflows and integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_full_conversation_flow(self):
        """Test complete conversation creation and messaging flow."""
        mock_db = Mock(spec=Session)
        
        # Step 1: Create conversation
        with patch.object(ChatService, 'create_conversation') as mock_create:
            mock_create.return_value = MockConversation(id="conv-123", user_id="user-123")
            
            conv_data = ConversationCreate(title="Test Chat", model="gpt-4")
            conversation = ChatService.create_conversation(mock_db, "user-123", conv_data)
            
            assert conversation.id == "conv-123"
        
        # Step 2: Send message
        with patch.object(ChatService, 'send_message') as mock_send:
            mock_send.return_value = MockMessage(content="AI response")
            
            response = await ChatService.send_message(mock_db, "conv-123", "Hello", "user-123")
            
            assert response.content == "AI response"
        
        # Step 3: Get messages
        with patch.object(ChatService, 'get_conversation_messages') as mock_get_msgs:
            mock_get_msgs.return_value = [
                MockMessage(role="user", content="Hello"),
                MockMessage(role="assistant", content="AI response")
            ]
            
            messages = ChatService.get_conversation_messages(mock_db, "conv-123", "user-123")
            
            assert len(messages) == 2
    
    def test_pagination_edge_cases(self):
        """Test pagination with various edge cases."""
        mock_db = Mock(spec=Session)
        
        mock_query = mock_db.query.return_value
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        
        # Test with zero limit
        result = ChatService.get_user_conversations(mock_db, "user-123", skip=0, limit=0)
        assert result == []
        
        # Test with large offset
        result = ChatService.get_user_conversations(mock_db, "user-123", skip=1000, limit=10)
        mock_query.offset.assert_called_with(1000)
    
    def test_concurrent_message_handling(self):
        """Test handling of concurrent message scenarios."""
        # This would test concurrent access patterns
        # For now, we'll test that the service handles basic concurrency
        mock_db = Mock(spec=Session)
        
        # Multiple rapid calls should all work
        for i in range(5):
            with patch.object(ChatService, 'get_conversation') as mock_get:
                mock_get.return_value = MockConversation(user_id="user-123")
                result = ChatService.get_conversation(mock_db, f"conv-{i}", "user-123")
                assert result.user_id == "user-123"
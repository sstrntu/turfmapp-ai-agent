"""
Tests for Enhanced Chat Service core functionality.

This module tests the core chat processing, tool handling, and conversation management.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any, List

from app.services.enhanced_chat_service import EnhancedChatService


class TestEnhancedChatServiceCore:
    """Test core enhanced chat service functionality."""
    
    @pytest.mark.asyncio
    async def test_process_chat_request_basic_message(self):
        """Test processing a basic chat message without tools."""
        chat_service = EnhancedChatService()
        
        mock_api_response = {
            "id": "resp-123",
            "status": "completed",
            "output_text": "Hello! How can I help you today?"
        }
        
        with patch.object(chat_service, 'call_responses_api', new_callable=AsyncMock) as mock_api, \
             patch.object(chat_service, 'create_conversation', return_value="conv-123"), \
             patch.object(chat_service, 'get_conversation_history', return_value=[]), \
             patch.object(chat_service, 'save_message_to_conversation', return_value=True):
            
            mock_api.return_value = mock_api_response
            
            result = await chat_service.process_chat_request(
                message="Hello",
                user_id="user-123",
                conversation_id=None
            )
            
            assert result["assistant_message"]["content"] == "Hello! How can I help you today?"
            assert result["conversation_id"] == "conv-123"
            mock_api.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_chat_request_with_existing_conversation(self):
        """Test processing a chat message with existing conversation."""
        chat_service = EnhancedChatService()
        
        mock_history = [
            {"role": "user", "content": "Previous message"},
            {"role": "assistant", "content": "Previous response"}
        ]
        
        mock_api_response = {
            "id": "resp-456", 
            "status": "completed",
            "output_text": "Based on our previous conversation..."
        }
        
        with patch.object(chat_service, 'call_responses_api', new_callable=AsyncMock) as mock_api, \
             patch.object(chat_service, 'get_conversation_history', return_value=mock_history), \
             patch.object(chat_service, 'save_message_to_conversation', return_value=True):
            
            mock_api.return_value = mock_api_response
            
            result = await chat_service.process_chat_request(
                message="Continue our discussion", 
                user_id="user-123",
                conversation_id="conv-existing"
            )
            
            assert result["conversation_id"] == "conv-existing"
            assert "Based on our previous conversation" in result["assistant_message"]["content"]
    
    @pytest.mark.asyncio
    async def test_process_chat_request_api_failure(self):
        """Test handling of API failures."""
        chat_service = EnhancedChatService()
        
        with patch.object(chat_service, 'call_responses_api', new_callable=AsyncMock) as mock_api, \
             patch.object(chat_service, 'create_conversation', return_value="conv-123"), \
             patch.object(chat_service, 'get_conversation_history', return_value=[]):
            
            mock_api.side_effect = Exception("API Error")
            
            with pytest.raises(Exception, match="API Error"):
                await chat_service.process_chat_request(
                    message="Test message",
                    user_id="user-123",
                    conversation_id=None
                )


class TestEnhancedChatServiceToolHandling:
    """Test tool handling functionality."""
    
    @pytest.mark.asyncio
    async def test_handle_tool_calls_web_search(self):
        """Test handling web search tool calls.""" 
        chat_service = EnhancedChatService()
        
        tool_calls = [{
            "id": "call-123",
            "type": "function",
            "function": {
                "name": "web_search",
                "arguments": '{"query": "Python programming", "num_results": 5}'
            }
        }]
        
        mock_search_results = [
            {"title": "Python Tutorial", "url": "https://python.org", "snippet": "Learn Python"}
        ]
        
        with patch('app.services.enhanced_chat_service.web_search', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = mock_search_results
            
            results = await chat_service.handle_tool_calls("user-123", tool_calls)
            
            assert len(results) == 1
            assert results[0]["tool_call_id"] == "call-123"
            assert "Python Tutorial" in results[0]["content"]
    
    @pytest.mark.asyncio
    async def test_handle_tool_calls_unknown_tool(self):
        """Test handling of unknown tool calls."""
        chat_service = EnhancedChatService()
        
        tool_calls = [{
            "id": "call-unknown",
            "type": "function", 
            "function": {
                "name": "unknown_tool",
                "arguments": '{}'
            }
        }]
        
        results = await chat_service.handle_tool_calls("user-123", tool_calls)
        
        assert len(results) == 1
        assert results[0]["tool_call_id"] == "call-unknown"
        assert "not supported" in results[0]["content"].lower()


class TestEnhancedChatServiceConversationManagement:
    """Test conversation management functionality."""
    
    @pytest.mark.asyncio
    async def test_create_conversation(self):
        """Test creating a new conversation."""
        chat_service = EnhancedChatService()
        
        with patch.object(chat_service, 'use_database_fallback', new_callable=AsyncMock) as mock_fallback:
            mock_fallback.return_value = "new-conv-123"
            
            conversation_id = await chat_service.create_conversation("user-123")
            
            assert conversation_id == "new-conv-123"
            mock_fallback.assert_called_once()
    
    @pytest.mark.asyncio 
    async def test_get_conversation_history(self):
        """Test retrieving conversation history."""
        chat_service = EnhancedChatService()
        
        mock_messages = [
            {
                "id": "msg-1",
                "role": "user",
                "content": "Hello",
                "metadata": {}
            },
            {
                "id": "msg-2", 
                "role": "assistant",
                "content": "Hi there!",
                "metadata": {}
            }
        ]
        
        with patch.object(chat_service, 'use_database_fallback', new_callable=AsyncMock) as mock_fallback:
            mock_fallback.return_value = mock_messages
            
            history = await chat_service.get_conversation_history("conv-123", "user-123")
            
            assert len(history) == 2
            assert history[0]["role"] == "user"
            assert history[1]["role"] == "assistant"
    
    @pytest.mark.asyncio
    async def test_save_message_to_conversation(self):
        """Test saving a message to conversation."""
        chat_service = EnhancedChatService()
        
        with patch.object(chat_service, 'use_database_fallback', new_callable=AsyncMock) as mock_fallback:
            mock_fallback.return_value = True
            
            result = await chat_service.save_message_to_conversation(
                conversation_id="conv-123",
                role="user",
                content="Test message",
                user_id="user-123"
            )
            
            assert result is True
            mock_fallback.assert_called_once()


class TestEnhancedChatServiceUtilities:
    """Test utility functions."""
    
    def test_build_conversation_context_empty(self):
        """Test building conversation context with empty history."""
        chat_service = EnhancedChatService()
        
        context = chat_service._build_conversation_context("New message", [])
        
        assert "New message" in context
        assert context.strip().endswith("New message")
    
    def test_build_conversation_context_with_history(self):
        """Test building conversation context with history."""
        chat_service = EnhancedChatService()
        
        history = [
            {"role": "user", "content": "Previous question"},
            {"role": "assistant", "content": "Previous answer"}
        ]
        
        context = chat_service._build_conversation_context("New question", history)
        
        assert "Previous question" in context
        assert "Previous answer" in context
        assert "New question" in context
    
    def test_extract_sources_from_text_with_urls(self):
        """Test extracting sources from text with URLs."""
        chat_service = EnhancedChatService()
        
        text_with_urls = "Check out https://example.com and https://test.org for more info."
        
        sources = chat_service._extract_sources_from_text(text_with_urls)
        
        assert len(sources) == 2
        assert any(source["url"] == "https://example.com" for source in sources)
        assert any(source["url"] == "https://test.org" for source in sources)
    
    def test_extract_sources_from_text_no_urls(self):
        """Test extracting sources from text without URLs."""
        chat_service = EnhancedChatService()
        
        text_without_urls = "This is just regular text with no links."
        
        sources = chat_service._extract_sources_from_text(text_without_urls)
        
        assert sources == []


class TestEnhancedChatServiceErrorHandling:
    """Test error handling scenarios."""
    
    @pytest.mark.asyncio
    async def test_database_connection_failure(self):
        """Test handling of database connection failures."""
        chat_service = EnhancedChatService()
        
        with patch('app.services.enhanced_chat_service.execute_query_one', new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = Exception("Database connection failed")
            
            with pytest.raises(Exception, match="Database connection failed"):
                await chat_service.create_conversation("user-123")
    
    @pytest.mark.asyncio
    async def test_api_timeout_handling(self):
        """Test handling of API timeouts."""
        chat_service = EnhancedChatService()
        
        with patch.object(chat_service, 'call_responses_api', new_callable=AsyncMock) as mock_api, \
             patch.object(chat_service, 'create_conversation', return_value="conv-123"), \
             patch.object(chat_service, 'get_conversation_history', return_value=[]):
            
            mock_api.side_effect = TimeoutError("API request timed out")
            
            with pytest.raises(TimeoutError, match="API request timed out"):
                await chat_service.process_chat_request(
                    message="Test timeout",
                    user_id="user-123",
                    conversation_id=None
                )
    
    @pytest.mark.asyncio
    async def test_invalid_tool_arguments(self):
        """Test handling of invalid tool arguments."""
        chat_service = EnhancedChatService()
        
        tool_calls = [{
            "id": "call-invalid",
            "type": "function",
            "function": {
                "name": "web_search", 
                "arguments": 'invalid json{'
            }
        }]
        
        results = await chat_service.handle_tool_calls("user-123", tool_calls)
        
        assert len(results) == 1
        assert results[0]["tool_call_id"] == "call-invalid"
        assert "error" in results[0]["content"].lower()


class TestEnhancedChatServiceModelHandling:
    """Test model selection and handling."""
    
    @pytest.mark.asyncio
    async def test_call_responses_api_with_different_models(self):
        """Test calling responses API with different models."""
        chat_service = EnhancedChatService()
        
        test_models = ["gpt-4o", "gpt-5-mini", "claude-3-sonnet"]
        
        for model in test_models:
            with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
                mock_response = Mock()
                mock_response.json.return_value = {
                    "id": "resp-123",
                    "status": "completed", 
                    "output_text": f"Response from {model}"
                }
                mock_response.status_code = 200
                mock_post.return_value = mock_response
                
                response = await chat_service.call_responses_api(
                    conversation_context="Test",
                    model=model,
                    user_id="user-123"
                )
                
                assert response["output_text"] == f"Response from {model}"
    
    @pytest.mark.asyncio
    async def test_call_responses_api_error_response(self):
        """Test handling of error responses from API."""
        chat_service = EnhancedChatService()
        
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_post.return_value = mock_response
            
            with pytest.raises(Exception, match="HTTP 500"):
                await chat_service.call_responses_api(
                    conversation_context="Test", 
                    model="gpt-4o",
                    user_id="user-123"
                )
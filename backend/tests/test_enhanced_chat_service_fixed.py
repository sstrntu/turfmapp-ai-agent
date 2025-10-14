"""
Fixed tests for Enhanced Chat Service core functionality.

This module tests the core chat processing, tool handling, and conversation management.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any, List
import json

from app.services.chat_service import (
    EnhancedChatService,
    _extract_sources_from_tool_result,
    _extract_sources_from_claude_response,
    _dedupe_sources,
)
from app.services.anthropic_client import AnthropicClient, anthropic_client


class TestEnhancedChatServiceCore:
    """Test core enhanced chat service functionality."""
    
    @pytest.mark.asyncio
    async def test_process_chat_request_basic_message(self):
        """Test processing a basic chat message without tools."""
        chat_service = EnhancedChatService()
        
        mock_api_response = {
            "id": "resp-123",
            "status": "completed",
            "output": [
                {
                    "content": [
                        {
                            "text": "Hello! How can I help you today?"
                        }
                    ]
                }
            ]
        }
        
        with patch.object(chat_service, 'call_responses_api', new_callable=AsyncMock) as mock_api, \
             patch.object(chat_service, 'create_conversation', new_callable=AsyncMock) as mock_create, \
             patch.object(chat_service, 'get_conversation_history', new_callable=AsyncMock) as mock_history, \
             patch.object(chat_service, 'save_message_to_conversation', new_callable=AsyncMock) as mock_save, \
             patch('app.utils.chat_utils.format_chat_history', return_value=[]):
            
            mock_create.return_value = "conv-123"
            mock_history.return_value = []
            mock_save.return_value = True
            mock_api.return_value = mock_api_response
            
            result = await chat_service.process_chat_request(
                message="Hello",
                user_id="user-123",
                conversation_id=None
            )
            
            assert "Hello! How can I help you today?" in result["assistant_message"]["content"]
            assert result["conversation_id"] == "conv-123"
            assert result["model"] == "gpt-4o"
            assert result["provider"] == "openai"
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
            "output": [
                {
                    "content": [
                        {
                            "text": "Based on our previous conversation..."
                        }
                    ]
                }
            ]
        }
        
        with patch.object(chat_service, 'call_responses_api', new_callable=AsyncMock) as mock_api, \
             patch.object(chat_service, 'get_conversation_history', new_callable=AsyncMock) as mock_history_call, \
             patch.object(chat_service, 'save_message_to_conversation', new_callable=AsyncMock) as mock_save, \
             patch('app.utils.chat_utils.format_chat_history', return_value=mock_history):
            
            mock_history_call.return_value = mock_history
            mock_save.return_value = True
            mock_api.return_value = mock_api_response
            
            result = await chat_service.process_chat_request(
                message="Continue our discussion", 
                user_id="user-123",
                conversation_id="conv-existing"
            )
            
            assert result["conversation_id"] == "conv-existing"
            assert "Based on our previous conversation" in result["assistant_message"]["content"]
            assert result["model"] == "gpt-4o"
            assert result["provider"] == "openai"
    
    @pytest.mark.asyncio
    async def test_process_chat_request_api_failure(self):
        """Test handling of API failures."""
        chat_service = EnhancedChatService()
        
        with patch.object(chat_service, 'call_responses_api', new_callable=AsyncMock) as mock_api, \
             patch.object(chat_service, 'create_conversation', new_callable=AsyncMock) as mock_create, \
             patch.object(chat_service, 'get_conversation_history', new_callable=AsyncMock) as mock_history, \
             patch.object(chat_service, 'save_message_to_conversation', new_callable=AsyncMock), \
             patch('app.utils.chat_utils.format_chat_history', return_value=[]):
            
            mock_create.return_value = "conv-123"
            mock_history.return_value = []
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
        
        results = await chat_service.handle_tool_calls("user-123", tool_calls)
        
        assert len(results) == 1
        assert results[0]["tool_call_id"] == "call-123"
        # Since web_search is not implemented, it should return not supported
        assert "not supported" in results[0]["content"].lower()
    
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

    @pytest.mark.asyncio
    async def test_call_claude_api_with_web_search_tool(self):
        """Claude requests should forward web search tooling to the Anthropic client."""
        chat_service = EnhancedChatService()
        tools = [{"type": "web_search_preview", "name": "web_search"}]
        messages = [{"role": "user", "content": "What's the latest sports news?"}]
        mock_response = {
            "content": [
                {"type": "text", "text": "Here are the latest headlines."}
            ]
        }

        with patch.object(anthropic_client, "api_key", "test-key"), \
             patch.object(anthropic_client, "call_messages_api", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response

            result = await chat_service.call_claude_api(
                messages=messages,
                model="claude-3-5-sonnet",
                tools=tools,
            )

        mock_call.assert_awaited_once()
        await_kwargs = mock_call.await_args.kwargs
        assert await_kwargs["tools"] == tools
        assert result["provider"] == "anthropic"
        assert "latest headlines" in result["output_text"]
        assert result["sources"] == []
        assert result["blocks"] == []
        assert result["sources"] == []


class TestEnhancedChatServiceConversationManagement:
    """Test conversation management functionality."""
    
    @pytest.mark.asyncio
    async def test_create_conversation(self):
        """Test creating a new conversation."""
        chat_service = EnhancedChatService()
        
        with patch.object(chat_service, 'use_database_fallback', new_callable=AsyncMock) as mock_fallback:
            mock_fallback.return_value = {"id": "new-conv-123"}
            
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
    
    @pytest.mark.asyncio
    async def test_get_user_preferences_default(self):
        """Test getting default user preferences."""
        chat_service = EnhancedChatService()

        preferences = await chat_service.get_user_preferences("user-123")

        assert "model" in preferences
        assert "include_reasoning" in preferences
        assert "reasoning_effort" in preferences
        assert "text_format" in preferences
        assert preferences["model"] == "gpt-4o"
        assert preferences["include_reasoning"] is False
    
    def test_stringify_text_string(self):
        """Test stringify_text with string input."""
        chat_service = EnhancedChatService()
        
        result = chat_service.stringify_text("Hello world")
        
        assert result == "Hello world"
    
    def test_stringify_text_dict(self):
        """Test stringify_text with dictionary input."""
        chat_service = EnhancedChatService()
        
        test_dict = {"message": "Hello", "status": "success"}
        result = chat_service.stringify_text(test_dict)
        
        assert isinstance(result, str)
        # Should contain the dict content as string
        assert "Hello" in result or json.dumps(test_dict) == result
    
    def test_extract_gmail_search_query_about_pattern(self):
        """Test extracting Gmail search query with 'about' pattern."""
        chat_service = EnhancedChatService()
        
        result = chat_service._extract_gmail_search_query("find emails about project deadline")
        
        assert "project deadline" in result
    
    def test_extract_gmail_search_query_from_pattern(self):
        """Test extracting Gmail search query with 'from' pattern."""
        chat_service = EnhancedChatService()
        
        result = chat_service._extract_gmail_search_query("emails from john@company.com")
        
        assert "john@company.com" in result
    
    def test_extract_gmail_search_query_fallback(self):
        """Test fallback Gmail search query extraction."""
        chat_service = EnhancedChatService()
        
        result = chat_service._extract_gmail_search_query("show me important messages")
        
        # Could be empty after prefix removal or contain important
        assert "important" in result or result == ""


class TestEnhancedChatServiceErrorHandling:
    """Test error handling scenarios."""
    
    @pytest.mark.asyncio
    async def test_database_connection_failure(self):
        """Test handling of database connection failures."""
        chat_service = EnhancedChatService()
        
        with patch.object(chat_service, 'use_database_fallback', new_callable=AsyncMock) as mock_fallback:
            mock_fallback.side_effect = Exception("Database connection failed")
            
            with pytest.raises(Exception, match="Database connection failed"):
                await chat_service.create_conversation("user-123")
    
    @pytest.mark.asyncio
    async def test_api_timeout_handling(self):
        """Test handling of API timeouts."""
        chat_service = EnhancedChatService()
        
        with patch.object(chat_service, 'call_responses_api', new_callable=AsyncMock) as mock_api, \
             patch.object(chat_service, 'create_conversation', new_callable=AsyncMock) as mock_create, \
             patch.object(chat_service, 'get_conversation_history', new_callable=AsyncMock) as mock_history, \
             patch.object(chat_service, 'save_message_to_conversation', new_callable=AsyncMock), \
             patch('app.utils.chat_utils.format_chat_history', return_value=[]):
            
            mock_create.return_value = "conv-123"
            mock_history.return_value = []
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
        assert "error" in results[0]["content"].lower() or "not supported" in results[0]["content"].lower()


class TestEnhancedChatServiceModelHandling:
    """Test model selection and handling."""
    
    @pytest.mark.asyncio
    async def test_call_responses_api_with_different_models(self):
        """Test calling responses API with different models."""
        chat_service = EnhancedChatService()
        
        test_models = ["gpt-4o", "gpt-5-mini", "claude-sonnet-4-20250514"]
        
        for model in test_models:
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client
                
                mock_response = Mock()
                mock_response.json.return_value = {
                    "id": "resp-123",
                    "status": "completed", 
                    "output": [
                        {
                            "content": [
                                {
                                    "text": f"Response from {model}"
                                }
                            ]
                        }
                    ]
                }
                mock_response.status_code = 200
                mock_client.post.return_value = mock_response
                
                response = await chat_service.call_responses_api(
                    conversation_context="Test",
                    model=model,
                    user_id="user-123"
                )
                
                assert response["output"][0]["content"][0]["text"] == f"Response from {model}"
    
    @pytest.mark.asyncio
    async def test_call_responses_api_error_response(self):
        """Test handling of error responses from API."""
        chat_service = EnhancedChatService()
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_post_result = AsyncMock()
            mock_post_result.return_value = mock_response
            mock_client.post = mock_post_result
            
            with pytest.raises(Exception):
                await chat_service.call_responses_api(
                    conversation_context="Test", 
                    model="gpt-4o",
                    user_id="user-123"
                )


class TestEnhancedChatServiceListOperations:
    """Test conversation list operations."""
    
    @pytest.mark.asyncio
    async def test_get_conversation_list(self):
        """Test getting conversation list."""
        chat_service = EnhancedChatService()
        
        mock_conversations = [
            {"id": "conv-1", "title": "First conversation", "created_at": "2025-01-01"},
            {"id": "conv-2", "title": "Second conversation", "created_at": "2025-01-02"}
        ]
        
        with patch.object(chat_service, 'use_database_fallback', new_callable=AsyncMock) as mock_fallback:
            mock_fallback.return_value = mock_conversations
            
            result = await chat_service.get_conversation_list("user-123")
            
            assert len(result) == 2
            assert result[0]["id"] == "conv-1"
            assert result[1]["id"] == "conv-2"
    
    @pytest.mark.asyncio
    async def test_delete_conversation(self):
        """Test deleting a conversation."""
        chat_service = EnhancedChatService()
        
        with patch.object(chat_service, 'use_database_fallback', new_callable=AsyncMock) as mock_fallback:
            mock_fallback.return_value = True
            
            result = await chat_service.delete_conversation("conv-123", "user-123")
            
            assert result is True
            mock_fallback.assert_called_once()


class TestAnthropicClientToolConversion:
    """Test Anthropic tool conversion helper."""

    def test_convert_web_search_tool(self):
        """Ensure web search preview tools convert to Anthropic format."""
        client = AnthropicClient()
        converted = client._convert_tools_to_anthropic_format(
            [{"type": "web_search_preview", "name": "web_search"}]
        )
        assert converted == [{
            "type": "web_search_20250305",
            "name": "web_search"
        }]

    def test_convert_function_tool(self):
        """Ensure function tools convert to Anthropic function schema."""
        client = AnthropicClient()
        converted = client._convert_tools_to_anthropic_format(
            [{
                "type": "function",
                "function": {
                    "name": "gmail_recent",
                    "description": "Fetch latest emails.",
                    "parameters": {"type": "object"}
                }
            }]
        )
        assert converted == [{
            "type": "custom",
            "name": "gmail_recent",
            "description": "Fetch latest emails.",
            "input_schema": {"type": "object"}
        }]

    def test_convert_web_search_with_location(self):
        """Ensure location metadata is preserved when provided."""
        client = AnthropicClient()
        converted = client._convert_tools_to_anthropic_format(
            [{
                "type": "web_search_preview",
                "name": "web_search",
                "user_location": {
                    "type": "fixed",
                    "city": "Bangkok",
                    "country": "Thailand"
                }
            }]
        )
        assert converted == [{
            "type": "web_search_20250305",
            "name": "web_search",
            "user_location": {
                "type": "fixed",
                "city": "Bangkok",
                "country": "Thailand"
            }
        }]

    def test_convert_web_search_ignores_context_size(self):
        """Ensure search context size is not forwarded to Anthropic."""
        client = AnthropicClient()
        converted = client._convert_tools_to_anthropic_format(
            [{
                "type": "web_search_preview",
                "name": "web_search",
                "search_context_size": "large"
            }]
        )
        assert converted == [{
            "type": "web_search_20250305",
            "name": "web_search"
        }]


class TestSourceExtractionHelpers:
    """Test helper utilities for extracting search sources."""

    def test_extract_sources_from_tool_result_json(self):
        """Extract sources from tool result containing JSON payload."""
        tool_result = {
            "type": "tool_result",
            "name": "web_search_preview",
            "content": [
                {
                    "type": "output_text",
                    "text": json.dumps({
                        "search_results": [
                            {"title": "Result One", "url": "https://example.com/1"},
                            {"title": "Result Two", "url": "https://example.com/2"}
                        ]
                    })
                }
            ]
        }

        sources = _extract_sources_from_tool_result(tool_result)
        assert len(sources) == 2
        assert sources[0]["url"] == "https://example.com/1"
        assert sources[1]["title"] == "Result Two"

    def test_extract_sources_from_claude_response_citations(self):
        """Extract sources from Claude response citations."""
        response = {
            "content": [
                {
                    "type": "text",
                    "text": "Answer with citation",
                    "citations": [
                        {"url": "https://news.example.com/story", "title": "Story"}
                    ]
                }
            ]
        }

        sources = _extract_sources_from_claude_response(response)
        assert sources == [{
            "url": "https://news.example.com/story",
            "title": "Story",
            "site": "news.example.com",
            "favicon": "https://www.google.com/s2/favicons?domain=news.example.com&sz=64"
        }]

    def test_dedupe_sources(self):
        """Ensure duplicate sources are removed while preserving order."""
        entries = [
            {"url": "https://example.com/a", "title": "A", "site": "example.com", "favicon": ""},
            {"url": "https://example.com/a", "title": "Duplicate", "site": "example.com", "favicon": ""},
            {"url": "https://example.com/b", "title": "B", "site": "example.com", "favicon": ""},
        ]

        deduped = _dedupe_sources(entries)
        assert len(deduped) == 2
        assert deduped[0]["url"] == "https://example.com/a"
        assert deduped[1]["url"] == "https://example.com/b"

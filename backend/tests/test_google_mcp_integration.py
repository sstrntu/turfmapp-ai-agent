"""
Tests for Google MCP integration functionality.

This module tests the Google MCP client and its integration with the chat system.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any, List

from app.services.mcp_client import google_mcp_client
from app.services.chat_service import EnhancedChatService


class TestGoogleMCPClient:
    """Test Google MCP client functionality."""

    @pytest.mark.asyncio
    async def test_gmail_recent_success(self):
        """Test successful Gmail recent messages retrieval."""
        mock_response = {
            "success": True,
            "response": "Recent emails:\n1. From: test@example.com - Subject: Test Email\n2. From: work@company.com - Subject: Meeting Update",
            "data": [
                {"from": "test@example.com", "subject": "Test Email", "snippet": "This is a test"},
                {"from": "work@company.com", "subject": "Meeting Update", "snippet": "Meeting at 2pm"}
            ]
        }
        
        with patch.object(google_mcp_client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            
            result = await google_mcp_client.call_tool('gmail_recent', {"user_id": "test-123", "max_results": 5})
            
            assert result["success"] is True
            assert "Recent emails:" in result["response"]
            assert len(result["data"]) == 2
            mock_call.assert_called_once_with('gmail_recent', {"user_id": "test-123", "max_results": 5})

    @pytest.mark.asyncio
    async def test_gmail_search_success(self):
        """Test successful Gmail search functionality."""
        mock_response = {
            "success": True,
            "response": "Found 3 emails matching 'meeting':\n1. Meeting reminder - 2 hours ago\n2. Team meeting notes - 1 day ago",
            "data": [
                {"from": "calendar@company.com", "subject": "Meeting reminder", "snippet": "Don't forget about the meeting"},
                {"from": "team@company.com", "subject": "Team meeting notes", "snippet": "Here are the notes from our meeting"}
            ]
        }
        
        with patch.object(google_mcp_client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            
            result = await google_mcp_client.call_tool('gmail_search', {
                "user_id": "test-123", 
                "query": "meeting", 
                "max_results": 10
            })
            
            assert result["success"] is True
            assert "Found 3 emails" in result["response"]
            assert "meeting" in result["response"].lower()

    @pytest.mark.asyncio
    async def test_calendar_upcoming_success(self):
        """Test successful Calendar upcoming events retrieval."""
        mock_response = {
            "success": True,
            "response": "Upcoming events:\n1. Team Standup - Today 10:00 AM\n2. Client Meeting - Tomorrow 2:00 PM",
            "data": [
                {"title": "Team Standup", "start": "2025-09-07T10:00:00", "location": "Office"},
                {"title": "Client Meeting", "start": "2025-09-08T14:00:00", "location": "Conference Room"}
            ]
        }
        
        with patch.object(google_mcp_client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            
            result = await google_mcp_client.call_tool('calendar_upcoming', {"user_id": "test-123", "max_results": 5})
            
            assert result["success"] is True
            assert "Upcoming events:" in result["response"]
            assert "Team Standup" in result["response"]
            assert len(result["data"]) == 2

    @pytest.mark.asyncio
    async def test_drive_list_files_success(self):
        """Test successful Drive file listing."""
        mock_response = {
            "success": True,
            "response": "Your recent files:\n1. Project Plan.docx - Modified 2 hours ago\n2. Budget 2025.xlsx - Modified yesterday",
            "data": [
                {"name": "Project Plan.docx", "type": "document", "modified": "2025-09-07T10:00:00"},
                {"name": "Budget 2025.xlsx", "type": "spreadsheet", "modified": "2025-09-06T15:30:00"}
            ]
        }
        
        with patch.object(google_mcp_client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            
            result = await google_mcp_client.call_tool('drive_list_files', {"user_id": "test-123", "max_results": 10})
            
            assert result["success"] is True
            assert "Your recent files:" in result["response"]
            assert "Project Plan.docx" in result["response"]

    @pytest.mark.asyncio
    async def test_mcp_tool_error_handling(self):
        """Test MCP tool error handling."""
        mock_response = {
            "success": False,
            "error": "Gmail API authentication failed",
            "response": ""
        }
        
        with patch.object(google_mcp_client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            
            result = await google_mcp_client.call_tool('gmail_recent', {"user_id": "test-123"})
            
            assert result["success"] is False
            assert "authentication failed" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_invalid_tool_name(self):
        """Test handling of invalid tool names."""
        with patch.object(google_mcp_client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = ValueError("Unknown tool: invalid_tool")
            
            with pytest.raises(ValueError, match="Unknown tool"):
                await google_mcp_client.call_tool('invalid_tool', {"user_id": "test-123"})


class TestGoogleMCPChatIntegration:
    """Test Google MCP integration with chat system."""

    @pytest.mark.asyncio
    async def test_chat_with_gmail_tool_activation(self):
        """Test chat request with Gmail tool explicitly activated."""
        chat_service = EnhancedChatService()
        
        # Mock Google MCP response
        mock_mcp_response = {
            "success": True,
            "response": "📧 **Gmail**: You have 3 new emails:\n1. From: boss@company.com - Subject: Urgent: Project Update\n2. From: client@business.com - Subject: Meeting Confirmation",
            "tools_used": ["gmail_recent"],
            "sources": []
        }
        
        with patch.object(chat_service, '_handle_google_mcp_request', new_callable=AsyncMock) as mock_handle, \
             patch.object(chat_service, 'create_conversation', return_value="conv-123"), \
             patch.object(chat_service, 'get_conversation_history', return_value=[]), \
             patch.object(chat_service, 'save_message_to_conversation', return_value=True):
            
            mock_handle.return_value = mock_mcp_response
            
            # Simulate tools parameter with Gmail activated
            result = await chat_service.process_chat_request(
                message="What are my latest emails?",
                user_id="user-456",
                conversation_id=None,
                tools=[{
                    "type": "google_mcp",
                    "enabled_tools": {
                        "gmail": True,
                        "calendar": False,
                        "drive": False
                    }
                }]
            )
            
            assert result["assistant_message"]["content"] == mock_mcp_response["response"]
            assert "📧 **Gmail**" in result["assistant_message"]["content"]
            mock_handle.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_with_multiple_google_tools(self):
        """Test chat request with multiple Google tools activated."""
        chat_service = EnhancedChatService()
        
        mock_mcp_response = {
            "success": True,
            "response": "📧 **Gmail**: 2 new emails\n\n📅 **Calendar**: Meeting at 3pm today\n\n💾 **Drive**: 5 recent files",
            "tools_used": ["gmail_recent", "calendar_upcoming", "drive_list_files"],
            "sources": []
        }
        
        with patch.object(chat_service, '_handle_google_mcp_request', new_callable=AsyncMock) as mock_handle, \
             patch.object(chat_service, 'create_conversation', return_value="conv-123"), \
             patch.object(chat_service, 'get_conversation_history', return_value=[]), \
             patch.object(chat_service, 'save_message_to_conversation', return_value=True):
            
            mock_handle.return_value = mock_mcp_response
            
            result = await chat_service.process_chat_request(
                message="Show me my emails, calendar, and files",
                user_id="user-456",
                conversation_id=None,
                tools=[{
                    "type": "google_mcp",
                    "enabled_tools": {
                        "gmail": True,
                        "calendar": True,
                        "drive": True
                    }
                }]
            )
            
            assert "📧 **Gmail**" in result["assistant_message"]["content"]
            assert "📅 **Calendar**" in result["assistant_message"]["content"] 
            assert "💾 **Drive**" in result["assistant_message"]["content"]

    @pytest.mark.asyncio
    async def test_google_mcp_fallback_to_regular_chat(self):
        """Test fallback to regular chat when Google MCP fails."""
        chat_service = EnhancedChatService()
        
        # Mock MCP failure
        mock_mcp_response = {"success": False, "response": "Google services unavailable"}
        
        # Mock regular API response
        mock_api_response = {
            "id": "resp-789",
            "status": "completed", 
            "output_text": "I can help you with general questions, but I can't access your personal Gmail right now."
        }
        
        with patch.object(chat_service, '_handle_google_mcp_request', new_callable=AsyncMock) as mock_handle, \
             patch.object(chat_service, 'call_responses_api', new_callable=AsyncMock) as mock_api, \
             patch.object(chat_service, 'create_conversation', return_value="conv-123"), \
             patch.object(chat_service, 'get_conversation_history', return_value=[]), \
             patch.object(chat_service, 'save_message_to_conversation', return_value=True):
            
            mock_handle.return_value = mock_mcp_response
            mock_api.return_value = mock_api_response
            
            result = await chat_service.process_chat_request(
                message="Check my emails",
                user_id="user-456", 
                conversation_id=None,
                tools=[{
                    "type": "google_mcp",
                    "enabled_tools": {"gmail": True, "calendar": False, "drive": False}
                }]
            )
            
            # Should fall back to regular API call
            assert "can't access your personal Gmail" in result["assistant_message"]["content"]
            mock_api.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_gmail_search_query(self):
        """Test Gmail search query extraction from user messages."""
        chat_service = EnhancedChatService()
        
        test_cases = [
            ("find emails about project", "project"),
            ("search for emails from john", "emails from john"),
            ("show me emails about meeting", "meeting"),
            ("emails from last week about budget", "last week about budget"),
            ("my emails", "")  # Should handle empty case
        ]
        
        for user_message, expected in test_cases:
            result = chat_service._extract_gmail_search_query(user_message)
            if expected:
                assert expected in result.lower()
            else:
                # For empty case like "my emails", it should return empty string after prefix removal
                assert result == ""


class TestGoogleMCPEdgeCases:
    """Test Google MCP edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_empty_google_tools_request(self):
        """Test request with Google MCP type but no tools enabled."""
        chat_service = EnhancedChatService()
        
        with patch.object(chat_service, 'call_responses_api', new_callable=AsyncMock) as mock_api, \
             patch.object(chat_service, 'create_conversation', return_value="conv-123"), \
             patch.object(chat_service, 'get_conversation_history', return_value=[]), \
             patch.object(chat_service, 'save_message_to_conversation', return_value=True):
            
            mock_api.return_value = {"id": "resp-123", "status": "completed", "output_text": "How can I help you?"}
            
            result = await chat_service.process_chat_request(
                message="Hello",
                user_id="user-456",
                conversation_id=None,
                tools=[{
                    "type": "google_mcp",
                    "enabled_tools": {
                        "gmail": False,
                        "calendar": False,
                        "drive": False
                    }
                }]
            )
            
            # Should skip Google MCP and use regular API
            mock_api.assert_called_once()
            assert "How can I help you?" in result["assistant_message"]["content"]

    @pytest.mark.asyncio
    async def test_malformed_google_mcp_request(self):
        """Test handling of malformed Google MCP requests."""
        chat_service = EnhancedChatService()
        
        with patch.object(chat_service, 'call_responses_api', new_callable=AsyncMock) as mock_api, \
             patch.object(chat_service, 'create_conversation', return_value="conv-123"), \
             patch.object(chat_service, 'get_conversation_history', return_value=[]), \
             patch.object(chat_service, 'save_message_to_conversation', return_value=True):
            
            mock_api.return_value = {"id": "resp-123", "status": "completed", "output_text": "Response"}
            
            # Malformed tools parameter
            result = await chat_service.process_chat_request(
                message="Test message",
                user_id="user-456",
                conversation_id=None,
                tools=[{
                    "type": "google_mcp"
                    # Missing enabled_tools
                }]
            )
            
            # Should handle gracefully and fall back to regular API
            mock_api.assert_called_once()
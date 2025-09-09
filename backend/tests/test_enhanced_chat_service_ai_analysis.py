"""
Tests for Enhanced Chat Service AI Analysis functionality.

This module tests the new AI analysis features for Google MCP tool results.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any, List
import json

from app.services.chat_service import EnhancedChatService


class TestEnhancedChatServiceAIAnalysis:
    """Test suite for AI analysis functionality in Google MCP requests."""

    @pytest.fixture
    def chat_service(self):
        return EnhancedChatService()

    @pytest.fixture
    def mock_gmail_tool_result(self):
        """Mock Gmail tool result with email data."""
        return {
            "success": True,
            "response": "📧 **Found 2 emails:** 1. **Moe Kuwayama** 📄 Re: Made in J.League | Episode 2&3 📅 Thu, 28 Aug 2025 📝 **Content:** Hi Trisikh-san, Thank you for sending the draft. I've just added the comment to each...",
            "tool": "gmail_recent"
        }

    @pytest.fixture
    def mock_calendar_tool_result(self):
        """Mock Calendar tool result with event data."""
        return {
            "success": True,
            "response": "📅 **Upcoming events (next 7 days):** 1. **Team Meeting** 🕐 2025-01-15T10:00:00Z",
            "tool": "calendar_upcoming_events"
        }

    @pytest.mark.asyncio
    async def test_google_mcp_with_ai_analysis_gmail(self, chat_service, mock_gmail_tool_result):
        """Test Google MCP request with AI analysis of Gmail results."""
        
        mock_client = AsyncMock()
        mock_client.call_tool = AsyncMock(return_value=mock_gmail_tool_result)
        
        mock_analysis_response = {
            "id": "resp_test123",
            "status": "completed",
            "output": [
                {
                    "content": [
                        {
                            "text": "Your latest email is from Moe Kuwayama about the Made in J.League project. He's thanking you for the draft and mentioning he added comments to each section."
                        }
                    ]
                }
            ]
        }
        
        # Use a proper UUID format for user_id
        user_id = "550e8400-e29b-41d4-a716-446655440000"
        
        with patch('app.services.mcp_client.google_mcp_client', mock_client), \
             patch('app.services.chat_service.google_mcp_client', mock_client), \
             patch.object(chat_service, 'call_responses_api', new_callable=AsyncMock) as mock_api:
            
            mock_api.return_value = mock_analysis_response
            
            result = await chat_service._handle_google_mcp_request(
                user_message="what's my latest email about?",
                conversation_history=[],
                user_id=user_id,
                enabled_tools={"gmail": True, "calendar": False, "drive": False}
            )
            
            assert result["success"] is True
            assert "Moe Kuwayama" in result["response"]
            assert "Made in J.League" in result["response"]
            assert result["tools_used"] == ["gmail_recent"]
            
            # Verify AI analysis was called (twice: once for tool selection, once for analysis)
            assert mock_api.call_count == 2

    @pytest.mark.asyncio
    async def test_calendar_tool_name_correction(self, chat_service, mock_calendar_tool_result):
        """Test that calendar tool uses correct name 'calendar_upcoming_events'."""
        
        mock_client = AsyncMock()
        mock_client.call_tool = AsyncMock(return_value=mock_calendar_tool_result)
        
        mock_analysis_response = {
            "id": "resp_cal123",
            "status": "completed",
            "output": [
                {
                    "content": [
                        {
                            "text": "You have a Team Meeting scheduled for January 15th at 10:00 AM."
                        }
                    ]
                }
            ]
        }
        
        with patch('app.services.mcp_client.google_mcp_client', mock_client), \
             patch('app.services.chat_service.google_mcp_client', mock_client), \
             patch.object(chat_service, 'call_responses_api', new_callable=AsyncMock) as mock_api:
            
            mock_api.return_value = mock_analysis_response
            
            result = await chat_service._handle_google_mcp_request(
                user_message="what are my upcoming meetings?",
                conversation_history=[],
                user_id="550e8400-e29b-41d4-a716-446655440000",
                enabled_tools={"gmail": False, "calendar": True, "drive": False}
            )
            
            assert result["success"] is True
            
            # Verify the correct tool name was called
            mock_client.call_tool.assert_called_once()
            call_args = mock_client.call_tool.call_args
            assert call_args[0][0] == "calendar_upcoming_events"

    @pytest.mark.asyncio
    async def test_multiple_tools_ai_analysis(self, chat_service, mock_gmail_tool_result, mock_calendar_tool_result):
        """Test AI analysis with multiple Google tools."""
        
        mock_client = AsyncMock()
        
        def mock_call_tool(tool_name, params):
            if tool_name == "gmail_search":
                return mock_gmail_tool_result
            elif tool_name == "calendar_upcoming_events":
                return mock_calendar_tool_result
            else:
                return {"success": False, "error": "Unknown tool"}
        
        mock_client.call_tool = AsyncMock(side_effect=mock_call_tool)
        
        mock_analysis_response = {
            "id": "resp_multi123",
            "status": "completed",
            "output": [
                {
                    "content": [
                        {
                            "text": "You have recent emails from Moe about the J.League project, and an upcoming Team Meeting on January 15th."
                        }
                    ]
                }
            ]
        }
        
        with patch('app.services.mcp_client.google_mcp_client', mock_client), \
             patch('app.services.chat_service.google_mcp_client', mock_client), \
             patch.object(chat_service, 'call_responses_api', new_callable=AsyncMock) as mock_api:
            
            mock_api.return_value = mock_analysis_response
            
            result = await chat_service._handle_google_mcp_request(
                user_message="what do I need to know about my schedule and emails?",
                conversation_history=[],
                user_id="550e8400-e29b-41d4-a716-446655440000",
                enabled_tools={"gmail": True, "calendar": True, "drive": False}
            )
            
            assert result["success"] is True
            assert "emails from Moe" in result["response"]
            assert "Team Meeting" in result["response"]
            assert len(result["tools_used"]) == 2
            assert "gmail_search" in result["tools_used"]
            assert "calendar_upcoming_events" in result["tools_used"]

    @pytest.mark.asyncio
    async def test_ai_analysis_fallback_on_failure(self, chat_service, mock_gmail_tool_result):
        """Test fallback when AI analysis fails."""
        
        mock_client = AsyncMock()
        mock_client.call_tool = AsyncMock(return_value=mock_gmail_tool_result)
        
        with patch('app.services.mcp_client.google_mcp_client', mock_client), \
             patch('app.services.chat_service.google_mcp_client', mock_client), \
             patch.object(chat_service, 'call_responses_api', new_callable=AsyncMock) as mock_api:
            
            mock_api.side_effect = Exception("API failed")
            
            result = await chat_service._handle_google_mcp_request(
                user_message="what's my latest email about?",
                conversation_history=[],
                user_id="550e8400-e29b-41d4-a716-446655440000",
                enabled_tools={"gmail": True, "calendar": False, "drive": False}
            )
            
            assert result["success"] is True
            # Should fall back to basic formatting
            assert "📧 **Gmail**:" in result["response"]
            assert mock_gmail_tool_result["response"] in result["response"]

    @pytest.mark.asyncio
    async def test_ai_analysis_prompt_structure(self, chat_service, mock_gmail_tool_result):
        """Test the structure of the AI analysis prompt."""
        
        mock_client = AsyncMock()
        mock_client.call_tool = AsyncMock(return_value=mock_gmail_tool_result)
        
        with patch('app.services.mcp_client.google_mcp_client', mock_client), \
             patch('app.services.chat_service.google_mcp_client', mock_client), \
             patch.object(chat_service, 'call_responses_api', new_callable=AsyncMock) as mock_api:
            
            mock_api.return_value = {
                "id": "resp_test",
                "status": "completed",
                "output": [{"content": [{"text": "Test response"}]}]
            }
            
            user_question = "what's my latest email about?"
            await chat_service._handle_google_mcp_request(
                user_message=user_question,
                conversation_history=[],
                user_id="550e8400-e29b-41d4-a716-446655440000",
                enabled_tools={"gmail": True, "calendar": False, "drive": False}
            )
            
            call_args = mock_api.call_args[1]
            
            # Verify messages structure instead of system_prompt
            messages = call_args["messages"]
            assert len(messages) >= 1
            system_message = next((msg for msg in messages if msg["role"] == "system"), None)
            assert system_message is not None
            prompt = system_message["content"]
            assert f"User Question: {user_question}" in prompt
            assert "Retrieved Data from Google Services:" in prompt
            assert "Please analyze the retrieved data" in prompt

    @pytest.mark.asyncio
    async def test_enhanced_debugging_logs(self, chat_service, mock_gmail_tool_result):
        """Test enhanced debugging functionality."""
        
        mock_client = AsyncMock()
        mock_client.call_tool = AsyncMock(return_value=mock_gmail_tool_result)
        
        with patch('app.services.chat_service.google_mcp_client', mock_client), \
             patch.object(chat_service, 'call_responses_api', new_callable=AsyncMock) as mock_api, \
             patch('builtins.print') as mock_print:
            
            mock_api.return_value = {
                "id": "resp_test",
                "status": "completed",
                "output": [{"content": [{"text": "Test response"}]}]
            }
            
            await chat_service._handle_google_mcp_request(
                user_message="test message",
                conversation_history=[],
                user_id="550e8400-e29b-41d4-a716-446655440000",
                enabled_tools={"gmail": True, "calendar": False, "drive": False}
            )
            
            # Check debugging prints were called
            print_calls = [str(call[0][0]) for call in mock_print.call_args_list if call[0]]
            debug_messages = [msg for msg in print_calls if "🔧" in msg or "Raw result" in msg]
            assert len(debug_messages) > 0

    @pytest.mark.asyncio
    async def test_gmail_recent_tool_selection_for_latest_email(self, chat_service):
        """Test that AI correctly selects gmail_recent for 'latest email' queries."""
        
        # Mock successful Gmail API response
        mock_gmail_result = {
            "success": True,
            "response": "📧 **Your 1 most recent emails:**\n\n1. **BrandMentions** - Puma Football - 654 new mentions\n   _Mon, 08 Sep 2025 06:49:09 +0000 (UTC)_",
            "tool": "gmail_recent"
        }
        
        # Mock AI analysis response 
        mock_analysis_response = {
            "id": "resp_latest123",
            "status": "completed", 
            "output": [
                {
                    "content": [
                        {
                            "text": "Your latest email is from BrandMentions about Puma Football, mentioning that there are 654 new mentions."
                        }
                    ]
                }
            ]
        }
        
        # Mock AI tool selection response
        mock_tool_selection_response = {
            "id": "resp_selection",
            "status": "completed",
            "output": [
                {
                    "type": "function_call",
                    "status": "completed",
                    "name": "gmail_recent",
                    "arguments": '{"max_results": 1}'
                }
            ]
        }
        
        mock_client = AsyncMock()
        mock_client.call_tool = AsyncMock(return_value=mock_gmail_result)
        
        with patch('app.services.mcp_client.google_mcp_client', mock_client), \
             patch('app.services.chat_service.google_mcp_client', mock_client), \
             patch.object(chat_service, 'call_responses_api', new_callable=AsyncMock) as mock_api:
            
            # First call returns tool selection, second call returns analysis
            mock_api.side_effect = [mock_tool_selection_response, mock_analysis_response]
            
            result = await chat_service._handle_google_mcp_request(
                user_message="what's my latest email about?",
                conversation_history=[],
                user_id="user-123",
                enabled_tools={"gmail": True, "calendar": False, "drive": False}
            )
            
            assert result["success"] is True
            assert "BrandMentions" in result["response"]
            assert "Puma Football" in result["response"]
            assert "654 new mentions" in result["response"]
            assert result["tools_used"] == ["gmail_recent"]
            
            # Verify gmail_recent was called with max_results=1
            mock_client.call_tool.assert_called_with("gmail_recent", {"user_id": "user-123", "max_results": 1})

    @pytest.mark.asyncio
    async def test_empty_ai_response_fallback(self, chat_service, mock_gmail_tool_result):
        """Test handling when AI returns empty response."""
        
        mock_client = AsyncMock()
        mock_client.call_tool = AsyncMock(return_value=mock_gmail_tool_result)
        
        with patch('app.services.mcp_client.google_mcp_client', mock_client), \
             patch('app.services.chat_service.google_mcp_client', mock_client), \
             patch.object(chat_service, 'call_responses_api', new_callable=AsyncMock) as mock_api:
            
            mock_api.return_value = {
                "id": "resp_empty",
                "status": "completed",
                "output": [{"content": [{"text": ""}]}]
            }
            
            result = await chat_service._handle_google_mcp_request(
                user_message="test question",
                conversation_history=[],
                user_id="550e8400-e29b-41d4-a716-446655440000",
                enabled_tools={"gmail": True, "calendar": False, "drive": False}
            )
            
            assert result["success"] is True
            assert "📧 **Gmail**:" in result["response"]

    @pytest.mark.asyncio
    async def test_no_successful_tools_error_handling(self, chat_service):
        """Test handling when no tools return successful results."""
        
        mock_client = AsyncMock()
        mock_client.call_tool = AsyncMock(return_value={
            "success": False,
            "error": "No access to Gmail",
            "tool": "gmail_recent"
        })
        
        with patch('app.services.chat_service.google_mcp_client', mock_client):
            
            result = await chat_service._handle_google_mcp_request(
                user_message="what's my latest email?",
                conversation_history=[],
                user_id="550e8400-e29b-41d4-a716-446655440000",
                enabled_tools={"gmail": True, "calendar": False, "drive": False}
            )
            
            assert result["success"] is False
            assert "couldn't retrieve data" in result["response"]

    @pytest.mark.asyncio
    async def test_non_dict_tool_result_handling(self, chat_service):
        """Test robustness when tool returns unexpected result type."""
        
        mock_client = AsyncMock()
        mock_client.call_tool = AsyncMock(return_value="unexpected string result")
        
        with patch('app.services.chat_service.google_mcp_client', mock_client), \
             patch('builtins.print') as mock_print:
            
            result = await chat_service._handle_google_mcp_request(
                user_message="test question",
                conversation_history=[],
                user_id="550e8400-e29b-41d4-a716-446655440000",
                enabled_tools={"gmail": True, "calendar": False, "drive": False}
            )
            
            # Should handle gracefully
            assert result["success"] is False
            
            # Check that type debugging was logged
            print_calls = [str(call) for call in mock_print.call_args_list]
            type_debug_calls = [call for call in print_calls if "Result type" in call]
            assert len(type_debug_calls) > 0

    @pytest.mark.asyncio
    async def test_ai_analysis_with_drive_data(self, chat_service):
        """Test AI analysis with Drive tool data."""
        
        mock_drive_result = {
            "success": True,
            "response": "📁 **Found 5 files in Google Drive:** 1. 📄 **Project Draft.docx** 📅 Modified: 2025-01-10",
            "tool": "drive_list_files"
        }
        
        mock_client = AsyncMock()
        mock_client.call_tool = AsyncMock(return_value=mock_drive_result)
        
        mock_analysis_response = {
            "id": "resp_drive123",
            "status": "completed",
            "output": [
                {
                    "content": [
                        {
                            "text": "You have 5 files in your Google Drive, including a Project Draft document that was recently modified on January 10th."
                        }
                    ]
                }
            ]
        }
        
        with patch('app.services.mcp_client.google_mcp_client', mock_client), \
             patch('app.services.chat_service.google_mcp_client', mock_client), \
             patch.object(chat_service, 'call_responses_api', new_callable=AsyncMock) as mock_api:
            
            mock_api.return_value = mock_analysis_response
            
            result = await chat_service._handle_google_mcp_request(
                user_message="what files do I have in my drive?",
                conversation_history=[],
                user_id="550e8400-e29b-41d4-a716-446655440000",
                enabled_tools={"gmail": False, "calendar": False, "drive": True}
            )
            
            assert result["success"] is True
            assert "Project Draft" in result["response"]
            assert result["tools_used"] == ["drive_list_files"]
            
            # Verify Drive data was included in AI analysis
            call_args = mock_api.call_args[1]["messages"]
            system_message = next((msg for msg in call_args if msg["role"] == "system"), None)
            assert system_message is not None
            assert "Drive:" in system_message["content"]


class TestEnhancedChatServiceDebuggingImprovements:
    """Test suite for debugging and logging improvements."""

    @pytest.fixture
    def chat_service(self):
        return EnhancedChatService()

    @pytest.mark.asyncio
    async def test_detailed_result_logging(self, chat_service):
        """Test that detailed result logging is implemented."""
        
        mock_tool_result = {
            "success": True,
            "response": "Test tool response",
            "tool": "gmail_recent"
        }
        
        mock_client = AsyncMock()
        mock_client.call_tool = AsyncMock(return_value=mock_tool_result)
        
        with patch('app.services.chat_service.google_mcp_client', mock_client), \
             patch.object(chat_service, 'call_responses_api', new_callable=AsyncMock) as mock_api, \
             patch('builtins.print') as mock_print:
            
            mock_api.return_value = {
                "id": "resp_ai",
                "status": "completed", 
                "output": [{"content": [{"text": "AI response"}]}]
            }
            
            await chat_service._handle_google_mcp_request(
                user_message="test message",
                conversation_history=[],
                user_id="550e8400-e29b-41d4-a716-446655440000",
                enabled_tools={"gmail": True, "calendar": False, "drive": False}
            )
            
            # Check for specific debug patterns
            print_calls = [str(call[0][0]) for call in mock_print.call_args_list if call[0]]
            
            # Should log raw result
            raw_result_logs = [call for call in print_calls if "Raw result from" in call]
            assert len(raw_result_logs) > 0
            
            # Should log result type
            type_logs = [call for call in print_calls if "Result type" in call]
            assert len(type_logs) > 0

    @pytest.mark.asyncio
    async def test_tool_parameter_logging(self, chat_service):
        """Test that tool parameters are logged for debugging."""
        
        mock_tool_result = {"success": True, "response": "Test response", "tool": "gmail_recent"}
        
        mock_client = AsyncMock()
        mock_client.call_tool = AsyncMock(return_value=mock_tool_result)
        
        with patch('app.services.chat_service.google_mcp_client', mock_client), \
             patch.object(chat_service, 'call_responses_api', new_callable=AsyncMock) as mock_api, \
             patch('builtins.print') as mock_print:
            
            mock_api.return_value = {
                "id": "resp_ai",
                "status": "completed", 
                "output": [{"content": [{"text": "AI response"}]}]
            }
            
            await chat_service._handle_google_mcp_request(
                user_message="show my recent emails",
                conversation_history=[],
                user_id="550e8400-e29b-41d4-a716-446655440000",
                enabled_tools={"gmail": True, "calendar": False, "drive": False}
            )
            
            # Check for tool calling logs
            print_calls = [str(call[0][0]) for call in mock_print.call_args_list if call[0]]
            calling_logs = [call for call in print_calls if "🔧 Calling" in call and "with params" in call]
            assert len(calling_logs) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
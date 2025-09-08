"""
Tests for MCP Client Simple debugging improvements.

This module tests the enhanced debugging functionality added to the calendar tools.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any
import traceback

from app.services.mcp_client_simple import SimplifiedGoogleMCPClient


class TestMCPClientSimpleDebugging:
    """Test suite for debugging improvements in MCP Client Simple."""

    @pytest.fixture
    def client(self):
        return SimplifiedGoogleMCPClient()

    @pytest.fixture
    def mock_credentials(self):
        """Mock Google credentials."""
        return Mock()

    @pytest.mark.asyncio
    async def test_calendar_tool_debugging_logs(self, client, mock_credentials):
        """Test that calendar tool handler includes proper debugging logs."""
        
        mock_calendar_events = {
            'events': [
                {
                    'summary': 'Test Meeting',
                    'start': {'dateTime': '2025-01-15T10:00:00Z'}
                }
            ]
        }
        
        with patch('app.services.mcp_client_simple.google_oauth_service') as mock_oauth, \
             patch('builtins.print') as mock_print:
            
            mock_oauth.get_calendar_events = AsyncMock(return_value=mock_calendar_events)
            
            result = await client._handle_calendar_tool(
                "calendar_upcoming_events", 
                mock_credentials, 
                {"days": 7}
            )
            
            assert result["success"] is True
            
            # Check that debugging logs were called
            print_calls = [str(call[0][0]) for call in mock_print.call_args_list if call[0]]
            
            # Should log tool handling start
            handling_logs = [call for call in print_calls if "🗓️ Handling calendar tool" in call]
            assert len(handling_logs) > 0
            
            # Should log getting events
            getting_logs = [call for call in print_calls if "🗓️ Getting upcoming calendar events" in call]
            assert len(getting_logs) > 0
            
            # Should log API result
            result_logs = [call for call in print_calls if "🗓️ Calendar API result:" in call]
            assert len(result_logs) > 0
            
            # Should log event count
            count_logs = [call for call in print_calls if "🗓️ Found" in call and "calendar events" in call]
            assert len(count_logs) > 0
            
            # Should log return response
            return_logs = [call for call in print_calls if "✅ Returning calendar response:" in call]
            assert len(return_logs) > 0

    @pytest.mark.asyncio
    async def test_calendar_tool_error_debugging(self, client, mock_credentials):
        """Test debugging logs when calendar tool encounters errors."""
        
        mock_error_result = {'error': 'Insufficient permissions'}
        
        with patch('app.services.mcp_client_simple.google_oauth_service') as mock_oauth, \
             patch('builtins.print') as mock_print:
            
            mock_oauth.get_calendar_events = AsyncMock(return_value=mock_error_result)
            
            result = await client._handle_calendar_tool(
                "calendar_upcoming_events", 
                mock_credentials, 
                {"days": 7}
            )
            
            assert result["success"] is False
            
            # Check error debugging logs
            print_calls = [str(call[0][0]) for call in mock_print.call_args_list if call[0]]
            error_logs = [call for call in print_calls if "❌ Calendar API error:" in call]
            assert len(error_logs) > 0

    @pytest.mark.asyncio
    async def test_calendar_tool_exception_debugging(self, client, mock_credentials):
        """Test debugging logs when calendar tool throws exception."""
        
        with patch('app.services.mcp_client_simple.google_oauth_service') as mock_oauth, \
             patch('builtins.print') as mock_print:
            
            mock_oauth.get_calendar_events = AsyncMock(side_effect=Exception("API connection failed"))
            
            result = await client._handle_calendar_tool(
                "calendar_upcoming_events", 
                mock_credentials, 
                {"days": 7}
            )
            
            assert result["success"] is False
            assert "Calendar tool error: API connection failed" in result["error"]
            
            # Check exception debugging logs
            print_calls = [str(call[0][0]) for call in mock_print.call_args_list if call[0]]
            
            exception_logs = [call for call in print_calls if "❌ Calendar tool exception:" in call]
            assert len(exception_logs) > 0
            
            traceback_logs = [call for call in print_calls if "❌ Calendar tool traceback:" in call]
            assert len(traceback_logs) > 0

    @pytest.mark.asyncio
    async def test_calendar_list_events_debugging(self, client, mock_credentials):
        """Test debugging for calendar_list_events tool."""
        
        mock_calendar_events = {
            'events': [
                {
                    'summary': 'Important Meeting',
                    'start': {'dateTime': '2025-01-20T14:00:00Z'},
                    'location': 'Conference Room A'
                }
            ]
        }
        
        with patch('app.services.mcp_client_simple.google_oauth_service') as mock_oauth, \
             patch('builtins.print') as mock_print:
            
            mock_oauth.get_calendar_events = AsyncMock(return_value=mock_calendar_events)
            
            result = await client._handle_calendar_tool(
                "calendar_list_events", 
                mock_credentials, 
                {"calendar_id": "primary", "max_results": 10}
            )
            
            assert result["success"] is True
            assert "Important Meeting" in result["response"]
            assert "Conference Room A" in result["response"]
            
            # Verify debugging was called
            print_calls = [str(call[0][0]) for call in mock_print.call_args_list if call[0]]
            handling_logs = [call for call in print_calls if "🗓️ Handling calendar tool" in call]
            assert len(handling_logs) > 0

    @pytest.mark.asyncio
    async def test_unknown_calendar_tool_debugging(self, client, mock_credentials):
        """Test debugging for unknown calendar tool."""
        
        with patch('builtins.print') as mock_print:
            
            result = await client._handle_calendar_tool(
                "unknown_calendar_tool", 
                mock_credentials, 
                {}
            )
            
            assert result["success"] is False
            assert "Unknown Calendar tool: unknown_calendar_tool" in result["error"]
            
            # Should still log the handling attempt
            print_calls = [str(call[0][0]) for call in mock_print.call_args_list if call[0]]
            handling_logs = [call for call in print_calls if "🗓️ Handling calendar tool" in call]
            assert len(handling_logs) > 0

    @pytest.mark.asyncio
    async def test_calendar_tool_no_events_debugging(self, client, mock_credentials):
        """Test debugging when no calendar events are found."""
        
        mock_empty_result = {'events': []}
        
        with patch('app.services.mcp_client_simple.google_oauth_service') as mock_oauth, \
             patch('builtins.print') as mock_print:
            
            mock_oauth.get_calendar_events = AsyncMock(return_value=mock_empty_result)
            
            result = await client._handle_calendar_tool(
                "calendar_upcoming_events", 
                mock_credentials, 
                {"days": 7}
            )
            
            assert result["success"] is True
            assert "No upcoming events" in result["response"]
            
            # Should log 0 events found
            print_calls = [str(call[0][0]) for call in mock_print.call_args_list if call[0]]
            count_logs = [call for call in print_calls if "🗓️ Found 0 calendar events" in call]
            assert len(count_logs) > 0

    @pytest.mark.asyncio
    async def test_calendar_tool_debugging_with_arguments(self, client, mock_credentials):
        """Test that tool arguments are properly logged."""
        
        mock_calendar_events = {'events': []}
        
        with patch('app.services.mcp_client_simple.google_oauth_service') as mock_oauth, \
             patch('builtins.print') as mock_print:
            
            mock_oauth.get_calendar_events = AsyncMock(return_value=mock_calendar_events)
            
            test_arguments = {"days": 14, "user_id": "test-user-123"}
            
            await client._handle_calendar_tool(
                "calendar_upcoming_events", 
                mock_credentials, 
                test_arguments
            )
            
            # Should log the arguments
            print_calls = [str(call[0][0]) for call in mock_print.call_args_list if call[0]]
            arg_logs = [call for call in print_calls if str(test_arguments) in call]
            assert len(arg_logs) > 0

    @pytest.mark.asyncio
    async def test_calendar_tool_api_result_structure_logging(self, client, mock_credentials):
        """Test that the full API result structure is logged for debugging."""
        
        complex_result = {
            'events': [
                {
                    'summary': 'Complex Meeting',
                    'start': {'dateTime': '2025-01-25T09:00:00Z'},
                    'end': {'dateTime': '2025-01-25T10:00:00Z'},
                    'location': 'Virtual',
                    'description': 'Detailed description'
                }
            ],
            'nextPageToken': 'token123'
        }
        
        with patch('app.services.mcp_client_simple.google_oauth_service') as mock_oauth, \
             patch('builtins.print') as mock_print:
            
            mock_oauth.get_calendar_events = AsyncMock(return_value=complex_result)
            
            await client._handle_calendar_tool(
                "calendar_list_events", 
                mock_credentials, 
                {}
            )
            
            # Should log the complete result structure
            print_calls = [str(call[0][0]) for call in mock_print.call_args_list if call[0]]
            result_logs = [call for call in print_calls if "nextPageToken" in call]
            assert len(result_logs) > 0


class TestMCPClientSimpleCalendarToolFixes:
    """Test suite for calendar tool name fixes and functionality."""

    @pytest.fixture
    def client(self):
        return SimplifiedGoogleMCPClient()

    @pytest.mark.asyncio
    async def test_calendar_upcoming_events_tool_exists(self, client):
        """Test that calendar_upcoming_events tool is properly defined."""
        
        tools = await client.list_tools()
        tool_names = [tool["name"] for tool in tools]
        
        assert "calendar_upcoming_events" in tool_names
        
        # Find the specific tool
        calendar_tool = next(tool for tool in tools if tool["name"] == "calendar_upcoming_events")
        assert "upcoming calendar events" in calendar_tool["description"]

    @pytest.mark.asyncio
    async def test_calendar_tool_mapping(self, client):
        """Test that calendar tools are properly mapped in execute_google_tool."""
        
        # Mock credentials retrieval
        with patch('app.services.mcp_client_simple.get_user_google_credentials') as mock_creds, \
             patch.object(client, '_handle_calendar_tool', new_callable=AsyncMock) as mock_handler:
            
            mock_creds.return_value = Mock()
            mock_handler.return_value = {"success": True, "response": "Test response"}
            
            # Test upcoming_events action maps to calendar_upcoming_events tool
            result = await client.execute_google_tool("upcoming_events", "user123")
            
            assert result["success"] is True
            mock_handler.assert_called_once_with("calendar_upcoming_events", mock_creds.return_value, {"user_id": "user123"})

    @pytest.mark.asyncio
    async def test_calendar_list_events_tool_mapping(self, client):
        """Test that list_events action maps correctly."""
        
        with patch('app.services.mcp_client_simple.get_user_google_credentials') as mock_creds, \
             patch.object(client, '_handle_calendar_tool', new_callable=AsyncMock) as mock_handler:
            
            mock_creds.return_value = Mock()
            mock_handler.return_value = {"success": True, "response": "Test response"}
            
            result = await client.execute_google_tool("list_events", "user123")
            
            assert result["success"] is True
            mock_handler.assert_called_once_with("calendar_list_events", mock_creds.return_value, {"user_id": "user123"})


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
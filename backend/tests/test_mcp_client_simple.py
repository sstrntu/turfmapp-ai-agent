"""
Tests for Simplified MCP Client.

This module tests the Google MCP client functionality, including tool listing,
execution, Gmail, Drive, and Calendar integrations.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any, List

from app.services.mcp_client_simple import (
    SimplifiedGoogleMCPClient, 
    google_mcp_client,
    get_mcp_client,
    execute_gmail_action,
    execute_drive_action,
    execute_calendar_action,
    get_all_google_tools
)


class TestSimplifiedGoogleMCPClient:
    """Test the main MCP client class."""
    
    def test_client_initialization(self):
        """Test client initializes with proper default state."""
        client = SimplifiedGoogleMCPClient()
        
        assert client._tools_cache is None
    
    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        """Test connect and disconnect methods (no-ops)."""
        client = SimplifiedGoogleMCPClient()
        
        # Should not raise any exceptions
        await client.connect()
        await client.disconnect()
    
    @pytest.mark.asyncio
    async def test_list_tools_first_call(self):
        """Test listing tools for the first time."""
        client = SimplifiedGoogleMCPClient()
        
        tools = await client.list_tools()
        
        assert isinstance(tools, list)
        assert len(tools) > 0
        
        # Check that cache was populated
        assert client._tools_cache is not None
        assert len(client._tools_cache) == len(tools)
        
        # Verify tool structure
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
    
    @pytest.mark.asyncio
    async def test_list_tools_cached(self):
        """Test that subsequent calls use cache."""
        client = SimplifiedGoogleMCPClient()
        
        # First call
        tools1 = await client.list_tools()
        cache_after_first = client._tools_cache
        
        # Second call should use cache
        tools2 = await client.list_tools()
        
        assert tools1 is tools2  # Should be the same object reference
        assert client._tools_cache is cache_after_first
    
    @pytest.mark.asyncio
    async def test_list_tools_content(self):
        """Test that all expected tools are present."""
        client = SimplifiedGoogleMCPClient()
        
        tools = await client.list_tools()
        tool_names = [tool["name"] for tool in tools]
        
        # Gmail tools
        assert "gmail_search" in tool_names
        assert "gmail_get_message" in tool_names
        assert "gmail_recent" in tool_names
        assert "gmail_important" in tool_names
        
        # Drive tools
        assert "drive_list_files" in tool_names
        assert "drive_create_folder" in tool_names
        assert "drive_list_folder_files" in tool_names
        
        # Calendar tools
        assert "calendar_list_events" in tool_names
        assert "calendar_upcoming_events" in tool_names


class TestToolExecution:
    """Test tool execution functionality."""
    
    @pytest.mark.asyncio
    async def test_call_tool_missing_user_id(self):
        """Test tool call without user_id."""
        client = SimplifiedGoogleMCPClient()
        
        result = await client.call_tool("gmail_recent", {})
        
        assert result["success"] is False
        assert "user_id is required" in result["error"]
        assert result["tool"] == "gmail_recent"
    
    @pytest.mark.asyncio
    async def test_call_tool_unknown_tool(self):
        """Test calling an unknown tool."""
        client = SimplifiedGoogleMCPClient()
        
        result = await client.call_tool("unknown_tool", {"user_id": "test-123"})
        
        assert result["success"] is False
        assert "Unknown tool" in result["error"]
        assert result["tool"] == "unknown_tool"
    
    @pytest.mark.asyncio
    async def test_call_tool_credentials_failure(self):
        """Test tool call when credentials fail."""
        client = SimplifiedGoogleMCPClient()
        
        with patch('app.services.mcp_client_simple.get_user_google_credentials', new_callable=AsyncMock) as mock_creds:
            mock_creds.side_effect = Exception("Credentials not found")
            
            result = await client.call_tool("gmail_recent", {"user_id": "test-123"})
            
            assert result["success"] is False
            assert "Failed to get Google credentials" in result["error"]
            assert result["tool"] == "gmail_recent"
    
    @pytest.mark.asyncio
    async def test_call_tool_placeholder_account_filtering(self):
        """Test filtering of placeholder account values."""
        client = SimplifiedGoogleMCPClient()
        
        placeholder_accounts = [
            "user's account email",
            "user@example.com", 
            "example@gmail.com",
            "your account"
        ]
        
        for placeholder in placeholder_accounts:
            with patch('app.services.mcp_client_simple.get_user_google_credentials', new_callable=AsyncMock) as mock_creds, \
                 patch.object(client, '_handle_gmail_tool', new_callable=AsyncMock) as mock_handler:
                
                mock_creds.return_value = {"access_token": "fake-token"}
                mock_handler.return_value = {"success": True, "result": "test"}
                
                await client.call_tool("gmail_recent", {
                    "user_id": "test-123",
                    "account": placeholder
                })
                
                # Should call get_user_google_credentials with None account
                mock_creds.assert_called_with("test-123", None)
    
    @pytest.mark.asyncio
    async def test_call_tool_exception_handling(self):
        """Test tool call with unexpected exception."""
        client = SimplifiedGoogleMCPClient()
        
        with patch('app.services.mcp_client_simple.get_user_google_credentials', new_callable=AsyncMock) as mock_creds:
            mock_creds.side_effect = RuntimeError("Unexpected error")
            
            result = await client.call_tool("gmail_recent", {"user_id": "test-123"})
            
            assert result["success"] is False
            assert "Tool execution failed" in result["error"]
            assert result["tool"] == "gmail_recent"


class TestGmailToolHandling:
    """Test Gmail-specific tool handling."""
    
    @pytest.mark.asyncio
    async def test_handle_gmail_tool_recent(self):
        """Test handling gmail_recent tool."""
        client = SimplifiedGoogleMCPClient()
        
        mock_credentials = {"access_token": "fake-token"}
        mock_messages = [
            {"id": "msg1", "snippet": "Test message 1"},
            {"id": "msg2", "snippet": "Test message 2"}
        ]
        
        with patch('app.services.mcp_client_simple.google_oauth_service') as mock_service:
            mock_service.get_gmail_messages.return_value = mock_messages
            
            result = await client._handle_gmail_tool("gmail_recent", mock_credentials, {
                "max_results": 10
            })
            
            assert result["success"] is True
            mock_service.get_gmail_messages.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_gmail_tool_search(self):
        """Test handling gmail_search tool."""
        client = SimplifiedGoogleMCPClient()
        
        mock_credentials = {"access_token": "fake-token"}
        mock_messages = [
            {"id": "msg1", "snippet": "Meeting tomorrow"},
            {"id": "msg2", "snippet": "Project update"}
        ]
        
        with patch('app.services.mcp_client_simple.google_oauth_service') as mock_service:
            mock_service.search_gmail_messages.return_value = mock_messages
            
            result = await client._handle_gmail_tool("gmail_search", mock_credentials, {
                "query": "meeting",
                "max_results": 5
            })
            
            assert result["success"] is True
            mock_service.search_gmail_messages.assert_called_once()
    
    @pytest.mark.asyncio 
    async def test_handle_gmail_tool_get_message(self):
        """Test handling gmail_get_message tool."""
        client = SimplifiedGoogleMCPClient()
        
        mock_credentials = {"access_token": "fake-token"}
        mock_message = {"id": "msg123", "payload": {"body": {"data": "SGVsbG8gV29ybGQ="}}}
        
        with patch('app.services.mcp_client_simple.google_oauth_service') as mock_service:
            mock_service.get_gmail_message_by_id.return_value = mock_message
            
            result = await client._handle_gmail_tool("gmail_get_message", mock_credentials, {
                "message_id": "msg123"
            })
            
            assert result["success"] is True
            mock_service.get_gmail_message_by_id.assert_called_once_with(mock_credentials, "msg123")
    
    @pytest.mark.asyncio
    async def test_handle_gmail_tool_error(self):
        """Test Gmail tool error handling."""
        client = SimplifiedGoogleMCPClient()
        
        mock_credentials = {"access_token": "fake-token"}
        
        with patch('app.services.mcp_client_simple.google_oauth_service') as mock_service:
            mock_service.get_gmail_messages.side_effect = Exception("Gmail API error")
            
            result = await client._handle_gmail_tool("gmail_recent", mock_credentials, {})
            
            assert result["success"] is False
            assert "Gmail API error" in result["error"]
    
    @pytest.mark.asyncio
    async def test_handle_gmail_tool_unknown(self):
        """Test handling unknown Gmail tool."""
        client = SimplifiedGoogleMCPClient()
        
        mock_credentials = {"access_token": "fake-token"}
        
        result = await client._handle_gmail_tool("gmail_unknown", mock_credentials, {})
        
        assert result["success"] is False
        assert "Unknown Gmail action" in result["error"]


class TestDriveToolHandling:
    """Test Google Drive tool handling."""
    
    @pytest.mark.asyncio
    async def test_handle_drive_tool_list_files(self):
        """Test handling drive_list_files tool."""
        client = SimplifiedGoogleMCPClient()
        
        mock_credentials = {"access_token": "fake-token"}
        mock_files = [
            {"id": "file1", "name": "Document1.pdf"},
            {"id": "file2", "name": "Spreadsheet1.xlsx"}
        ]
        
        with patch('app.services.mcp_client_simple.google_oauth_service') as mock_service:
            mock_service.list_drive_files.return_value = mock_files
            
            result = await client._handle_drive_tool("drive_list_files", mock_credentials, {
                "max_results": 10
            })
            
            assert result["success"] is True
            mock_service.list_drive_files.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_drive_tool_create_folder(self):
        """Test handling drive_create_folder tool."""
        client = SimplifiedGoogleMCPClient()
        
        mock_credentials = {"access_token": "fake-token"}
        mock_folder = {"id": "folder123", "name": "New Folder"}
        
        with patch('app.services.mcp_client_simple.google_oauth_service') as mock_service:
            mock_service.create_drive_folder_structure.return_value = mock_folder
            
            result = await client._handle_drive_tool("drive_create_folder", mock_credentials, {
                "folder_path": "Projects/2025"
            })
            
            assert result["success"] is True
            mock_service.create_drive_folder_structure.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_drive_tool_error(self):
        """Test Drive tool error handling."""
        client = SimplifiedGoogleMCPClient()
        
        mock_credentials = {"access_token": "fake-token"}
        
        with patch('app.services.mcp_client_simple.google_oauth_service') as mock_service:
            mock_service.list_drive_files.side_effect = Exception("Drive API error")
            
            result = await client._handle_drive_tool("drive_list_files", mock_credentials, {})
            
            assert result["success"] is False
            assert "Drive API error" in result["error"]


class TestCalendarToolHandling:
    """Test Google Calendar tool handling."""
    
    @pytest.mark.asyncio
    async def test_handle_calendar_tool_list_events(self):
        """Test handling calendar_list_events tool."""
        client = SimplifiedGoogleMCPClient()
        
        mock_credentials = {"access_token": "fake-token"}
        mock_events = [
            {"id": "event1", "summary": "Team Meeting"},
            {"id": "event2", "summary": "Client Call"}
        ]
        
        with patch('app.services.mcp_client_simple.google_oauth_service') as mock_service:
            mock_service.list_calendar_events.return_value = mock_events
            
            result = await client._handle_calendar_tool("calendar_list_events", mock_credentials, {
                "calendar_id": "primary"
            })
            
            assert result["success"] is True
            mock_service.list_calendar_events.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_calendar_tool_upcoming_events(self):
        """Test handling calendar_upcoming_events tool."""
        client = SimplifiedGoogleMCPClient()
        
        mock_credentials = {"access_token": "fake-token"}
        mock_events = [
            {"id": "event1", "summary": "Tomorrow's Meeting"},
            {"id": "event2", "summary": "Next Week's Review"}
        ]
        
        with patch('app.services.mcp_client_simple.google_oauth_service') as mock_service:
            mock_service.get_upcoming_calendar_events.return_value = mock_events
            
            result = await client._handle_calendar_tool("calendar_upcoming_events", mock_credentials, {
                "days": 7
            })
            
            assert result["success"] is True
            mock_service.get_upcoming_calendar_events.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_calendar_tool_error(self):
        """Test Calendar tool error handling."""
        client = SimplifiedGoogleMCPClient()
        
        mock_credentials = {"access_token": "fake-token"}
        
        with patch('app.services.mcp_client_simple.google_oauth_service') as mock_service:
            mock_service.list_calendar_events.side_effect = Exception("Calendar API error")
            
            result = await client._handle_calendar_tool("calendar_list_events", mock_credentials, {})
            
            assert result["success"] is False
            assert "Calendar API error" in result["error"]


class TestOpenAIIntegration:
    """Test OpenAI function format integration."""
    
    @pytest.mark.asyncio
    async def test_get_available_tools_for_openai(self):
        """Test getting tools in OpenAI function format."""
        client = SimplifiedGoogleMCPClient()
        
        tools = await client.get_available_tools_for_openai()
        
        assert isinstance(tools, list)
        assert len(tools) > 0
        
        # Check OpenAI function format
        for tool in tools:
            assert tool["type"] == "function"
            assert "function" in tool
            assert "name" in tool["function"]
            assert "description" in tool["function"]
            assert "parameters" in tool["function"]
    
    @pytest.mark.asyncio
    async def test_execute_google_tool_gmail(self):
        """Test executing Google tool with Gmail action."""
        client = SimplifiedGoogleMCPClient()
        
        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"success": True, "result": "Gmail action executed"}
            
            result = await client.execute_google_tool("gmail_recent", "user-123", max_results=5)
            
            assert result["success"] is True
            mock_call.assert_called_once_with("gmail_recent", {
                "user_id": "user-123",
                "max_results": 5
            })
    
    @pytest.mark.asyncio
    async def test_execute_google_tool_drive(self):
        """Test executing Google tool with Drive action."""
        client = SimplifiedGoogleMCPClient()
        
        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"success": True, "result": "Drive action executed"}
            
            result = await client.execute_google_tool("drive_list_files", "user-456", query="presentations")
            
            assert result["success"] is True
            mock_call.assert_called_once_with("drive_list_files", {
                "user_id": "user-456",
                "query": "presentations"
            })


class TestGlobalFunctions:
    """Test global utility functions."""
    
    @pytest.mark.asyncio
    async def test_get_mcp_client(self):
        """Test getting global MCP client."""
        client = await get_mcp_client()
        
        assert isinstance(client, SimplifiedGoogleMCPClient)
        # Should be the global instance
        assert client is google_mcp_client
    
    @pytest.mark.asyncio
    async def test_execute_gmail_action(self):
        """Test execute_gmail_action function."""
        with patch.object(google_mcp_client, 'execute_google_tool', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {"success": True, "result": "Gmail executed"}
            
            result = await execute_gmail_action("gmail_recent", "user-789", max_results=3)
            
            assert result["success"] is True
            mock_execute.assert_called_once_with("gmail_recent", "user-789", max_results=3)
    
    @pytest.mark.asyncio
    async def test_execute_drive_action(self):
        """Test execute_drive_action function."""
        with patch.object(google_mcp_client, 'execute_google_tool', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {"success": True, "result": "Drive executed"}
            
            result = await execute_drive_action("drive_list_files", "user-101", query="documents")
            
            assert result["success"] is True
            mock_execute.assert_called_once_with("drive_list_files", "user-101", query="documents")
    
    @pytest.mark.asyncio
    async def test_execute_calendar_action(self):
        """Test execute_calendar_action function."""
        with patch.object(google_mcp_client, 'execute_google_tool', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {"success": True, "result": "Calendar executed"}
            
            result = await execute_calendar_action("calendar_list_events", "user-202", calendar_id="primary")
            
            assert result["success"] is True
            mock_execute.assert_called_once_with("calendar_list_events", "user-202", calendar_id="primary")
    
    @pytest.mark.asyncio
    async def test_get_all_google_tools(self):
        """Test get_all_google_tools function."""
        with patch.object(google_mcp_client, 'list_tools', new_callable=AsyncMock) as mock_list:
            mock_tools = [
                {"name": "gmail_recent", "description": "Get recent emails"},
                {"name": "drive_list_files", "description": "List Drive files"}
            ]
            mock_list.return_value = mock_tools
            
            tools = await get_all_google_tools()
            
            assert tools == mock_tools
            mock_list.assert_called_once()


class TestGlobalMCPClient:
    """Test the global MCP client instance."""
    
    def test_global_client_exists(self):
        """Test that global client instance exists."""
        assert google_mcp_client is not None
        assert isinstance(google_mcp_client, SimplifiedGoogleMCPClient)
    
    @pytest.mark.asyncio
    async def test_global_client_functionality(self):
        """Test that global client works properly."""
        # Should be able to list tools
        tools = await google_mcp_client.list_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0
        
        # Should be able to call connect/disconnect
        await google_mcp_client.connect()
        await google_mcp_client.disconnect()


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and comprehensive error handling."""
    
    @pytest.mark.asyncio
    async def test_call_tool_with_empty_arguments(self):
        """Test calling tool with minimal arguments."""
        client = SimplifiedGoogleMCPClient()
        
        result = await client.call_tool("gmail_recent", {"user_id": "test-user"})
        
        # Should attempt to get credentials even with minimal args
        assert "success" in result
        if not result["success"]:
            # If it fails, it should be due to credentials, not argument validation
            assert "credentials" in result["error"].lower() or "tool execution failed" in result["error"]
    
    @pytest.mark.asyncio
    async def test_tool_routing_comprehensive(self):
        """Test tool routing for all supported prefixes."""
        client = SimplifiedGoogleMCPClient()
        
        test_cases = [
            ("gmail_test", "_handle_gmail_tool"),
            ("drive_test", "_handle_drive_tool"),
            ("calendar_test", "_handle_calendar_tool")
        ]
        
        for tool_name, expected_method in test_cases:
            with patch('app.services.mcp_client_simple.get_user_google_credentials', new_callable=AsyncMock) as mock_creds, \
                 patch.object(client, expected_method, new_callable=AsyncMock) as mock_handler:
                
                mock_creds.return_value = {"access_token": "test-token"}
                mock_handler.return_value = {"success": True, "result": "handled"}
                
                result = await client.call_tool(tool_name, {"user_id": "test-123"})
                
                mock_handler.assert_called_once()
                assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_account_parameter_variations(self):
        """Test various account parameter values."""
        client = SimplifiedGoogleMCPClient()
        
        # Valid account should be preserved
        valid_account = "real.user@gmail.com"
        
        with patch('app.services.mcp_client_simple.get_user_google_credentials', new_callable=AsyncMock) as mock_creds, \
             patch.object(client, '_handle_gmail_tool', new_callable=AsyncMock) as mock_handler:
            
            mock_creds.return_value = {"access_token": "test-token"}
            mock_handler.return_value = {"success": True, "result": "handled"}
            
            await client.call_tool("gmail_recent", {
                "user_id": "test-123",
                "account": valid_account
            })
            
            # Should preserve the valid account
            mock_creds.assert_called_with("test-123", valid_account)
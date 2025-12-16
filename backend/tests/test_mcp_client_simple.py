"""
Tests for Simplified MCP Client.

This module tests the Google MCP client functionality, including tool listing,
execution, Gmail, Drive, and Calendar integrations.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any, List

from app.services.mcp_client import (
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
        await client.connect()
        await client.disconnect()
    
    @pytest.mark.asyncio
    async def test_list_tools_first_call(self):
        """Test listing tools for the first time."""
        client = SimplifiedGoogleMCPClient()
        tools = await client.list_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0
        assert client._tools_cache is not None
        assert len(client._tools_cache) == len(tools)
    
    @pytest.mark.asyncio
    async def test_list_tools_cached(self):
        """Test that subsequent calls use cache."""
        client = SimplifiedGoogleMCPClient()
        tools1 = await client.list_tools()
        cache_after_first = client._tools_cache
        tools2 = await client.list_tools()
        assert tools1 is tools2
        assert client._tools_cache is cache_after_first


class TestToolExecution:
    """Test tool execution functionality."""
    
    @pytest.mark.asyncio
    async def test_call_tool_missing_user_id(self):
        """Test tool call without user_id."""
        client = SimplifiedGoogleMCPClient()
        result = await client.call_tool("gmail_recent", {})
        assert result["success"] is False
        assert "user_id is required" in result["error"]
    
    @pytest.mark.asyncio
    async def test_call_tool_unknown_tool(self):
        """Test calling an unknown tool."""
        client = SimplifiedGoogleMCPClient()
        # Credential check happens first, so we must mock it to succeed to reach tool check
        with patch('app.services.mcp_client.get_user_google_credentials', new_callable=AsyncMock) as mock_creds:
            mock_creds.return_value = {"token": "valid"}
            result = await client.call_tool("unknown_tool", {"user_id": "test-123"})
            assert result["success"] is False
            assert "Unknown tool" in result["error"]
    
    @pytest.mark.asyncio
    async def test_call_tool_credentials_failure(self):
        """Test tool call when credentials fail."""
        client = SimplifiedGoogleMCPClient()
        with patch('app.services.mcp_client.get_user_google_credentials', new_callable=AsyncMock) as mock_creds:
            mock_creds.side_effect = Exception("Credentials not found")
            result = await client.call_tool("gmail_recent", {"user_id": "test-123"})
            assert result["success"] is False
            assert "Failed to get Google credentials" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_google_tool_gmail(self):
        """Test executing Google tool with Gmail action."""
        client = SimplifiedGoogleMCPClient()
        # Mock call_tool since execute_google_tool calls it
        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"success": True, "result": "executed"}
            
            # Use valid action "recent" which maps to "gmail_recent"
            result = await client.execute_google_tool("recent", "user-123", max_results=5)
            
            assert result["success"] is True
            mock_call.assert_called_once_with("gmail_recent", {
                "user_id": "user-123",
                "max_results": 5
            })
    @pytest.mark.asyncio
    async def test_call_tool_exception_handling(self):
        """Test tool call with unexpected exception."""
        client = SimplifiedGoogleMCPClient()
        # Mock credentials to succeed, then mock handler to fail to trigger generic exception
        with patch('app.services.mcp_client.get_user_google_credentials', new_callable=AsyncMock) as mock_creds, \
             patch('app.services.mcp_client.handle_gmail_tool', new_callable=AsyncMock) as mock_handler:
            
            mock_creds.return_value = {"token": "valid"}
            mock_handler.side_effect = RuntimeError("Unexpected execution error")
            
            result = await client.call_tool("gmail_recent", {"user_id": "test-123"})
            assert result["success"] is False
            # Now it should be caught by the outer try/except
            assert "Tool execution failed" in result["error"]
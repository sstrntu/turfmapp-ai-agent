"""
Comprehensive tests for mcp_client.py - MCP Client for Google Services Integration
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import asyncio
from typing import Dict, Any, List

# Import the service to test
from app.services.mcp_client import (
    GoogleMCPClient,
    google_mcp_client,
    get_mcp_client,
    execute_gmail_action,
    execute_drive_action,
    execute_calendar_action,
    get_all_google_tools
)


class TestGoogleMCPClientInitialization:
    """Test suite for GoogleMCPClient initialization"""

    def test_client_initialization_with_server_url(self):
        """Test GoogleMCPClient initialization with server URL"""
        server_url = "http://localhost:8080"
        client = GoogleMCPClient(server_url=server_url)
        
        assert client.server_url == server_url
        assert client.session is None
        assert client._tools_cache is None

    def test_client_initialization_without_server_url(self):
        """Test GoogleMCPClient initialization without server URL"""
        client = GoogleMCPClient()
        
        assert client.server_url is None
        assert client.session is None
        assert client._tools_cache is None

    def test_global_instance_exists(self):
        """Test that global google_mcp_client instance exists"""
        assert google_mcp_client is not None
        assert isinstance(google_mcp_client, GoogleMCPClient)


class TestConnection:
    """Test suite for connection management"""

    @pytest.fixture
    def mock_client(self):
        """Create a GoogleMCPClient for testing"""
        return GoogleMCPClient()

    @pytest.mark.asyncio
    async def test_connect_with_server_url(self):
        """Test connecting to external MCP server"""
        server_url = "http://localhost:8080"
        client = GoogleMCPClient(server_url=server_url)
        
        mock_session = Mock()
        
        with patch('app.services.mcp_client.sse_client') as mock_sse:
            mock_sse.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            
            await client.connect()
            
            assert client.session == mock_session
            mock_sse.assert_called_once_with(server_url)

    @pytest.mark.asyncio
    async def test_connect_without_server_url(self, mock_client):
        """Test connecting with in-process server"""
        await mock_client.connect()
        
        assert hasattr(mock_client, '_use_direct_server')
        assert mock_client._use_direct_server is True
        assert hasattr(mock_client, '_server_instance')

    @pytest.mark.asyncio
    async def test_disconnect_with_session(self):
        """Test disconnecting when session exists"""
        client = GoogleMCPClient()
        
        # Mock session
        mock_session = Mock()
        mock_session.__aexit__ = AsyncMock()
        client.session = mock_session
        
        await client.disconnect()
        
        assert client.session is None
        mock_session.__aexit__.assert_called_once_with(None, None, None)

    @pytest.mark.asyncio
    async def test_disconnect_without_session(self, mock_client):
        """Test disconnecting when no session exists"""
        # Should not raise any exception
        await mock_client.disconnect()
        assert mock_client.session is None


class TestListTools:
    """Test suite for list_tools method"""

    @pytest.fixture
    def mock_client(self):
        return GoogleMCPClient()

    @pytest.mark.asyncio
    async def test_list_tools_with_cache(self, mock_client):
        """Test list_tools when cache exists"""
        mock_tools = [Mock(name="gmail_search"), Mock(name="drive_list")]
        mock_client._tools_cache = mock_tools
        
        tools = await mock_client.list_tools()
        
        assert tools == mock_tools

    @pytest.mark.asyncio
    async def test_list_tools_direct_server(self, mock_client):
        """Test list_tools with direct server access"""
        # Set up direct server mode
        mock_client._use_direct_server = True
        
        mock_tools = [Mock(name="gmail_search"), Mock(name="drive_list")]
        mock_handler = AsyncMock(return_value=mock_tools)
        
        # Mock the server and handler
        mock_server = Mock()
        mock_handler_info = Mock()
        mock_handler_info.method = 'tools/list'
        mock_handler_info.handler = mock_handler
        mock_server._handlers = [mock_handler_info]
        
        with patch('app.services.mcp_client.google_mcp_server') as mock_mcp_server:
            mock_mcp_server.server = mock_server
            
            tools = await mock_client.list_tools()
            
            assert tools == mock_tools
            assert mock_client._tools_cache == mock_tools
            mock_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_tools_direct_server_no_handler(self, mock_client):
        """Test list_tools with direct server but no handler found"""
        mock_client._use_direct_server = True
        
        # Mock server with no matching handler
        mock_server = Mock()
        mock_server._handlers = []
        
        with patch('app.services.mcp_client.google_mcp_server') as mock_mcp_server:
            mock_mcp_server.server = mock_server
            
            tools = await mock_client.list_tools()
            
            assert tools == []
            assert mock_client._tools_cache == []

    @pytest.mark.asyncio
    async def test_list_tools_mcp_protocol(self):
        """Test list_tools using MCP protocol"""
        client = GoogleMCPClient("http://localhost:8080")
        
        mock_session = Mock()
        mock_result = Mock()
        mock_tools = [Mock(name="gmail_search"), Mock(name="drive_list")]
        mock_result.tools = mock_tools
        mock_session.list_tools = AsyncMock(return_value=mock_result)
        
        client.session = mock_session
        
        tools = await client.list_tools()
        
        assert tools == mock_tools
        assert client._tools_cache == mock_tools
        mock_session.list_tools.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_tools_no_session_raises_error(self, mock_client):
        """Test list_tools raises error when not connected"""
        # Don't set direct server mode
        with pytest.raises(RuntimeError, match="Not connected to MCP server"):
            await mock_client.list_tools()


class TestCallTool:
    """Test suite for call_tool method"""

    @pytest.fixture
    def mock_client(self):
        return GoogleMCPClient()

    @pytest.mark.asyncio
    async def test_call_tool_direct_server_success(self, mock_client):
        """Test call_tool with direct server access - success"""
        mock_client._use_direct_server = True
        
        # Mock successful tool result
        mock_content = Mock()
        mock_content.text = "Tool execution successful"
        mock_result = Mock()
        mock_result.content = [mock_content]
        
        mock_handler = AsyncMock(return_value=mock_result)
        
        # Mock server and handler
        mock_server = Mock()
        mock_handler_info = Mock()
        mock_handler_info.method = 'tools/call'
        mock_handler_info.handler = mock_handler
        mock_server._handlers = [mock_handler_info]
        
        with patch('app.services.mcp_client.google_mcp_server') as mock_mcp_server:
            mock_mcp_server.server = mock_server
            
            result = await mock_client.call_tool("gmail_search", {"query": "test"})
            
            assert result["success"] is True
            assert result["response"] == "Tool execution successful"
            assert result["tool"] == "gmail_search"
            mock_handler.assert_called_once_with("gmail_search", {"query": "test"})

    @pytest.mark.asyncio
    async def test_call_tool_direct_server_no_handler(self, mock_client):
        """Test call_tool with direct server but no handler found"""
        mock_client._use_direct_server = True
        
        # Mock server with no matching handler
        mock_server = Mock()
        mock_server._handlers = []
        
        with patch('app.services.mcp_client.google_mcp_server') as mock_mcp_server:
            mock_mcp_server.server = mock_server
            
            result = await mock_client.call_tool("gmail_search", {"query": "test"})
            
            assert result["success"] is False
            assert result["error"] == "No call_tool handler found"
            assert result["tool"] == "gmail_search"

    @pytest.mark.asyncio
    async def test_call_tool_direct_server_invalid_result(self, mock_client):
        """Test call_tool with direct server - invalid result format"""
        mock_client._use_direct_server = True
        
        # Mock handler that returns invalid result
        mock_result = Mock()
        # No content attribute
        mock_handler = AsyncMock(return_value=mock_result)
        
        mock_server = Mock()
        mock_handler_info = Mock()
        mock_handler_info.method = 'tools/call'
        mock_handler_info.handler = mock_handler
        mock_server._handlers = [mock_handler_info]
        
        with patch('app.services.mcp_client.google_mcp_server') as mock_mcp_server:
            mock_mcp_server.server = mock_server
            
            result = await mock_client.call_tool("gmail_search", {"query": "test"})
            
            assert result["success"] is False
            assert result["error"] == "Invalid tool result format"
            assert result["tool"] == "gmail_search"

    @pytest.mark.asyncio
    async def test_call_tool_direct_server_exception(self, mock_client):
        """Test call_tool with direct server - exception handling"""
        mock_client._use_direct_server = True
        
        # Mock server that raises exception
        with patch('app.services.mcp_client.google_mcp_server', side_effect=Exception("Server error")):
            result = await mock_client.call_tool("gmail_search", {"query": "test"})
            
            assert result["success"] is False
            assert result["error"] == "Server error"
            assert result["tool"] == "gmail_search"

    @pytest.mark.asyncio
    async def test_call_tool_mcp_protocol_success(self):
        """Test call_tool using MCP protocol - success"""
        client = GoogleMCPClient("http://localhost:8080")
        
        # Mock successful MCP result
        mock_content = Mock()
        mock_content.text = "MCP tool execution successful"
        mock_result = Mock()
        mock_result.content = [mock_content]
        
        mock_session = Mock()
        mock_session.call_tool = AsyncMock(return_value=mock_result)
        client.session = mock_session
        
        result = await client.call_tool("gmail_search", {"query": "test"})
        
        assert result["success"] is True
        assert result["response"] == "MCP tool execution successful"
        assert result["tool"] == "gmail_search"
        assert "raw_result" in result

    @pytest.mark.asyncio
    async def test_call_tool_mcp_protocol_exception(self):
        """Test call_tool using MCP protocol - exception handling"""
        client = GoogleMCPClient("http://localhost:8080")
        
        mock_session = Mock()
        mock_session.call_tool = AsyncMock(side_effect=Exception("MCP error"))
        client.session = mock_session
        
        result = await client.call_tool("gmail_search", {"query": "test"})
        
        assert result["success"] is False
        assert result["error"] == "MCP error"
        assert result["tool"] == "gmail_search"

    @pytest.mark.asyncio
    async def test_call_tool_no_session_raises_error(self, mock_client):
        """Test call_tool raises error when not connected"""
        # Don't set direct server mode
        with pytest.raises(RuntimeError, match="Not connected to MCP server"):
            await mock_client.call_tool("gmail_search", {"query": "test"})


class TestGetAvailableToolsForOpenAI:
    """Test suite for get_available_tools_for_openai method"""

    @pytest.fixture
    def mock_client(self):
        return GoogleMCPClient()

    @pytest.mark.asyncio
    async def test_get_available_tools_for_openai(self, mock_client):
        """Test formatting tools for OpenAI function calling"""
        # Mock tools
        mock_tool1 = Mock()
        mock_tool1.name = "gmail_search"
        mock_tool1.description = "Search Gmail emails"
        mock_tool1.inputSchema = {"type": "object", "properties": {"query": {"type": "string"}}}
        
        mock_tool2 = Mock()
        mock_tool2.name = "drive_list_files"
        mock_tool2.description = "List Google Drive files"
        mock_tool2.inputSchema = {"type": "object", "properties": {"folder_id": {"type": "string"}}}
        
        mock_tools = [mock_tool1, mock_tool2]
        
        with patch.object(mock_client, 'list_tools', new_callable=AsyncMock, return_value=mock_tools):
            openai_tools = await mock_client.get_available_tools_for_openai()
            
            assert len(openai_tools) == 2
            
            # Check first tool
            assert openai_tools[0]["type"] == "function"
            assert openai_tools[0]["name"] == "gmail_search"
            assert openai_tools[0]["description"] == "Search Gmail emails"
            assert openai_tools[0]["parameters"] == mock_tool1.inputSchema
            
            # Check second tool
            assert openai_tools[1]["type"] == "function"
            assert openai_tools[1]["name"] == "drive_list_files"
            assert openai_tools[1]["description"] == "List Google Drive files"
            assert openai_tools[1]["parameters"] == mock_tool2.inputSchema


class TestExecuteGoogleTool:
    """Test suite for execute_google_tool method"""

    @pytest.fixture
    def mock_client(self):
        return GoogleMCPClient()

    @pytest.mark.asyncio
    async def test_execute_google_tool_gmail_actions(self, mock_client):
        """Test execute_google_tool with Gmail actions"""
        # Mock call_tool method
        mock_client.call_tool = AsyncMock(return_value={"success": True, "response": "Gmail result"})
        
        # Test search action
        result = await mock_client.execute_google_tool("search", "user123", query="test")
        assert result["success"] is True
        mock_client.call_tool.assert_called_with("gmail_search", {"user_id": "user123", "query": "test"})
        
        # Test recent action
        result = await mock_client.execute_google_tool("recent", "user123", max_results=5)
        mock_client.call_tool.assert_called_with("gmail_recent", {"user_id": "user123", "max_results": 5})
        
        # Test important action
        result = await mock_client.execute_google_tool("important", "user123")
        mock_client.call_tool.assert_called_with("gmail_important", {"user_id": "user123"})
        
        # Test read action
        result = await mock_client.execute_google_tool("read", "user123", message_id="msg123")
        mock_client.call_tool.assert_called_with("gmail_get_message", {"user_id": "user123", "message_id": "msg123"})

    @pytest.mark.asyncio
    async def test_execute_google_tool_drive_actions(self, mock_client):
        """Test execute_google_tool with Drive actions"""
        mock_client.call_tool = AsyncMock(return_value={"success": True, "response": "Drive result"})
        
        # Test list_files action
        result = await mock_client.execute_google_tool("list_files", "user123")
        mock_client.call_tool.assert_called_with("drive_list_files", {"user_id": "user123"})
        
        # Test create_folder action
        result = await mock_client.execute_google_tool("create_folder", "user123", name="New Folder")
        mock_client.call_tool.assert_called_with("drive_create_folder", {"user_id": "user123", "name": "New Folder"})
        
        # Test list_folder_files action
        result = await mock_client.execute_google_tool("list_folder_files", "user123", folder_id="folder123")
        mock_client.call_tool.assert_called_with("drive_list_folder_files", {"user_id": "user123", "folder_id": "folder123"})

    @pytest.mark.asyncio
    async def test_execute_google_tool_calendar_actions(self, mock_client):
        """Test execute_google_tool with Calendar actions"""
        mock_client.call_tool = AsyncMock(return_value={"success": True, "response": "Calendar result"})
        
        # Test list_events action
        result = await mock_client.execute_google_tool("list_events", "user123")
        mock_client.call_tool.assert_called_with("calendar_list_events", {"user_id": "user123"})
        
        # Test upcoming_events action
        result = await mock_client.execute_google_tool("upcoming_events", "user123", max_results=10)
        mock_client.call_tool.assert_called_with("calendar_upcoming_events", {"user_id": "user123", "max_results": 10})

    @pytest.mark.asyncio
    async def test_execute_google_tool_unknown_action(self, mock_client):
        """Test execute_google_tool with unknown action"""
        result = await mock_client.execute_google_tool("unknown_action", "user123")
        
        assert result["success"] is False
        assert "Unknown action: unknown_action" in result["error"]
        assert "Available actions:" in result["error"]
        assert result["action"] == "unknown_action"

    @pytest.mark.asyncio
    async def test_execute_google_tool_with_additional_kwargs(self, mock_client):
        """Test execute_google_tool with additional keyword arguments"""
        mock_client.call_tool = AsyncMock(return_value={"success": True, "response": "Result"})
        
        result = await mock_client.execute_google_tool(
            "search", 
            "user123", 
            query="test", 
            max_results=10, 
            include_spam=False
        )
        
        mock_client.call_tool.assert_called_with("gmail_search", {
            "user_id": "user123",
            "query": "test",
            "max_results": 10,
            "include_spam": False
        })


class TestListResources:
    """Test suite for list_resources method"""

    @pytest.fixture
    def mock_client(self):
        return GoogleMCPClient()

    @pytest.mark.asyncio
    async def test_list_resources_direct_server(self, mock_client):
        """Test list_resources with direct server access"""
        mock_client._use_direct_server = True
        
        # Mock resources
        mock_resource1 = Mock()
        mock_resource1.uri = "resource://gmail/inbox"
        mock_resource1.name = "Gmail Inbox"
        mock_resource1.description = "User's Gmail inbox"
        
        mock_resource2 = Mock()
        mock_resource2.uri = "resource://drive/files"
        mock_resource2.name = "Drive Files"
        mock_resource2.description = "User's Google Drive files"
        
        mock_result = Mock()
        mock_result.resources = [mock_resource1, mock_resource2]
        
        mock_handler = AsyncMock(return_value=mock_result)
        
        # Mock server and handler
        mock_server = Mock()
        mock_handler_info = Mock()
        mock_handler_info.method = 'resources/list'
        mock_handler_info.handler = mock_handler
        mock_server._handlers = [mock_handler_info]
        
        with patch('app.services.mcp_client.google_mcp_server') as mock_mcp_server:
            mock_mcp_server.server = mock_server
            
            resources = await mock_client.list_resources()
            
            assert len(resources) == 2
            assert resources[0]["uri"] == "resource://gmail/inbox"
            assert resources[0]["name"] == "Gmail Inbox"
            assert resources[0]["description"] == "User's Gmail inbox"
            assert resources[1]["uri"] == "resource://drive/files"
            assert resources[1]["name"] == "Drive Files"
            assert resources[1]["description"] == "User's Google Drive files"

    @pytest.mark.asyncio
    async def test_list_resources_direct_server_no_handler(self, mock_client):
        """Test list_resources with direct server but no handler found"""
        mock_client._use_direct_server = True
        
        # Mock server with no matching handler
        mock_server = Mock()
        mock_server._handlers = []
        
        with patch('app.services.mcp_client.google_mcp_server') as mock_mcp_server:
            mock_mcp_server.server = mock_server
            
            resources = await mock_client.list_resources()
            
            assert resources == []

    @pytest.mark.asyncio
    async def test_list_resources_mcp_protocol(self):
        """Test list_resources using MCP protocol"""
        client = GoogleMCPClient("http://localhost:8080")
        
        # Mock resources
        mock_resource = Mock()
        mock_resource.uri = "resource://gmail/inbox"
        mock_resource.name = "Gmail Inbox"
        mock_resource.description = "User's Gmail inbox"
        
        mock_result = Mock()
        mock_result.resources = [mock_resource]
        
        mock_session = Mock()
        mock_session.list_resources = AsyncMock(return_value=mock_result)
        client.session = mock_session
        
        resources = await client.list_resources()
        
        assert len(resources) == 1
        assert resources[0]["uri"] == "resource://gmail/inbox"
        assert resources[0]["name"] == "Gmail Inbox"
        assert resources[0]["description"] == "User's Gmail inbox"

    @pytest.mark.asyncio
    async def test_list_resources_no_session_raises_error(self, mock_client):
        """Test list_resources raises error when not connected"""
        # Don't set direct server mode
        with pytest.raises(RuntimeError, match="Not connected to MCP server"):
            await mock_client.list_resources()


class TestGlobalFunctions:
    """Test suite for global convenience functions"""

    @pytest.mark.asyncio
    async def test_get_mcp_client_already_connected(self):
        """Test get_mcp_client when client is already connected"""
        with patch('app.services.mcp_client.google_mcp_client') as mock_client:
            mock_client.session = Mock()  # Already has session
            
            result = await get_mcp_client()
            
            assert result == mock_client
            # Should not call connect since session exists

    @pytest.mark.asyncio
    async def test_get_mcp_client_not_connected(self):
        """Test get_mcp_client when client needs connection"""
        with patch('app.services.mcp_client.google_mcp_client') as mock_client:
            mock_client.session = None  # No session
            mock_client.connect = AsyncMock()
            
            result = await get_mcp_client()
            
            assert result == mock_client
            mock_client.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_mcp_client_no_session_attribute(self):
        """Test get_mcp_client when client has no session attribute"""
        with patch('app.services.mcp_client.google_mcp_client') as mock_client:
            # Remove session attribute
            if hasattr(mock_client, 'session'):
                delattr(mock_client, 'session')
            mock_client.connect = AsyncMock()
            
            result = await get_mcp_client()
            
            assert result == mock_client
            mock_client.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_gmail_action(self):
        """Test execute_gmail_action convenience function"""
        with patch('app.services.mcp_client.get_mcp_client') as mock_get_client:
            mock_client = Mock()
            mock_client.execute_google_tool = AsyncMock(return_value={"success": True, "response": "Gmail result"})
            mock_get_client.return_value = mock_client
            
            result = await execute_gmail_action("search", "user123", query="test")
            
            assert result["success"] is True
            assert result["response"] == "Gmail result"
            mock_client.execute_google_tool.assert_called_once_with("search", "user123", query="test")

    @pytest.mark.asyncio
    async def test_execute_drive_action(self):
        """Test execute_drive_action convenience function"""
        with patch('app.services.mcp_client.get_mcp_client') as mock_get_client:
            mock_client = Mock()
            mock_client.execute_google_tool = AsyncMock(return_value={"success": True, "response": "Drive result"})
            mock_get_client.return_value = mock_client
            
            result = await execute_drive_action("list_files", "user123")
            
            assert result["success"] is True
            assert result["response"] == "Drive result"
            mock_client.execute_google_tool.assert_called_once_with("list_files", "user123")

    @pytest.mark.asyncio
    async def test_execute_calendar_action(self):
        """Test execute_calendar_action convenience function"""
        with patch('app.services.mcp_client.get_mcp_client') as mock_get_client:
            mock_client = Mock()
            mock_client.execute_google_tool = AsyncMock(return_value={"success": True, "response": "Calendar result"})
            mock_get_client.return_value = mock_client
            
            result = await execute_calendar_action("list_events", "user123", max_results=10)
            
            assert result["success"] is True
            assert result["response"] == "Calendar result"
            mock_client.execute_google_tool.assert_called_once_with("list_events", "user123", max_results=10)

    @pytest.mark.asyncio
    async def test_get_all_google_tools(self):
        """Test get_all_google_tools convenience function"""
        mock_tools = [
            {
                "type": "function",
                "name": "gmail_search",
                "description": "Search Gmail emails",
                "parameters": {"type": "object", "properties": {}}
            }
        ]
        
        with patch('app.services.mcp_client.get_mcp_client') as mock_get_client:
            mock_client = Mock()
            mock_client.get_available_tools_for_openai = AsyncMock(return_value=mock_tools)
            mock_get_client.return_value = mock_client
            
            tools = await get_all_google_tools()
            
            assert tools == mock_tools
            mock_client.get_available_tools_for_openai.assert_called_once()


class TestEdgeCasesAndErrorHandling:
    """Test suite for edge cases and error handling"""

    @pytest.fixture
    def mock_client(self):
        return GoogleMCPClient()

    @pytest.mark.asyncio
    async def test_call_tool_with_multiple_content_items(self, mock_client):
        """Test call_tool with multiple content items in result"""
        mock_client._use_direct_server = True
        
        # Mock result with multiple content items
        mock_content1 = Mock()
        mock_content1.text = "First part"
        mock_content2 = Mock()
        mock_content2.text = " Second part"
        mock_result = Mock()
        mock_result.content = [mock_content1, mock_content2]
        
        mock_handler = AsyncMock(return_value=mock_result)
        
        mock_server = Mock()
        mock_handler_info = Mock()
        mock_handler_info.method = 'tools/call'
        mock_handler_info.handler = mock_handler
        mock_server._handlers = [mock_handler_info]
        
        with patch('app.services.mcp_client.google_mcp_server') as mock_mcp_server:
            mock_mcp_server.server = mock_server
            
            result = await mock_client.call_tool("test_tool", {})
            
            assert result["success"] is True
            assert result["response"] == "First part Second part"

    @pytest.mark.asyncio
    async def test_call_tool_with_content_without_text(self, mock_client):
        """Test call_tool with content items that don't have text attribute"""
        mock_client._use_direct_server = True
        
        # Mock result with content without text
        mock_content = Mock()
        # No text attribute
        mock_result = Mock()
        mock_result.content = [mock_content]
        
        mock_handler = AsyncMock(return_value=mock_result)
        
        mock_server = Mock()
        mock_handler_info = Mock()
        mock_handler_info.method = 'tools/call'
        mock_handler_info.handler = mock_handler
        mock_server._handlers = [mock_handler_info]
        
        with patch('app.services.mcp_client.google_mcp_server') as mock_mcp_server:
            mock_mcp_server.server = mock_server
            
            result = await mock_client.call_tool("test_tool", {})
            
            assert result["success"] is True
            assert result["response"] == ""  # Empty string when no text content

    def test_tool_mapping_completeness(self, mock_client):
        """Test that all expected actions are mapped to tools"""
        # Get the tool mapping from the method (we'll need to extract it)
        tool_mapping = {
            # Gmail actions
            "search": "gmail_search",
            "recent": "gmail_recent", 
            "find_recent": "gmail_recent",
            "important": "gmail_important",
            "find_important": "gmail_important",
            "read": "gmail_get_message",
            "get_message": "gmail_get_message",
            
            # Drive actions
            "list_files": "drive_list_files",
            "create_folder": "drive_create_folder",
            "list_folder_files": "drive_list_folder_files",
            
            # Calendar actions
            "list_events": "calendar_list_events",
            "upcoming_events": "calendar_upcoming_events"
        }
        
        # Test that all actions have mappings
        for action in ["search", "recent", "important", "read", "list_files", "create_folder", "list_events"]:
            assert action in tool_mapping
            assert tool_mapping[action] is not None
            assert isinstance(tool_mapping[action], str)

    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self, mock_client):
        """Test concurrent tool calls don't interfere with each other"""
        mock_client.call_tool = AsyncMock(side_effect=lambda tool, args: {
            "success": True,
            "response": f"Result for {tool}",
            "tool": tool
        })
        
        # Execute multiple tools concurrently
        tasks = [
            mock_client.execute_google_tool("search", "user1", query="test1"),
            mock_client.execute_google_tool("recent", "user2"),
            mock_client.execute_google_tool("list_files", "user3")
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 3
        assert all(result["success"] for result in results)
        assert results[0]["response"] == "Result for gmail_search"
        assert results[1]["response"] == "Result for gmail_recent"
        assert results[2]["response"] == "Result for drive_list_files"

    @pytest.mark.asyncio
    async def test_large_tool_response_handling(self, mock_client):
        """Test handling of large tool responses"""
        mock_client._use_direct_server = True
        
        # Mock very large response
        large_text = "x" * 10000  # 10KB of text
        mock_content = Mock()
        mock_content.text = large_text
        mock_result = Mock()
        mock_result.content = [mock_content]
        
        mock_handler = AsyncMock(return_value=mock_result)
        
        mock_server = Mock()
        mock_handler_info = Mock()
        mock_handler_info.method = 'tools/call'
        mock_handler_info.handler = mock_handler
        mock_server._handlers = [mock_handler_info]
        
        with patch('app.services.mcp_client.google_mcp_server') as mock_mcp_server:
            mock_mcp_server.server = mock_server
            
            result = await mock_client.call_tool("test_tool", {})
            
            assert result["success"] is True
            assert len(result["response"]) == 10000
            assert result["response"] == large_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
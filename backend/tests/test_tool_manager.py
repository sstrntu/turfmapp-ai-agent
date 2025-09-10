"""
Tests for Tool Manager service.

This module tests the tool management functionality, including tool registration,
execution, MCP integration, and error handling.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any, List

from app.services.tool_manager import ToolManager, tool_manager


class MockTool:
    """Mock tool for testing purposes."""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    def get_tool_definition(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {"type": "object", "properties": {}}
            }
        }
    
    async def execute(self, user_id: str, **kwargs):
        return {"success": True, "result": f"{self.name} executed for {user_id}"}


class TestToolManager:
    """Test basic tool manager functionality."""
    
    def test_tool_manager_initialization(self):
        """Test tool manager initializes with empty tools."""
        tm = ToolManager()
        
        assert isinstance(tm.tools, dict)
        assert len(tm.tools) == 0
    
    def test_add_tool(self):
        """Test adding a tool to the manager."""
        tm = ToolManager()
        mock_tool = MockTool("test_tool", "A test tool")
        
        tm.add_tool("test_tool", mock_tool)
        
        assert "test_tool" in tm.tools
        assert tm.tools["test_tool"] == mock_tool
    
    def test_remove_tool(self):
        """Test removing a tool from the manager."""
        tm = ToolManager()
        mock_tool = MockTool("test_tool", "A test tool")
        
        tm.add_tool("test_tool", mock_tool)
        assert "test_tool" in tm.tools
        
        tm.remove_tool("test_tool")
        assert "test_tool" not in tm.tools
    
    def test_remove_nonexistent_tool(self):
        """Test removing a tool that doesn't exist."""
        tm = ToolManager()
        
        # Should not raise an exception
        tm.remove_tool("nonexistent_tool")
        assert len(tm.tools) == 0
    
    def test_get_tool_by_name(self):
        """Test retrieving a tool by name."""
        tm = ToolManager()
        mock_tool = MockTool("test_tool", "A test tool")
        
        tm.add_tool("test_tool", mock_tool)
        
        retrieved_tool = tm.get_tool_by_name("test_tool")
        assert retrieved_tool == mock_tool
        
        nonexistent_tool = tm.get_tool_by_name("nonexistent")
        assert nonexistent_tool is None
    
    def test_get_available_tools_empty(self):
        """Test getting available tools when none exist."""
        tm = ToolManager()
        
        tools = tm.get_available_tools()
        
        assert isinstance(tools, list)
        assert len(tools) == 0
    
    def test_get_available_tools_with_tools(self):
        """Test getting available tools when tools exist."""
        tm = ToolManager()
        mock_tool1 = MockTool("tool1", "First tool")
        mock_tool2 = MockTool("tool2", "Second tool")
        
        tm.add_tool("tool1", mock_tool1)
        tm.add_tool("tool2", mock_tool2)
        
        tools = tm.get_available_tools()
        
        assert len(tools) == 2
        assert all("type" in tool for tool in tools)
        assert all("function" in tool for tool in tools)
    
    def test_get_tool_descriptions_empty(self):
        """Test getting tool descriptions when no tools exist."""
        tm = ToolManager()
        
        descriptions = tm.get_tool_descriptions()
        
        assert isinstance(descriptions, dict)
        assert len(descriptions) == 0
    
    def test_get_tool_descriptions_with_tools(self):
        """Test getting tool descriptions when tools exist."""
        tm = ToolManager()
        mock_tool1 = MockTool("tool1", "First tool")
        mock_tool2 = MockTool("tool2", "Second tool")
        
        tm.add_tool("tool1", mock_tool1)
        tm.add_tool("tool2", mock_tool2)
        
        descriptions = tm.get_tool_descriptions()
        
        assert len(descriptions) == 2
        assert descriptions["tool1"] == "First tool"
        assert descriptions["tool2"] == "Second tool"


class TestToolExecution:
    """Test tool execution functionality."""
    
    @pytest.mark.asyncio
    async def test_execute_tool_success(self):
        """Test successful tool execution."""
        tm = ToolManager()
        mock_tool = MockTool("test_tool", "A test tool")
        
        tm.add_tool("test_tool", mock_tool)
        
        result = await tm.execute_tool("test_tool", "user-123", param1="value1")
        
        assert result["success"] is True
        assert "test_tool executed for user-123" in result["result"]
    
    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self):
        """Test executing a tool that doesn't exist."""
        tm = ToolManager()
        
        result = await tm.execute_tool("nonexistent_tool", "user-123")
        
        assert result["success"] is False
        assert "not found" in result["error"]
        assert "available_tools" in result
        assert isinstance(result["available_tools"], list)
    
    @pytest.mark.asyncio
    async def test_execute_tool_exception(self):
        """Test tool execution when tool raises an exception."""
        tm = ToolManager()
        mock_tool = Mock()
        mock_tool.execute = AsyncMock(side_effect=Exception("Tool execution failed"))
        
        tm.add_tool("failing_tool", mock_tool)
        
        result = await tm.execute_tool("failing_tool", "user-123")
        
        assert result["success"] is False
        assert "Tool execution error" in result["error"]
        assert result["tool"] == "failing_tool"


class TestMCPIntegration:
    """Test MCP (Model Context Protocol) integration."""
    
    def test_is_mcp_tool_gmail(self):
        """Test MCP tool detection for Gmail tools."""
        tm = ToolManager()
        
        assert tm.is_mcp_tool("gmail_recent") is True
        assert tm.is_mcp_tool("gmail_search") is True
        assert tm.is_mcp_tool("gmail_send") is True
        assert tm.is_mcp_tool("regular_tool") is False
    
    def test_is_mcp_tool_drive(self):
        """Test MCP tool detection for Drive tools."""
        tm = ToolManager()
        
        assert tm.is_mcp_tool("drive_list_files") is True
        assert tm.is_mcp_tool("drive_upload") is True
        assert tm.is_mcp_tool("regular_tool") is False
    
    def test_is_mcp_tool_calendar(self):
        """Test MCP tool detection for Calendar tools."""
        tm = ToolManager()
        
        assert tm.is_mcp_tool("calendar_upcoming") is True
        assert tm.is_mcp_tool("calendar_events") is True
        assert tm.is_mcp_tool("regular_tool") is False
    
    @pytest.mark.asyncio
    async def test_get_all_tools_with_mcp_success(self):
        """Test getting all tools including MCP tools successfully."""
        tm = ToolManager()
        mock_tool = MockTool("traditional_tool", "A traditional tool")
        tm.add_tool("traditional_tool", mock_tool)
        
        mock_mcp_tools = [
            {
                "name": "gmail_recent",
                "description": "Get recent Gmail messages",
                "inputSchema": {"type": "object", "properties": {"max_results": {"type": "integer"}}}
            },
            {
                "name": "calendar_upcoming",
                "description": "Get upcoming calendar events",
                "inputSchema": {"type": "object", "properties": {"max_events": {"type": "integer"}}}
            }
        ]
        
        with patch('app.services.mcp_client.get_all_google_tools', new_callable=AsyncMock) as mock_get_mcp:
            mock_get_mcp.return_value = mock_mcp_tools
            
            all_tools = await tm.get_all_tools_with_mcp()
            
            assert len(all_tools) == 3  # 1 traditional + 2 MCP
            
            # Check traditional tool
            traditional_tools = [t for t in all_tools if t["function"]["name"] == "traditional_tool"]
            assert len(traditional_tools) == 1
            
            # Check MCP tools
            mcp_tools = [t for t in all_tools if t["function"]["name"].startswith(("gmail_", "calendar_"))]
            assert len(mcp_tools) == 2
    
    @pytest.mark.asyncio
    async def test_get_all_tools_with_mcp_failure(self):
        """Test getting all tools when MCP fails."""
        tm = ToolManager()
        mock_tool = MockTool("traditional_tool", "A traditional tool")
        tm.add_tool("traditional_tool", mock_tool)
        
        with patch('app.services.mcp_client.get_all_google_tools', new_callable=AsyncMock) as mock_get_mcp:
            mock_get_mcp.side_effect = Exception("MCP connection failed")
            
            all_tools = await tm.get_all_tools_with_mcp()
            
            # Should fallback to traditional tools only
            assert len(all_tools) == 1
            assert all_tools[0]["function"]["name"] == "traditional_tool"
    
    @pytest.mark.asyncio
    async def test_get_all_descriptions_with_mcp_success(self):
        """Test getting all tool descriptions including MCP."""
        tm = ToolManager()
        mock_tool = MockTool("traditional_tool", "A traditional tool")
        tm.add_tool("traditional_tool", mock_tool)
        
        mock_mcp_tools = [
            {"name": "gmail_recent", "description": "Get recent Gmail messages"},
            {"name": "calendar_upcoming", "description": "Get upcoming calendar events"}
        ]
        
        with patch('app.services.mcp_client.get_all_google_tools', new_callable=AsyncMock) as mock_get_mcp:
            mock_get_mcp.return_value = mock_mcp_tools
            
            descriptions = await tm.get_all_descriptions_with_mcp()
            
            assert len(descriptions) == 3
            assert descriptions["traditional_tool"] == "A traditional tool"
            assert descriptions["gmail_recent"] == "Get recent Gmail messages"
            assert descriptions["calendar_upcoming"] == "Get upcoming calendar events"
    
    @pytest.mark.asyncio
    async def test_get_all_descriptions_with_mcp_failure(self):
        """Test getting tool descriptions when MCP fails."""
        tm = ToolManager()
        mock_tool = MockTool("traditional_tool", "A traditional tool")
        tm.add_tool("traditional_tool", mock_tool)
        
        with patch('app.services.mcp_client.get_all_google_tools', new_callable=AsyncMock) as mock_get_mcp:
            mock_get_mcp.side_effect = Exception("MCP connection failed")
            
            descriptions = await tm.get_all_descriptions_with_mcp()
            
            # Should fallback to traditional descriptions only
            assert len(descriptions) == 1
            assert descriptions["traditional_tool"] == "A traditional tool"


class TestToolManagerEdgeCases:
    """Test edge cases and error scenarios."""
    
    def test_tool_manager_with_none_tool(self):
        """Test adding None as a tool."""
        tm = ToolManager()
        
        # Should not break, but tool won't be functional
        tm.add_tool("none_tool", None)
        assert "none_tool" in tm.tools
        assert tm.tools["none_tool"] is None
    
    @pytest.mark.asyncio
    async def test_execute_none_tool(self):
        """Test executing a None tool."""
        tm = ToolManager()
        tm.add_tool("none_tool", None)
        
        # Should handle gracefully
        result = await tm.execute_tool("none_tool", "user-123")
        assert result["success"] is False
        assert "error" in result
    
    def test_get_available_tools_with_broken_tool(self):
        """Test getting available tools when a tool's definition method fails."""
        tm = ToolManager()
        broken_tool = Mock()
        broken_tool.get_tool_definition.side_effect = Exception("Tool definition error")
        
        tm.add_tool("broken_tool", broken_tool)
        
        # Should handle the exception gracefully
        with pytest.raises(Exception):
            tm.get_available_tools()
    
    def test_multiple_tool_operations(self):
        """Test multiple tool operations in sequence."""
        tm = ToolManager()
        
        # Add multiple tools
        for i in range(5):
            tool = MockTool(f"tool_{i}", f"Tool number {i}")
            tm.add_tool(f"tool_{i}", tool)
        
        assert len(tm.tools) == 5
        
        # Remove some tools
        tm.remove_tool("tool_2")
        tm.remove_tool("tool_4")
        
        assert len(tm.tools) == 3
        assert "tool_0" in tm.tools
        assert "tool_1" in tm.tools
        assert "tool_2" not in tm.tools
        assert "tool_3" in tm.tools
        assert "tool_4" not in tm.tools


class TestGlobalToolManager:
    """Test the global tool manager instance."""
    
    def test_global_tool_manager_exists(self):
        """Test that global tool manager instance exists."""
        assert tool_manager is not None
        assert isinstance(tool_manager, ToolManager)
    
    def test_global_tool_manager_is_singleton(self):
        """Test that tool_manager behaves like a singleton."""
        from app.services.tool_manager import tool_manager as tm2
        
        # Should be the same instance
        assert tool_manager is tm2
    
    def test_global_tool_manager_operations(self):
        """Test operations on the global tool manager."""
        initial_count = len(tool_manager.tools)
        
        # Add a test tool
        test_tool = MockTool("global_test", "Global test tool")
        tool_manager.add_tool("global_test", test_tool)
        
        assert len(tool_manager.tools) == initial_count + 1
        assert tool_manager.get_tool_by_name("global_test") == test_tool
        
        # Clean up
        tool_manager.remove_tool("global_test")
        assert len(tool_manager.tools) == initial_count


class TestToolManagerIntegration:
    """Test integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test a complete workflow with tool registration and execution."""
        tm = ToolManager()
        
        # Step 1: Add tools
        database_tool = MockTool("database_query", "Execute database queries")
        file_tool = MockTool("file_processor", "Process files")
        
        tm.add_tool("database_query", database_tool)
        tm.add_tool("file_processor", file_tool)
        
        # Step 2: Get available tools
        available = tm.get_available_tools()
        assert len(available) == 2
        
        # Step 3: Get descriptions
        descriptions = tm.get_tool_descriptions()
        assert "database_query" in descriptions
        assert "file_processor" in descriptions
        
        # Step 4: Execute tools
        db_result = await tm.execute_tool("database_query", "user-123", query="SELECT * FROM users")
        assert db_result["success"] is True
        
        file_result = await tm.execute_tool("file_processor", "user-456", filename="data.csv")
        assert file_result["success"] is True
        
        # Step 5: Try to execute non-existent tool
        invalid_result = await tm.execute_tool("non_existent", "user-789")
        assert invalid_result["success"] is False
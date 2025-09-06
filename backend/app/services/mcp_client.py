"""
MCP Client for Google Services Integration

This module implements a Model Context Protocol (MCP) client that connects
to the Google Services MCP server to provide standardized tool integration
for the AI chat system.
"""

from __future__ import annotations

import asyncio
import json
from typing import Dict, Any, List, Optional

import httpx
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from mcp.types import (
    Tool,
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListResourcesRequest,
    ReadResourceRequest
)


class GoogleMCPClient:
    """MCP Client for Google Services integration."""
    
    def __init__(self, server_url: Optional[str] = None):
        """
        Initialize MCP client.
        
        Args:
            server_url: URL of the MCP server (if None, uses in-process server)
        """
        self.server_url = server_url
        self.session: Optional[ClientSession] = None
        self._tools_cache: Optional[List[Tool]] = None
        
    async def connect(self):
        """Connect to the MCP server."""
        if self.server_url:
            # Connect to external MCP server via HTTP/SSE
            self.session = await sse_client(self.server_url).__aenter__()
        else:
            # Use in-process server (for testing/development)
            # For now, we'll use direct method calls as fallback
            self._use_direct_server = True
            self._server_instance = None
        
    async def disconnect(self):
        """Disconnect from the MCP server."""
        if self.session:
            await self.session.__aexit__(None, None, None)
            self.session = None
    
    async def list_tools(self) -> List[Tool]:
        """Get list of available tools from the MCP server."""
        if self._tools_cache:
            return self._tools_cache
        
        if hasattr(self, '_use_direct_server'):
            # Direct server access for development
            from .mcp_server import google_mcp_server
            # Get the list_tools handler directly from the server
            handler = None
            for handler_info in google_mcp_server.server._handlers:
                if hasattr(handler_info, 'method') and handler_info.method == 'tools/list':
                    handler = handler_info.handler
                    break
            
            if handler:
                tools = await handler()
                self._tools_cache = tools
                return tools
            else:
                # Fallback: create tools list directly
                self._tools_cache = []
                return self._tools_cache
        
        if not self.session:
            raise RuntimeError("Not connected to MCP server. Call connect() first.")
        
        # Use MCP protocol
        result = await self.session.list_tools(ListToolsRequest())
        tools = result.tools
        self._tools_cache = tools
        return tools
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool through the MCP protocol.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        if hasattr(self, '_use_direct_server'):
            # Direct server access for development
            from .mcp_server import google_mcp_server
            try:
                # Get the call_tool handler directly from the server
                handler = None
                for handler_info in google_mcp_server.server._handlers:
                    if hasattr(handler_info, 'method') and handler_info.method == 'tools/call':
                        handler = handler_info.handler
                        break
                
                if handler:
                    result = await handler(tool_name, arguments)
                    
                    # Convert CallToolResult to our expected format
                    if hasattr(result, 'content'):
                        content_text = ""
                        for content in result.content:
                            if hasattr(content, 'text'):
                                content_text += content.text
                        
                        return {
                            "success": True,
                            "response": content_text,
                            "tool": tool_name
                        }
                    else:
                        return {
                            "success": False,
                            "error": "Invalid tool result format",
                            "tool": tool_name
                        }
                else:
                    return {
                        "success": False,
                        "error": "No call_tool handler found",
                        "tool": tool_name
                    }
                    
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "tool": tool_name
                }
        
        if not self.session:
            raise RuntimeError("Not connected to MCP server. Call connect() first.")
        
        # Use MCP protocol
        request = CallToolRequest(
            name=tool_name,
            arguments=arguments
        )
        
        try:
            result = await self.session.call_tool(request)
            
            # Process the result
            content_text = ""
            for content in result.content:
                if hasattr(content, 'text'):
                    content_text += content.text
            
            return {
                "success": True,
                "response": content_text,
                "tool": tool_name,
                "raw_result": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "tool": tool_name
            }
    
    async def get_available_tools_for_openai(self) -> List[Dict[str, Any]]:
        """
        Get tools formatted for OpenAI function calling.
        
        Returns:
            List of tool definitions in OpenAI format
        """
        tools = await self.list_tools()
        
        openai_tools = []
        for tool in tools:
            openai_tool = {
                "type": "function",
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }
            openai_tools.append(openai_tool)
        
        return openai_tools
    
    async def execute_google_tool(self, action: str, user_id: str, **kwargs) -> Dict[str, Any]:
        """
        Execute a Google service tool with simplified interface.
        
        Args:
            action: The action to perform (search, recent, important, etc.)
            user_id: User ID for authentication
            **kwargs: Additional arguments for the tool
            
        Returns:
            Tool execution result
        """
        # Map actions to MCP tool names
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
        
        tool_name = tool_mapping.get(action)
        if not tool_name:
            return {
                "success": False,
                "error": f"Unknown action: {action}. Available actions: {list(tool_mapping.keys())}",
                "action": action
            }
        
        # Prepare arguments
        arguments = {"user_id": user_id, **kwargs}
        
        # Execute the tool
        return await self.call_tool(tool_name, arguments)
    
    async def list_resources(self) -> List[Dict[str, Any]]:
        """List available resources from the MCP server."""
        if hasattr(self, '_use_direct_server'):
            # Direct server access for development
            from .mcp_server import google_mcp_server
            # Get the list_resources handler directly from the server
            handler = None
            for handler_info in google_mcp_server.server._handlers:
                if hasattr(handler_info, 'method') and handler_info.method == 'resources/list':
                    handler = handler_info.handler
                    break
            
            if handler:
                result = await handler()
                return [
                    {
                        "uri": resource.uri,
                        "name": resource.name,
                        "description": resource.description
                    }
                    for resource in result.resources
                ]
            else:
                return []
        
        if not self.session:
            raise RuntimeError("Not connected to MCP server. Call connect() first.")
        
        result = await self.session.list_resources(ListResourcesRequest())
        return [
            {
                "uri": resource.uri,
                "name": resource.name,
                "description": resource.description
            }
            for resource in result.resources
        ]


# Global instance for use throughout the application
google_mcp_client = GoogleMCPClient()


async def get_mcp_client() -> GoogleMCPClient:
    """Get the global MCP client instance, ensuring it's connected."""
    if not hasattr(google_mcp_client, 'session') or google_mcp_client.session is None:
        await google_mcp_client.connect()
    return google_mcp_client


# Convenience functions for common operations
async def execute_gmail_action(action: str, user_id: str, **kwargs) -> Dict[str, Any]:
    """Execute a Gmail action through MCP."""
    client = await get_mcp_client()
    return await client.execute_google_tool(action, user_id, **kwargs)


async def execute_drive_action(action: str, user_id: str, **kwargs) -> Dict[str, Any]:
    """Execute a Google Drive action through MCP."""
    client = await get_mcp_client()
    return await client.execute_google_tool(action, user_id, **kwargs)


async def execute_calendar_action(action: str, user_id: str, **kwargs) -> Dict[str, Any]:
    """Execute a Google Calendar action through MCP."""
    client = await get_mcp_client()
    return await client.execute_google_tool(action, user_id, **kwargs)


async def get_all_google_tools() -> List[Dict[str, Any]]:
    """Get all available Google tools formatted for OpenAI."""
    client = await get_mcp_client()
    return await client.get_available_tools_for_openai()
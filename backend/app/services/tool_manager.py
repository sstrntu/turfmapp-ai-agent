"""
Tool Manager for Agentic Chatbot Integration

This module manages all available tools that the agentic chatbot can use.
It provides a unified interface for tool discovery, execution, and management.
Now enhanced with MCP (Model Context Protocol) integration for Google services.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
import json
import asyncio

class ToolManager:
    """Manages all available tools for the agentic chatbot (non-Google services)."""
    
    def __init__(self):
        # Traditional tools (non-Google services only)
        # Google services are now handled via MCP
        self.tools = {
            # Add non-Google tools here as they're created
            # "database": database_tool,
            # "file_processing": file_processing_tool,
        }
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get all available tools as OpenAI function definitions."""
        return [tool.get_tool_definition() for tool in self.tools.values()]
    
    def get_tool_by_name(self, name: str):
        """Get a specific tool by name."""
        return self.tools.get(name)
    
    async def execute_tool(self, tool_name: str, user_id: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool with the given parameters."""
        tool = self.get_tool_by_name(tool_name)
        
        if not tool:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found",
                "available_tools": list(self.tools.keys())
            }
        
        try:
            result = await tool.execute(user_id, **kwargs)
            return result
        except Exception as e:
            return {
                "success": False,
                "error": f"Tool execution error: {str(e)}",
                "tool": tool_name
            }
    
    def get_tool_descriptions(self) -> Dict[str, str]:
        """Get descriptions of all available tools."""
        return {
            name: tool.description 
            for name, tool in self.tools.items()
        }
    
    def add_tool(self, name: str, tool):
        """Add a new tool to the manager."""
        self.tools[name] = tool
    
    def remove_tool(self, name: str):
        """Remove a tool from the manager."""
        if name in self.tools:
            del self.tools[name]
    
    async def get_all_tools_with_mcp(self) -> List[Dict[str, Any]]:
        """Get all available tools including MCP Google tools."""
        try:
            # Get traditional tools
            traditional_tools = self.get_available_tools()
            
            # Get MCP tools
            from .mcp_client import get_all_google_tools
            mcp_tools = await get_all_google_tools()
            
            # Convert MCP tools to OpenAI function format
            mcp_openai_tools = []
            for mcp_tool in mcp_tools:
                openai_tool = {
                    "type": "function",
                    "function": {
                        "name": mcp_tool.get("name"),
                        "description": mcp_tool.get("description"),
                        "parameters": mcp_tool.get("inputSchema")
                    }
                }
                mcp_openai_tools.append(openai_tool)
            
            # Combine both sets
            return traditional_tools + mcp_openai_tools
            
        except Exception as e:
            print(f"❌ Failed to get MCP tools in tool manager: {e}")
            # Fallback to traditional tools only
            return self.get_available_tools()
    
    async def get_all_descriptions_with_mcp(self) -> Dict[str, str]:
        """Get descriptions of all available tools including MCP tools."""
        try:
            # Get traditional descriptions
            traditional_descriptions = self.get_tool_descriptions()
            
            # Get MCP tools
            from .mcp_client import get_all_google_tools
            mcp_tools = await get_all_google_tools()
            
            # Extract MCP tool descriptions
            mcp_descriptions = {}
            for mcp_tool in mcp_tools:
                tool_name = mcp_tool.get("name")
                tool_desc = mcp_tool.get("description")
                mcp_descriptions[tool_name] = tool_desc
            
            # Combine both sets
            return {**traditional_descriptions, **mcp_descriptions}
            
        except Exception as e:
            print(f"❌ Failed to get MCP tool descriptions: {e}")
            # Fallback to traditional descriptions only
            return self.get_tool_descriptions()
    
    def is_mcp_tool(self, tool_name: str) -> bool:
        """Check if a tool is an MCP tool."""
        mcp_tool_prefixes = ["gmail_", "drive_", "calendar_"]
        return any(tool_name.startswith(prefix) for prefix in mcp_tool_prefixes)


# Global instance
tool_manager = ToolManager()

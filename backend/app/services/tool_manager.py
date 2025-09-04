"""
Tool Manager for Agentic Chatbot Integration

This module manages all available tools that the agentic chatbot can use.
It provides a unified interface for tool discovery, execution, and management.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
import json

from .gmail_tool import gmail_tool


class ToolManager:
    """Manages all available tools for the agentic chatbot."""
    
    def __init__(self):
        self.tools = {
            "gmail": gmail_tool,
            # Add more tools here as they're created
            # "calendar": calendar_tool,
            # "drive": drive_tool,
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


# Global instance
tool_manager = ToolManager()

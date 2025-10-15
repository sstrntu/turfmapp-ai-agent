"""
Simplified MCP Client for Google Services Integration

This is a simplified MCP client that provides the same interface but
directly calls the Google OAuth service methods, bypassing the complex
MCP server architecture for now.

Refactored (Phase 3 - January 2025):
- Split handler methods into focused modules in mcp/ subdirectory
- Gmail, Drive, and Calendar handlers are now separate modules
"""

from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional

from .google_oauth import google_oauth_service
from ..api.v1.google_api import get_user_google_credentials
from .mcp import handle_gmail_tool, handle_drive_tool, handle_calendar_tool

logger = logging.getLogger(__name__)


class SimplifiedGoogleMCPClient:
    """Simplified MCP Client for Google Services integration."""
    
    def __init__(self):
        self._tools_cache: Optional[List[Dict[str, Any]]] = None
        
    async def connect(self):
        """Connect (no-op for simplified client)."""
        pass
        
    async def disconnect(self):
        """Disconnect (no-op for simplified client)."""
        pass
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """Get list of available Google service tools with their schemas.

        Returns a comprehensive list of all available tools for Gmail, Google Drive,
        and Google Calendar. Results are cached after the first call for efficiency.

        Returns:
            List[Dict[str, Any]]: A list of tool definitions, where each tool is a dictionary containing:
                - name (str): The unique identifier for the tool
                - description (str): Human-readable description of what the tool does
                - inputSchema (dict): JSON schema defining the tool's input parameters including:
                    - type (str): Schema type (typically "object")
                    - properties (dict): Parameter definitions with types and descriptions
                    - required (list): List of required parameter names

        Raises:
            None: This method does not raise exceptions.
        """
        if self._tools_cache:
            return self._tools_cache
        
        tools = [
            # Gmail Tools
            {
                "name": "gmail_search",
                "description": "Search Gmail messages with query parameters. ONLY use when user explicitly asks about their emails, inbox, or specific email content. DO NOT use for general knowledge questions.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Gmail search query", "default": ""},
                        "max_results": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
                        "account": {"type": "string", "description": "Specific Gmail account email (optional)"}
                    },
                    "required": []
                }
            },
            {
                "name": "gmail_get_message",
                "description": "Get full content of a specific Gmail message. ONLY use when user explicitly asks about their emails or specific email content.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "message_id": {"type": "string", "description": "Gmail message ID"},
                        "account": {"type": "string", "description": "Specific Gmail account email (optional)"}
                    },
                    "required": ["message_id"]
                }
            },
            {
                "name": "gmail_recent",
                "description": "Get recent Gmail messages. ONLY use when user explicitly asks about their emails or inbox.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "max_results": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
                        "account": {"type": "string", "description": "Specific Gmail account email (optional)"}
                    },
                    "required": []
                }
            },
            {
                "name": "gmail_important",
                "description": "Get important/starred Gmail messages. ONLY use when user explicitly asks about their emails or important messages.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "max_results": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
                        "account": {"type": "string", "description": "Specific Gmail account email (optional)"}
                    },
                    "required": []
                }
            },
            
            # Google Drive Tools
            {
                "name": "drive_list_files",
                "description": "List files in Google Drive. ONLY use when user explicitly asks about their files, documents, or Drive content.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Drive search query", "default": ""},
                        "max_results": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
                        "account": {"type": "string", "description": "Specific Google account email (optional)"}
                    },
                    "required": []
                }
            },
            {
                "name": "drive_create_folder",
                "description": "Create folder structure in Google Drive. ONLY use when user explicitly asks to create folders or organize their Drive.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "folder_path": {"type": "string", "description": "Folder path to create"},
                        "root_folder": {"type": "string", "default": "TURFMAPP", "description": "Root folder name"},
                        "account": {"type": "string", "description": "Specific Google account email (optional)"}
                    },
                    "required": ["folder_path"]
                }
            },
            {
                "name": "drive_list_folder_files",
                "description": "List files in a specific Drive folder. ONLY use when user explicitly asks about their files in a specific folder.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "folder_path": {"type": "string", "description": "Folder path to list files from"},
                        "account": {"type": "string", "description": "Specific Google account email (optional)"}
                    },
                    "required": ["folder_path"]
                }
            },
            {
                "name": "drive_shared_drives",
                "description": "List shared drives (Team Drives) that the user has access to. ONLY use when user explicitly asks about their shared drives or team drives.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "max_results": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
                        "account": {"type": "string", "description": "Specific Google account email (optional)"}
                    },
                    "required": []
                }
            },
            {
                "name": "drive_search",
                "description": "Advanced search for files in Google Drive with filters for content, file type, and year. Perfect for queries like 'photos of Team A in 2022' or 'documents about project'.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "search_term": {"type": "string", "description": "Search term to look for in file names and content"},
                        "file_type": {"type": "string", "description": "File type filter: 'photos/images', 'documents', 'videos', 'folders', or specific mimeType"},
                        "year": {"type": "string", "description": "Year filter (e.g., '2022') to find files from that year"},
                        "max_results": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
                        "account": {"type": "string", "description": "Specific Google account email (optional)"}
                    },
                    "required": []
                }
            },
            {
                "name": "drive_search_folders",
                "description": "Search specifically for folders in Google Drive by name. Use when user is looking for a specific folder or directory.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "folder_name": {"type": "string", "description": "Name of the folder to search for"},
                        "max_results": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
                        "account": {"type": "string", "description": "Specific Google account email (optional)"}
                    },
                    "required": ["folder_name"]
                }
            },
            
            # Google Calendar Tools
            {
                "name": "calendar_list_events",
                "description": "List Google Calendar events. ONLY use when user explicitly asks about their calendar, schedule, or events.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "calendar_id": {"type": "string", "default": "primary", "description": "Calendar ID to list events from"},
                        "max_results": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
                        "account": {"type": "string", "description": "Specific Google account email (optional)"}
                    },
                    "required": []
                }
            },
            {
                "name": "calendar_upcoming_events", 
                "description": "Get upcoming calendar events for the next week. ONLY use when user explicitly asks about their upcoming schedule or events.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "days": {"type": "integer", "default": 7, "description": "Number of days to look ahead"},
                        "account": {"type": "string", "description": "Specific Google account email (optional)"}
                    },
                    "required": []
                }
            }
        ]
        
        self._tools_cache = tools
        return tools
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool by name with arguments, handling authentication and routing.

        Central dispatcher for all tool calls. Validates user credentials, filters
        placeholder account values, and routes requests to the appropriate service
        handler (Gmail, Drive, or Calendar).

        Args:
            tool_name (str): The name of the tool to execute (e.g., "gmail_search",
                "drive_list_files", "calendar_upcoming_events").
            arguments (Dict[str, Any]): Arguments for the tool call. Must include:
                - user_id (str): Required user ID for authentication
                - account (str, optional): Specific account email to use
                Additional arguments depend on the specific tool being called.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - success (bool): Whether the operation succeeded
                - response (str, optional): Formatted response text if successful
                - error (str, optional): Error message if success is False
                - tool (str): The name of the tool that was executed

        Raises:
            Exception: Caught internally and returned as error in response dict.
        """
        try:
            user_id = arguments.get("user_id")
            if not user_id:
                return {"success": False, "error": "user_id is required", "tool": tool_name}
            
            account = arguments.get("account")
            
            # Filter out placeholder account values that AI might provide
            placeholder_accounts = [
                "user's account email", "user account email", "user email", "user's email",
                "user@example.com", "example@gmail.com", "account email", "your account"
            ]
            if account and account.lower() in [p.lower() for p in placeholder_accounts]:
                logger.debug(f"🔧 Filtering out placeholder account: '{account}' -> using primary account")
                account = None  # Use primary account instead

            logger.debug(f"🔧 Processed account parameter: '{account}' (user_id: {user_id})")
            
            # Get user credentials
            try:
                credentials = await get_user_google_credentials(user_id, account)
            except Exception as e:
                return {"success": False, "error": f"Failed to get Google credentials: {str(e)}", "tool": tool_name}
            
            # Route to appropriate handler
            if tool_name.startswith("gmail_"):
                return await handle_gmail_tool(tool_name, credentials, arguments, google_oauth_service)
            elif tool_name.startswith("drive_"):
                return await handle_drive_tool(tool_name, credentials, arguments, google_oauth_service)
            elif tool_name.startswith("calendar_"):
                return await handle_calendar_tool(tool_name, credentials, arguments, google_oauth_service)
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}", "tool": tool_name}

        except Exception as e:
            return {"success": False, "error": f"Tool execution failed: {str(e)}", "tool": tool_name}
    
    async def get_available_tools_for_openai(self) -> List[Dict[str, Any]]:
        """Get tools formatted for OpenAI function calling API.

        Transforms internal tool definitions into the format expected by OpenAI's
        function calling API. Each tool is converted to include a "type" field and
        renamed fields to match OpenAI's schema.

        Returns:
            List[Dict[str, Any]]: A list of tool definitions formatted for OpenAI, where each tool contains:
                - type (str): Always "function" for OpenAI function calling
                - name (str): The function name
                - description (str): The function description
                - parameters (dict): The input schema (renamed from inputSchema)

        Raises:
            Exception: May propagate exceptions from list_tools().
        """
        tools = await self.list_tools()
        
        openai_tools = []
        for tool in tools:
            openai_tool = {
                "type": "function",
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["inputSchema"]
            }
            openai_tools.append(openai_tool)
        
        return openai_tools
    
    async def execute_google_tool(self, action: str, user_id: str, **kwargs) -> Dict[str, Any]:
        """Execute a Google service tool with simplified interface using action mapping.

        Provides a high-level interface for executing Google service tools by mapping
        user-friendly action names to internal tool names. This method simplifies
        tool execution by accepting action strings instead of full tool names.

        Args:
            action (str): The action to perform. Supported actions include:
                - Gmail: "search", "recent", "find_recent", "important", "find_important",
                  "read", "get_message"
                - Drive: "list_files", "create_folder", "list_folder_files"
                - Calendar: "list_events", "upcoming_events"
            user_id (str): The user ID for authentication and credential lookup.
            **kwargs: Additional keyword arguments to pass to the underlying tool,
                such as query parameters, max_results, folder_path, etc.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - success (bool): Whether the operation succeeded
                - response (str): Formatted response text with results
                - tool (str): The name of the tool that was executed
                - error (str, optional): Error message if success is False
                - action (str, optional): The action name if it was unknown

        Raises:
            Exception: Caught internally by call_tool and returned as error in response dict.
        """
        # Map actions to tool names
        tool_mapping = {
            "search": "gmail_search",
            "recent": "gmail_recent", 
            "find_recent": "gmail_recent",
            "important": "gmail_important",
            "find_important": "gmail_important",
            "read": "gmail_get_message",
            "get_message": "gmail_get_message",
            "list_files": "drive_list_files",
            "create_folder": "drive_create_folder",
            "list_folder_files": "drive_list_folder_files",
            "list_events": "calendar_list_events",
            "upcoming_events": "calendar_upcoming_events"
        }
        
        tool_name = tool_mapping.get(action)
        if not tool_name:
            return {"success": False, "error": f"Unknown action: {action}. Available actions: {list(tool_mapping.keys())}", "action": action}
        
        # Prepare arguments
        arguments = {"user_id": user_id, **kwargs}
        
        # Execute the tool
        return await self.call_tool(tool_name, arguments)


# Global instance for use throughout the application
google_mcp_client = SimplifiedGoogleMCPClient()


async def get_mcp_client() -> SimplifiedGoogleMCPClient:
    """Get the global MCP client instance, ensuring it's connected.

    Returns the singleton instance of SimplifiedGoogleMCPClient and ensures
    it is properly connected before returning.

    Returns:
        SimplifiedGoogleMCPClient: The global MCP client instance ready for use.

    Raises:
        Exception: May propagate exceptions from connect() method.
    """
    await google_mcp_client.connect()
    return google_mcp_client


# Convenience functions for common operations
async def execute_gmail_action(action: str, user_id: str, **kwargs) -> Dict[str, Any]:
    """Execute a Gmail action through MCP client.

    Convenience function for executing Gmail-specific actions. This is a wrapper
    around the MCP client's execute_google_tool method.

    Args:
        action (str): The Gmail action to perform (e.g., "search", "recent", "important").
        user_id (str): The user ID for authentication.
        **kwargs: Additional keyword arguments to pass to the tool (e.g., query, max_results).

    Returns:
        Dict[str, Any]: Response dictionary from the tool execution containing success status and results.

    Raises:
        Exception: May propagate exceptions from get_mcp_client() or execute_google_tool().
    """
    client = await get_mcp_client()
    return await client.execute_google_tool(action, user_id, **kwargs)


async def execute_drive_action(action: str, user_id: str, **kwargs) -> Dict[str, Any]:
    """Execute a Google Drive action through MCP client.

    Convenience function for executing Google Drive-specific actions. This is a wrapper
    around the MCP client's execute_google_tool method.

    Args:
        action (str): The Drive action to perform (e.g., "list_files", "create_folder").
        user_id (str): The user ID for authentication.
        **kwargs: Additional keyword arguments to pass to the tool (e.g., query, folder_path).

    Returns:
        Dict[str, Any]: Response dictionary from the tool execution containing success status and results.

    Raises:
        Exception: May propagate exceptions from get_mcp_client() or execute_google_tool().
    """
    client = await get_mcp_client()
    return await client.execute_google_tool(action, user_id, **kwargs)


async def execute_calendar_action(action: str, user_id: str, **kwargs) -> Dict[str, Any]:
    """Execute a Google Calendar action through MCP client.

    Convenience function for executing Google Calendar-specific actions. This is a wrapper
    around the MCP client's execute_google_tool method.

    Args:
        action (str): The Calendar action to perform (e.g., "list_events", "upcoming_events").
        user_id (str): The user ID for authentication.
        **kwargs: Additional keyword arguments to pass to the tool (e.g., calendar_id, days).

    Returns:
        Dict[str, Any]: Response dictionary from the tool execution containing success status and results.

    Raises:
        Exception: May propagate exceptions from get_mcp_client() or execute_google_tool().
    """
    client = await get_mcp_client()
    return await client.execute_google_tool(action, user_id, **kwargs)


async def get_all_google_tools() -> List[Dict[str, Any]]:
    """Get all available Google tools in raw MCP format.

    Convenience function to retrieve the complete list of available Google service tools
    in their internal MCP format.

    Returns:
        List[Dict[str, Any]]: List of tool definitions with names, descriptions, and input schemas.

    Raises:
        Exception: May propagate exceptions from get_mcp_client() or list_tools().
    """
    client = await get_mcp_client()
    return await client.list_tools()
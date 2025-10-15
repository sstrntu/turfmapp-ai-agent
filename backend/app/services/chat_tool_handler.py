"""
Chat Tool Handler - Tool Execution and Google MCP Integration

This module handles all tool-related functionality for the chat service, including:
- Google MCP tool integration (Gmail, Drive, Calendar)
- AI-driven tool selection and execution
- Function call parsing and result handling
- Tool availability checking and permission management

Refactored (Phase 3 - January 2025):
- Tool definitions extracted to chat_tool_definitions.py
- MCP request handling extracted to chat_mcp_handler.py
- Tool execution extracted to chat_tool_executor.py

Architecture:
- Integrates with ChatApiClient for AI-driven tool selection
- Uses google_mcp_client for Google service tool execution
- Supports parallel tool execution
- Provides intelligent fallback behavior
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any

from .chat_tool_definitions import build_google_function_tools as _build_google_function_tools
from .chat_mcp_handler import handle_google_mcp_request as _handle_google_mcp_request
from .chat_mcp_handler import extract_gmail_search_query as _extract_gmail_search_query
from .chat_tool_executor import handle_tool_calls as _handle_tool_calls

logger = logging.getLogger(__name__)


class ChatToolHandler:
    """Handler for chat tool execution and Google MCP integration."""

    def __init__(self, chat_api_client):
        """Initialize the ChatToolHandler with required dependencies.

        Sets up the tool handler with a ChatApiClient instance that will be used
        for AI-driven tool selection and function calling capabilities.

        Args:
            chat_api_client: ChatApiClient instance that provides access to the
                AI API for tool selection and message processing. Must support
                call_responses_api method for function calling.

        Returns:
            None

        Example:
            >>> from app.services.chat_api_client import ChatApiClient
            >>> api_client = ChatApiClient()
            >>> handler = ChatToolHandler(api_client)
        """
        self.chat_api_client = chat_api_client

    def build_google_function_tools(self, enabled_tools: Dict[str, bool]) -> List[Dict[str, Any]]:
        """Build function tool definitions for enabled Google services.

        Wrapper method that delegates to the extracted build_google_function_tools function.

        Args:
            enabled_tools (Dict[str, bool]): Dictionary mapping service names to their
                enabled state. Supported keys are 'gmail', 'calendar', and 'drive'.

        Returns:
            List[Dict[str, Any]]: List of tool definitions for AI function calling.
        """
        return _build_google_function_tools(enabled_tools)

    async def handle_google_mcp_request(
        self,
        user_message: str,
        conversation_history: List[Dict[str, Any]],
        user_id: str,
        enabled_tools: Dict[str, bool],
        **kwargs
    ) -> Dict[str, Any]:
        """Handle Google MCP request using AI-driven tool selection.

        Wrapper method that delegates to the extracted handle_google_mcp_request function.

        Args:
            user_message (str): The user's natural language request or question.
            conversation_history (List[Dict[str, Any]]): Previous messages in the
                conversation for context.
            user_id (str): Unique identifier for the user making the request.
            enabled_tools (Dict[str, bool]): Dictionary of enabled Google services.
            **kwargs: Additional keyword arguments for future extensibility.

        Returns:
            Dict[str, Any]: Response dictionary with success status and response text.
        """
        available_tools = self.build_google_function_tools(enabled_tools)
        return await _handle_google_mcp_request(
            chat_api_client=self.chat_api_client,
            user_message=user_message,
            conversation_history=conversation_history,
            user_id=user_id,
            enabled_tools=enabled_tools,
            available_tools=available_tools,
            **kwargs
        )

    def extract_gmail_search_query(self, user_message: str) -> str:
        """Extract search query from user message for Gmail search.

        Wrapper method that delegates to the extracted extract_gmail_search_query function.

        Args:
            user_message (str): The user's natural language message containing a search request.

        Returns:
            str: Extracted search query string, limited to 100 characters.
        """
        return _extract_gmail_search_query(user_message)

    async def handle_tool_calls(self, user_id: str, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Handle tool calls from the AI assistant with MCP integration.

        Wrapper method that delegates to the extracted handle_tool_calls function.

        Args:
            user_id (str): Unique identifier for the user making the request.
            tool_calls (List[Dict[str, Any]]): List of tool call dictionaries from the AI assistant.

        Returns:
            List[Dict[str, Any]]: List of tool execution results.
        """
        return await _handle_tool_calls(user_id, tool_calls)


# Global instance for convenience
chat_tool_handler = None  # Will be initialized after ChatApiClient is available

"""
MCP (Model Context Protocol) handlers package.

This package contains handler modules for different Google services:
- Gmail operations (search, read, recent, important)
- Google Drive operations (list, search, folders, shared drives)
- Google Calendar operations (list events, upcoming events)
"""

from .mcp_gmail_handler import handle_gmail_tool
from .mcp_drive_handler import handle_drive_tool
from .mcp_calendar_handler import handle_calendar_tool

__all__ = [
    "handle_gmail_tool",
    "handle_drive_tool",
    "handle_calendar_tool",
]

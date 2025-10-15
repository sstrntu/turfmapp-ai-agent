"""
Tool Definitions for Google Services

This module contains function tool definitions for Google services (Gmail, Calendar, Drive).
Each service provides multiple tool schemas with parameters and descriptions for AI function calling.

Extracted from chat_tool_handler.py (Phase 3 - January 2025)
"""

from __future__ import annotations

from typing import List, Dict, Any


def build_google_function_tools(enabled_tools: Dict[str, bool]) -> List[Dict[str, Any]]:
    """Build function tool definitions for enabled Google services.

    Constructs a list of function tool definitions based on which Google services
    are enabled. Each service (Gmail, Calendar, Drive) provides multiple tool
    definitions with their parameters and descriptions for AI function calling.

    Args:
        enabled_tools (Dict[str, bool]): Dictionary mapping service names to their
            enabled state. Supported keys are 'gmail', 'calendar', and 'drive'.
            Example: {'gmail': True, 'calendar': False, 'drive': True}

    Returns:
        List[Dict[str, Any]]: List of tool definitions in the format expected by
            AI function calling APIs. Each tool definition includes:
            - type: Always 'function'
            - function: Object containing name, description, and parameters
            Returns empty list if no tools are enabled.

    Example:
        >>> tools = build_google_function_tools({'gmail': True, 'drive': False})
        >>> len(tools)  # Returns number of Gmail tools
        4
    """
    available_tools: List[Dict[str, Any]] = []

    if not enabled_tools:
        return available_tools

    if enabled_tools.get("gmail"):
        available_tools.extend([
            {
                "type": "function",
                "function": {
                    "name": "gmail_recent",
                    "description": "Get the most recent Gmail messages in chronological order. Use this when users ask about 'latest', 'recent', 'first', 'newest', or 'last' emails. Perfect for questions like 'what is my first email about?' or 'show me my latest message'. This tool retrieves emails by recency, not by search criteria.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "max_results": {
                                "type": "integer",
                                "description": "Number of emails to retrieve. Use 1 for 'first/latest/newest', 3-5 for 'recent emails', up to 10 for broader requests.",
                                "default": 5,
                                "minimum": 1,
                                "maximum": 50,
                            }
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "gmail_search",
                    "description": "Search Gmail messages using specific queries. Use this when users want to find emails about specific topics, from specific people, or containing certain keywords. Do NOT use for recent/latest emails - use gmail_recent instead. Perfect for 'find emails from John', 'emails about project', or 'messages containing meeting'.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Gmail search query. Extract the main search terms from user's request. For 'emails from John' use 'John', for 'about project deadline' use 'project deadline'.",
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Number of emails to retrieve",
                                "default": 10,
                                "minimum": 1,
                                "maximum": 50,
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "gmail_get_message",
                    "description": "Retrieve the full content of a specific Gmail message. Use when the user references a particular email and needs the details.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message_id": {
                                "type": "string",
                                "description": "Gmail message ID to retrieve",
                            },
                        },
                        "required": ["message_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "gmail_important",
                    "description": "List important or starred Gmail messages. Use when the user requests important, starred, or priority emails.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "max_results": {
                                "type": "integer",
                                "description": "Number of important emails to retrieve",
                                "default": 5,
                                "minimum": 1,
                                "maximum": 50,
                            }
                        },
                    },
                },
            },
        ])

    if enabled_tools.get("calendar"):
        available_tools.append(
            {
                "type": "function",
                "function": {
                    "name": "calendar_upcoming_events",
                    "description": "Get upcoming calendar events and meetings. Use for scheduling questions, meeting inquiries, or calendar requests.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "max_results": {"type": "integer", "default": 5}
                        },
                    },
                },
            }
        )
        available_tools.append(
            {
                "type": "function",
                "function": {
                    "name": "calendar_list_events",
                    "description": "List Google Calendar events from a specific calendar. Use when the user asks about events on a certain calendar or timeframe.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "calendar_id": {
                                "type": "string",
                                "description": "Calendar ID to list events from",
                                "default": "primary",
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Number of events to list",
                                "default": 10,
                                "minimum": 1,
                                "maximum": 50,
                            },
                        },
                    },
                },
            }
        )

    if enabled_tools.get("drive"):
        available_tools.extend([
            {
                "type": "function",
                "function": {
                    "name": "drive_list_files",
                    "description": "List files in Google Drive. Use when users ask about their files, documents, or Drive content. Returns up to the requested number of files with metadata.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Optional Drive search query to filter results",
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Number of files to list",
                                "default": 10,
                                "minimum": 1,
                                "maximum": 50,
                            },
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "drive_search",
                    "description": "Advanced search for files in Google Drive with filters for content, file type, and year. Perfect for queries like 'photos of Team A in 2022' or 'documents about project'.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "search_term": {
                                "type": "string",
                                "description": "Search term for file names or content",
                            },
                            "file_type": {
                                "type": "string",
                                "description": "File type filter such as 'documents', 'images', or exact mime type",
                            },
                            "year": {
                                "type": "string",
                                "description": "Optional year filter (e.g., '2024')",
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Number of files to return",
                                "default": 10,
                                "minimum": 1,
                                "maximum": 50,
                            },
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "drive_search_folders",
                    "description": "Search for folders in Google Drive by name. Use when the user is looking for a specific folder or directory.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "folder_name": {
                                "type": "string",
                                "description": "Name of the folder to search for",
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Number of folders to return",
                                "default": 10,
                                "minimum": 1,
                                "maximum": 50,
                            },
                        },
                        "required": ["folder_name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "drive_list_folder_files",
                    "description": "List files in a specific Google Drive folder. Use when the user references a known folder.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "folder_path": {
                                "type": "string",
                                "description": "Drive folder path to list files from",
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Number of files to return",
                                "default": 10,
                                "minimum": 1,
                                "maximum": 50,
                            },
                        },
                        "required": ["folder_path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "drive_create_folder",
                    "description": "Create a folder structure in Google Drive. Use when the user explicitly asks to create folders or organize files.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "folder_path": {
                                "type": "string",
                                "description": "Folder path to create (supports nested paths)",
                            },
                            "root_folder": {
                                "type": "string",
                                "description": "Optional root folder override",
                                "default": "TURFMAPP",
                            },
                        },
                        "required": ["folder_path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "drive_shared_drives",
                    "description": "List shared drives (Team Drives) that the user can access. Use when they ask about shared or team drives.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "max_results": {
                                "type": "integer",
                                "description": "Number of shared drives to list",
                                "default": 10,
                                "minimum": 1,
                                "maximum": 50,
                            },
                        },
                    },
                },
            },
        ])

    return available_tools

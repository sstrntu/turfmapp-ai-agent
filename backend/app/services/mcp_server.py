"""
Google Services MCP Server

This module implements a Model Context Protocol (MCP) server that wraps
the existing Google OAuth service to provide standardized access to
Gmail, Google Drive, and Google Calendar APIs through the MCP protocol.
"""

from __future__ import annotations

import asyncio
import json
from typing import Dict, Any, List, Optional, Sequence

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import (
    Tool,
    TextContent,
    CallToolRequest,
    CallToolResult,
    Resource,
    ListResourcesResult,
    ReadResourceRequest,
    ReadResourceResult,
    McpError,
    ErrorCode
)

from .google_oauth import google_oauth_service
from ..api.v1.google_api import get_user_google_credentials


class GoogleMCPServer:
    """MCP Server for Google Services integration."""
    
    def __init__(self):
        self.server = Server("google-services")
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Set up MCP protocol handlers."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available Google services tools."""
            return [
                # Gmail Tools
                Tool(
                    name="gmail_search",
                    description="Search Gmail messages with query parameters. Use this when the user asks about their emails, inbox, messages, or when they want to find specific emails. Also use for follow-up questions about email content mentioned in conversation.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "string",
                                "description": "User ID for authentication"
                            },
                            "query": {
                                "type": "string", 
                                "description": "Gmail search query (e.g., 'from:john@example.com', 'subject:meeting')",
                                "default": ""
                            },
                            "max_results": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 50,
                                "default": 10,
                                "description": "Maximum number of messages to return"
                            },
                            "account": {
                                "type": "string",
                                "description": "Specific Gmail account email (optional, uses primary if not specified)"
                            }
                        },
                        "required": ["user_id"]
                    }
                ),
                Tool(
                    name="gmail_get_message",
                    description="Get full content of a specific Gmail message. Use this when you need the complete details of an email that was found in a previous search, or when the user asks to read a specific email in detail.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "string",
                                "description": "User ID for authentication"
                            },
                            "message_id": {
                                "type": "string",
                                "description": "Gmail message ID"
                            },
                            "account": {
                                "type": "string",
                                "description": "Specific Gmail account email (optional)"
                            }
                        },
                        "required": ["user_id", "message_id"]
                    }
                ),
                Tool(
                    name="gmail_recent",
                    description="Get recent Gmail messages",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "string",
                                "description": "User ID for authentication"
                            },
                            "max_results": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 50,
                                "default": 10,
                                "description": "Maximum number of messages to return"
                            },
                            "account": {
                                "type": "string",
                                "description": "Specific Gmail account email (optional)"
                            }
                        },
                        "required": ["user_id"]
                    }
                ),
                Tool(
                    name="gmail_important",
                    description="Get important/starred Gmail messages. Use this when the user asks about important emails, starred messages, or priority emails.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "string",
                                "description": "User ID for authentication"
                            },
                            "max_results": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 50,
                                "default": 10,
                                "description": "Maximum number of messages to return"
                            },
                            "account": {
                                "type": "string",
                                "description": "Specific Gmail account email (optional)"
                            }
                        },
                        "required": ["user_id"]
                    }
                ),
                
                # Google Drive Tools
                Tool(
                    name="drive_list_files",
                    description="List files in Google Drive. Use this when the user asks about their files, documents, folders, or when they want to see what's in their Drive. Also use for follow-up questions about files mentioned in conversation.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "string",
                                "description": "User ID for authentication"
                            },
                            "query": {
                                "type": "string",
                                "description": "Drive search query",
                                "default": ""
                            },
                            "max_results": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 50,
                                "default": 10,
                                "description": "Maximum number of files to return"
                            },
                            "account": {
                                "type": "string",
                                "description": "Specific Google account email (optional)"
                            }
                        },
                        "required": ["user_id"]
                    }
                ),
                Tool(
                    name="drive_create_folder",
                    description="Create folder structure in Google Drive",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "string",
                                "description": "User ID for authentication"
                            },
                            "folder_path": {
                                "type": "string",
                                "description": "Folder path to create (e.g., 'Projects/Client/Documents')"
                            },
                            "root_folder": {
                                "type": "string",
                                "default": "TURFMAPP",
                                "description": "Root folder name"
                            },
                            "account": {
                                "type": "string",
                                "description": "Specific Google account email (optional)"
                            }
                        },
                        "required": ["user_id", "folder_path"]
                    }
                ),
                Tool(
                    name="drive_list_folder_files",
                    description="List files in a specific Drive folder",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "string",
                                "description": "User ID for authentication"
                            },
                            "folder_path": {
                                "type": "string",
                                "description": "Folder path to list files from"
                            },
                            "account": {
                                "type": "string",
                                "description": "Specific Google account email (optional)"
                            }
                        },
                        "required": ["user_id", "folder_path"]
                    }
                ),
                
                # Google Calendar Tools
                Tool(
                    name="calendar_list_events",
                    description="List Google Calendar events. Use this when the user asks about their calendar, meetings, events, schedule, or appointments. Also use for follow-up questions about calendar events mentioned in conversation.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "string",
                                "description": "User ID for authentication"
                            },
                            "calendar_id": {
                                "type": "string",
                                "default": "primary",
                                "description": "Calendar ID to list events from"
                            },
                            "max_results": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 50,
                                "default": 10,
                                "description": "Maximum number of events to return"
                            },
                            "account": {
                                "type": "string",
                                "description": "Specific Google account email (optional)"
                            }
                        },
                        "required": ["user_id"]
                    }
                ),
                Tool(
                    name="calendar_upcoming_events",
                    description="Get upcoming calendar events for the next week",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "string",
                                "description": "User ID for authentication"
                            },
                            "days": {
                                "type": "integer",
                                "default": 7,
                                "description": "Number of days to look ahead"
                            },
                            "account": {
                                "type": "string",
                                "description": "Specific Google account email (optional)"
                            }
                        },
                        "required": ["user_id"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            """Handle tool execution requests."""
            try:
                user_id = arguments.get("user_id")
                if not user_id:
                    raise McpError(ErrorCode.InvalidParams, "user_id is required")
                
                account = arguments.get("account")
                
                # Get user credentials
                try:
                    credentials = await get_user_google_credentials(user_id, account)
                except Exception as e:
                    raise McpError(
                        ErrorCode.InternalError,
                        f"Failed to get Google credentials: {str(e)}"
                    )
                
                # Route to appropriate handler
                if name.startswith("gmail_"):
                    return await self._handle_gmail_tool(name, credentials, arguments)
                elif name.startswith("drive_"):
                    return await self._handle_drive_tool(name, credentials, arguments)
                elif name.startswith("calendar_"):
                    return await self._handle_calendar_tool(name, credentials, arguments)
                else:
                    raise McpError(ErrorCode.MethodNotFound, f"Unknown tool: {name}")
                    
            except McpError:
                raise
            except Exception as e:
                raise McpError(ErrorCode.InternalError, f"Tool execution failed: {str(e)}")
        
        @self.server.list_resources()
        async def handle_list_resources() -> ListResourcesResult:
            """List available Google services resources."""
            return ListResourcesResult(
                resources=[
                    Resource(
                        uri="google://gmail/messages",
                        name="Gmail Messages",
                        description="Access to Gmail messages and threads"
                    ),
                    Resource(
                        uri="google://drive/files",
                        name="Google Drive Files",
                        description="Access to Google Drive files and folders"
                    ),
                    Resource(
                        uri="google://calendar/events", 
                        name="Google Calendar Events",
                        description="Access to Google Calendar events and schedules"
                    )
                ]
            )
        
        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> ReadResourceResult:
            """Handle resource read requests."""
            # This would be implemented for specific resource access patterns
            # For now, return a simple response
            return ReadResourceResult(
                contents=[
                    TextContent(
                        type="text",
                        text=f"Resource {uri} access requires specific tool calls. Use the available tools to interact with Google services."
                    )
                ]
            )
    
    async def _handle_gmail_tool(self, name: str, credentials, arguments: Dict[str, Any]) -> CallToolResult:
        """Handle Gmail tool calls."""
        try:
            if name == "gmail_search":
                query = arguments.get("query", "")
                max_results = arguments.get("max_results", 10)
                
                result = await google_oauth_service.get_gmail_messages(
                    credentials=credentials,
                    query=query,
                    max_results=max_results
                )
                
                if "error" in result:
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=f"❌ Gmail search failed: {result['error']}"
                        )]
                    )
                
                messages = result.get("messages", [])
                if not messages:
                    response_text = "📭 No emails found for your search."
                else:
                    response_text = f"📧 **Found {len(messages)} emails:**\n\n"
                    for i, msg in enumerate(messages[:5], 1):
                        sender = msg.get('from', 'Unknown').split('<')[0].strip('"') if '<' in msg.get('from', '') else msg.get('from', 'Unknown')
                        response_text += f"{i}. **{sender}**\n"
                        response_text += f"   📄 {msg.get('subject', 'No Subject')}\n"
                        response_text += f"   📅 {msg.get('date', 'Unknown Date')}\n"
                        response_text += f"   📝 {msg.get('snippet', '')[:80]}...\n\n"
                    
                    if len(messages) > 5:
                        response_text += f"_...and {len(messages) - 5} more emails_"
                
                return CallToolResult(
                    content=[TextContent(type="text", text=response_text)]
                )
            
            elif name == "gmail_get_message":
                message_id = arguments.get("message_id")
                
                result = await google_oauth_service.get_gmail_message_content(
                    credentials=credentials,
                    message_id=message_id
                )
                
                if "error" in result:
                    return CallToolResult(
                        content=[TextContent(
                            type="text", 
                            text=f"❌ Failed to get message: {result['error']}"
                        )]
                    )
                
                response_text = f"📧 **Gmail Message ({message_id})**\n\n"
                response_text += f"**Snippet:** {result.get('snippet', 'No preview available')}\n\n"
                response_text += f"**Thread ID:** {result.get('threadId', 'N/A')}"
                
                return CallToolResult(
                    content=[TextContent(type="text", text=response_text)]
                )
            
            elif name == "gmail_recent":
                max_results = arguments.get("max_results", 10)
                
                result = await google_oauth_service.get_gmail_messages(
                    credentials=credentials,
                    query="newer:2024/01/01",
                    max_results=max_results
                )
                
                if "error" in result:
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=f"❌ Failed to get recent emails: {result['error']}"
                        )]
                    )
                
                messages = result.get("messages", [])
                if not messages:
                    response_text = "📭 No recent emails found."
                else:
                    response_text = f"📧 **Your {len(messages)} most recent emails:**\n\n"
                    for i, msg in enumerate(messages, 1):
                        sender = msg.get('from', 'Unknown').split('<')[0].strip('"') if '<' in msg.get('from', '') else msg.get('from', 'Unknown')
                        response_text += f"{i}. **{sender}** - {msg.get('subject', 'No Subject')}\n"
                        response_text += f"   _{msg.get('date', 'Unknown Date')}_\n\n"
                
                return CallToolResult(
                    content=[TextContent(type="text", text=response_text)]
                )
            
            elif name == "gmail_important":
                max_results = arguments.get("max_results", 10)
                
                result = await google_oauth_service.get_gmail_messages(
                    credentials=credentials,
                    query="is:important OR is:starred OR label:important",
                    max_results=max_results
                )
                
                if "error" in result:
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=f"❌ Failed to get important emails: {result['error']}"
                        )]
                    )
                
                messages = result.get("messages", [])
                if not messages:
                    response_text = "⭐ No important or starred emails found."
                else:
                    response_text = f"⭐ **Found {len(messages)} important emails:**\n\n"
                    for i, msg in enumerate(messages, 1):
                        sender = msg.get('from', 'Unknown').split('<')[0].strip('"') if '<' in msg.get('from', '') else msg.get('from', 'Unknown')
                        response_text += f"{i}. **{sender}**\n"
                        response_text += f"   ⭐ {msg.get('subject', 'No Subject')}\n"
                        response_text += f"   📅 {msg.get('date', 'Unknown Date')}\n"
                        response_text += f"   📄 {msg.get('snippet', '')[:80]}...\n\n"
                
                return CallToolResult(
                    content=[TextContent(type="text", text=response_text)]
                )
            
            else:
                raise McpError(ErrorCode.MethodNotFound, f"Unknown Gmail tool: {name}")
                
        except Exception as e:
            raise McpError(ErrorCode.InternalError, f"Gmail tool error: {str(e)}")
    
    async def _handle_drive_tool(self, name: str, credentials, arguments: Dict[str, Any]) -> CallToolResult:
        """Handle Google Drive tool calls."""
        try:
            if name == "drive_list_files":
                query = arguments.get("query", "")
                max_results = arguments.get("max_results", 10)
                
                result = await google_oauth_service.get_drive_files(
                    credentials=credentials,
                    query=query,
                    max_results=max_results
                )
                
                if "error" in result:
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=f"❌ Drive list failed: {result['error']}"
                        )]
                    )
                
                files = result.get("files", [])
                if not files:
                    response_text = "📁 No files found in Google Drive."
                else:
                    response_text = f"📁 **Found {len(files)} files in Google Drive:**\n\n"
                    for i, file in enumerate(files, 1):
                        file_name = file.get('name', 'Unknown')
                        file_type = file.get('mimeType', 'Unknown type')
                        file_size = file.get('size', 'Unknown size')
                        modified_time = file.get('modifiedTime', 'Unknown date')
                        
                        # Simplify mime type display
                        if 'folder' in file_type:
                            icon = "📁"
                        elif 'document' in file_type:
                            icon = "📄"
                        elif 'spreadsheet' in file_type:
                            icon = "📊"
                        elif 'presentation' in file_type:
                            icon = "📽️"
                        elif 'image' in file_type:
                            icon = "🖼️"
                        else:
                            icon = "📄"
                        
                        response_text += f"{i}. {icon} **{file_name}**\n"
                        response_text += f"   📅 Modified: {modified_time}\n"
                        if file_size and file_size != 'Unknown size':
                            response_text += f"   📊 Size: {file_size} bytes\n"
                        response_text += "\n"
                
                return CallToolResult(
                    content=[TextContent(type="text", text=response_text)]
                )
            
            elif name == "drive_create_folder":
                folder_path = arguments.get("folder_path")
                root_folder = arguments.get("root_folder", "TURFMAPP")
                
                try:
                    folder_id = await google_oauth_service.create_folder_structure(
                        credentials=credentials,
                        folder_path=folder_path,
                        root_folder=root_folder
                    )
                    
                    response_text = f"📁 **Folder created successfully!**\n\n"
                    response_text += f"**Path:** {root_folder}/{folder_path}\n"
                    response_text += f"**Folder ID:** {folder_id}"
                    
                    return CallToolResult(
                        content=[TextContent(type="text", text=response_text)]
                    )
                    
                except Exception as e:
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=f"❌ Failed to create folder: {str(e)}"
                        )]
                    )
            
            elif name == "drive_list_folder_files":
                folder_path = arguments.get("folder_path")
                
                result = await google_oauth_service.list_files_in_folder(
                    credentials=credentials,
                    folder_path=folder_path
                )
                
                if not result.get("success", False):
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=f"❌ Failed to list folder files: {result.get('error', 'Unknown error')}"
                        )]
                    )
                
                files = result.get("files", [])
                if not files:
                    response_text = f"📁 No files found in folder '{folder_path}'."
                else:
                    response_text = f"📁 **Files in '{folder_path}' ({len(files)} files):**\n\n"
                    for i, file in enumerate(files, 1):
                        file_name = file.get('name', 'Unknown')
                        file_type = file.get('mimeType', '')
                        
                        # File type icon
                        if 'folder' in file_type:
                            icon = "📁"
                        elif 'document' in file_type:
                            icon = "📄"
                        elif 'spreadsheet' in file_type:
                            icon = "📊"
                        elif 'presentation' in file_type:
                            icon = "📽️"
                        elif 'image' in file_type:
                            icon = "🖼️"
                        else:
                            icon = "📄"
                        
                        response_text += f"{i}. {icon} **{file_name}**\n"
                        response_text += f"   📅 Modified: {file.get('modifiedTime', 'Unknown')}\n\n"
                
                return CallToolResult(
                    content=[TextContent(type="text", text=response_text)]
                )
            
            else:
                raise McpError(ErrorCode.MethodNotFound, f"Unknown Drive tool: {name}")
                
        except Exception as e:
            raise McpError(ErrorCode.InternalError, f"Drive tool error: {str(e)}")
    
    async def _handle_calendar_tool(self, name: str, credentials, arguments: Dict[str, Any]) -> CallToolResult:
        """Handle Google Calendar tool calls."""
        try:
            if name == "calendar_list_events":
                calendar_id = arguments.get("calendar_id", "primary")
                max_results = arguments.get("max_results", 10)
                
                result = await google_oauth_service.get_calendar_events(
                    credentials=credentials,
                    calendar_id=calendar_id,
                    max_results=max_results
                )
                
                if "error" in result:
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=f"❌ Calendar access failed: {result['error']}"
                        )]
                    )
                
                events = result.get("events", [])
                if not events:
                    response_text = "📅 No calendar events found."
                else:
                    response_text = f"📅 **Found {len(events)} calendar events:**\n\n"
                    for i, event in enumerate(events, 1):
                        title = event.get('summary', 'No Title')
                        start_time = event.get('start', {})
                        end_time = event.get('end', {})
                        
                        # Format time
                        start_date = start_time.get('dateTime', start_time.get('date', 'Unknown time'))
                        end_date = end_time.get('dateTime', end_time.get('date', 'Unknown time'))
                        
                        response_text += f"{i}. **{title}**\n"
                        response_text += f"   🕐 Start: {start_date}\n"
                        response_text += f"   🕐 End: {end_date}\n"
                        
                        if event.get('location'):
                            response_text += f"   📍 Location: {event['location']}\n"
                        
                        if event.get('description'):
                            desc = event['description'][:100] + "..." if len(event['description']) > 100 else event['description']
                            response_text += f"   📝 Description: {desc}\n"
                        
                        response_text += "\n"
                
                return CallToolResult(
                    content=[TextContent(type="text", text=response_text)]
                )
            
            elif name == "calendar_upcoming_events":
                days = arguments.get("days", 7)
                
                # This would require implementing a more specific query for upcoming events
                # For now, use the basic list events
                result = await google_oauth_service.get_calendar_events(
                    credentials=credentials,
                    calendar_id="primary",
                    max_results=10
                )
                
                if "error" in result:
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=f"❌ Failed to get upcoming events: {result['error']}"
                        )]
                    )
                
                events = result.get("events", [])
                if not events:
                    response_text = f"📅 No upcoming events in the next {days} days."
                else:
                    response_text = f"📅 **Upcoming events (next {days} days):**\n\n"
                    for i, event in enumerate(events, 1):
                        title = event.get('summary', 'No Title')
                        start_time = event.get('start', {})
                        start_date = start_time.get('dateTime', start_time.get('date', 'Unknown time'))
                        
                        response_text += f"{i}. **{title}**\n"
                        response_text += f"   🕐 {start_date}\n\n"
                
                return CallToolResult(
                    content=[TextContent(type="text", text=response_text)]
                )
            
            else:
                raise McpError(ErrorCode.MethodNotFound, f"Unknown Calendar tool: {name}")
                
        except Exception as e:
            raise McpError(ErrorCode.InternalError, f"Calendar tool error: {str(e)}")
    
    async def run(self, host: str = "localhost", port: int = 8001):
        """Run the MCP server."""
        import uvicorn
        uvicorn.run(self.server.create_app(), host=host, port=port)


# Global instance
google_mcp_server = GoogleMCPServer()

# For standalone running
if __name__ == "__main__":
    asyncio.run(google_mcp_server.run())
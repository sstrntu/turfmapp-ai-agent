"""
Simplified MCP Client for Google Services Integration

This is a simplified MCP client that provides the same interface but
directly calls the Google OAuth service methods, bypassing the complex
MCP server architecture for now.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional

from .google_oauth import google_oauth_service
from ..api.v1.google_api import get_user_google_credentials
from ..core.logging_config import get_logger

logger = get_logger(__name__)


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
        """Get list of available tools."""
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
        """Call a tool by name with arguments."""
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
                logger.debug(f"Filtering out placeholder account: '{account}' -> using primary account")
                account = None  # Use primary account instead
                
            logger.debug(f"Processed account parameter: '{account}'", extra={"user_id": user_id})
            
            # Get user credentials
            try:
                credentials = await get_user_google_credentials(user_id, account)
            except Exception as e:
                return {"success": False, "error": f"Failed to get Google credentials: {str(e)}", "tool": tool_name}
            
            # Route to appropriate handler
            if tool_name.startswith("gmail_"):
                return await self._handle_gmail_tool(tool_name, credentials, arguments)
            elif tool_name.startswith("drive_"):
                return await self._handle_drive_tool(tool_name, credentials, arguments)
            elif tool_name.startswith("calendar_"):
                return await self._handle_calendar_tool(tool_name, credentials, arguments)
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}", "tool": tool_name}
                
        except Exception as e:
            return {"success": False, "error": f"Tool execution failed: {str(e)}", "tool": tool_name}
    
    async def _handle_gmail_tool(self, name: str, credentials, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Gmail tool calls."""
        try:
            if name == "gmail_search":
                query = arguments.get("query", "")
                max_results = arguments.get("max_results", 10)
                
                result = await google_oauth_service.get_gmail_messages(
                    credentials=credentials, query=query, max_results=max_results
                )
                
                if "error" in result:
                    return {"success": False, "response": f"❌ Gmail search failed: {result['error']}", "tool": name}
                
                messages = result.get("messages", [])
                if not messages:
                    response_text = "📭 No emails found for your search."
                else:
                    response_text = f"📧 **Found {len(messages)} emails:**\n\n"
                    for i, msg in enumerate(messages[:3], 1):  # Limit to 3 for full content
                        sender = msg.get('from', 'Unknown').split('<')[0].strip('"') if '<' in msg.get('from', '') else msg.get('from', 'Unknown')
                        response_text += f"{i}. **{sender}**\n"
                        response_text += f"   📄 {msg.get('subject', 'No Subject')}\n"
                        response_text += f"   📅 {msg.get('date', 'Unknown Date')}\n"
                        
                        # Include full body content for analysis
                        body_content = msg.get('body', msg.get('snippet', ''))
                        if body_content:
                            # Truncate very long emails but keep substantial content for analysis
                            if len(body_content) > 1000:
                                body_content = body_content[:1000] + "... [content truncated]"
                            response_text += f"   📝 **Content:**\n{body_content}\n\n"
                        else:
                            response_text += f"   📝 {msg.get('snippet', '')[:80]}...\n\n"
                    
                    if len(messages) > 3:
                        response_text += f"_...and {len(messages) - 3} more emails (showing first 3 with full content)_"
                
                return {"success": True, "response": response_text, "tool": name}
            
            elif name == "gmail_get_message":
                message_id = arguments.get("message_id")
                
                result = await google_oauth_service.get_gmail_message_content(
                    credentials=credentials, message_id=message_id
                )
                
                if "error" in result:
                    return {"success": False, "response": f"❌ Failed to get message: {result['error']}", "tool": name}
                
                response_text = f"📧 **Gmail Message ({message_id})**\n\n"
                response_text += f"**Snippet:** {result.get('snippet', 'No preview available')}\n\n"
                response_text += f"**Thread ID:** {result.get('threadId', 'N/A')}"
                
                return {"success": True, "response": response_text, "tool": name}
            
            elif name == "gmail_recent":
                max_results = arguments.get("max_results", 10)
                
                result = await google_oauth_service.get_gmail_messages(
                    credentials=credentials, query="newer:2024/01/01", max_results=max_results
                )
                
                if "error" in result:
                    return {"success": False, "response": f"❌ Failed to get recent emails: {result['error']}", "tool": name}
                
                messages = result.get("messages", [])
                if not messages:
                    response_text = "📭 No recent emails found."
                else:
                    response_text = f"📧 **Your {len(messages)} most recent emails:**\n\n"
                    for i, msg in enumerate(messages, 1):
                        sender = msg.get('from', 'Unknown').split('<')[0].strip('"') if '<' in msg.get('from', '') else msg.get('from', 'Unknown')
                        response_text += f"{i}. **{sender}** - {msg.get('subject', 'No Subject')}\n"
                        response_text += f"   _{msg.get('date', 'Unknown Date')}_\n"
                        
                        # Include full body content for analysis
                        body_content = msg.get('body', msg.get('snippet', ''))
                        if body_content:
                            # Truncate very long emails but keep substantial content for analysis
                            if len(body_content) > 800:
                                body_content = body_content[:800] + "... [content truncated]"
                            response_text += f"   📝 **Content:**\n{body_content}\n\n"
                        else:
                            response_text += f"   📝 {msg.get('snippet', '')[:80]}...\n\n"
                
                return {"success": True, "response": response_text, "tool": name}
            
            elif name == "gmail_important":
                max_results = arguments.get("max_results", 10)
                
                result = await google_oauth_service.get_gmail_messages(
                    credentials=credentials, query="is:important OR is:starred OR label:important", max_results=max_results
                )
                
                if "error" in result:
                    return {"success": False, "response": f"❌ Failed to get important emails: {result['error']}", "tool": name}
                
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
                        
                        # Include full body content for analysis
                        body_content = msg.get('body', msg.get('snippet', ''))
                        if body_content:
                            # Truncate very long emails but keep substantial content for analysis
                            if len(body_content) > 800:
                                body_content = body_content[:800] + "... [content truncated]"
                            response_text += f"   📝 **Content:**\n{body_content}\n\n"
                        else:
                            response_text += f"   📄 {msg.get('snippet', '')[:80]}...\n\n"
                
                return {"success": True, "response": response_text, "tool": name}
            
            else:
                return {"success": False, "error": f"Unknown Gmail tool: {name}", "tool": name}
                
        except Exception as e:
            return {"success": False, "error": f"Gmail tool error: {str(e)}", "tool": name}
    
    async def _handle_drive_tool(self, name: str, credentials, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Google Drive tool calls."""
        try:
            if name == "drive_list_files":
                query = arguments.get("query", "")
                max_results = arguments.get("max_results", 10)
                
                result = await google_oauth_service.get_drive_files(
                    credentials=credentials, query=query, max_results=max_results
                )
                
                if "error" in result:
                    return {"success": False, "response": f"❌ Drive list failed: {result['error']}", "tool": name}
                
                files = result.get("files", [])
                if not files:
                    response_text = "📁 No files found in Google Drive."
                else:
                    response_text = f"📁 **Found {len(files)} files in Google Drive:**\n\n"
                    for i, file in enumerate(files, 1):
                        file_name = file.get('name', 'Unknown')
                        file_type = file.get('mimeType', 'Unknown type')
                        
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
                
                return {"success": True, "response": response_text, "tool": name}
            
            elif name == "drive_create_folder":
                folder_path = arguments.get("folder_path")
                root_folder = arguments.get("root_folder", "TURFMAPP")
                
                try:
                    folder_id = await google_oauth_service.create_folder_structure(
                        credentials=credentials, folder_path=folder_path, root_folder=root_folder
                    )
                    
                    response_text = f"📁 **Folder created successfully!**\n\n"
                    response_text += f"**Path:** {root_folder}/{folder_path}\n"
                    response_text += f"**Folder ID:** {folder_id}"
                    
                    return {"success": True, "response": response_text, "tool": name}
                    
                except Exception as e:
                    return {"success": False, "response": f"❌ Failed to create folder: {str(e)}", "tool": name}
            
            elif name == "drive_list_folder_files":
                folder_path = arguments.get("folder_path")
                
                result = await google_oauth_service.list_files_in_folder(
                    credentials=credentials, folder_path=folder_path
                )
                
                if not result.get("success", False):
                    return {"success": False, "response": f"❌ Failed to list folder files: {result.get('error', 'Unknown error')}", "tool": name}
                
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
                
                return {"success": True, "response": response_text, "tool": name}
            
            elif name == "drive_shared_drives":
                max_results = arguments.get("max_results", 10)
                
                result = await google_oauth_service.get_shared_drives(
                    credentials=credentials, max_results=max_results
                )
                
                if "error" in result:
                    return {"success": False, "response": f"❌ Shared drives access failed: {result['error']}", "tool": name}
                
                drives = result.get("drives", [])
                if not drives:
                    response_text = "📁 No shared drives found. You may not have access to any shared drives or team drives."
                else:
                    response_text = f"📁 **Found {len(drives)} shared drive(s):**\n\n"
                    for i, drive in enumerate(drives, 1):
                        drive_name = drive.get('name', 'Unknown')
                        created_time = drive.get('createdTime', 'Unknown')
                        
                        response_text += f"{i}. 📂 **{drive_name}**\n"
                        response_text += f"   📅 Created: {created_time}\n"
                        response_text += f"   🔗 Drive ID: {drive.get('id', 'Unknown')}\n\n"
                
                return {"success": True, "response": response_text, "tool": name}
            
            elif name == "drive_search":
                search_term = arguments.get("search_term", "")
                file_type = arguments.get("file_type", "")
                year = arguments.get("year", "")
                max_results = arguments.get("max_results", 10)
                
                result = await google_oauth_service.search_drive_files(
                    credentials=credentials,
                    search_term=search_term,
                    file_type=file_type,
                    year=year,
                    max_results=max_results
                )
                
                if "error" in result:
                    return {"success": False, "response": f"❌ Drive search failed: {result['error']}", "tool": name}
                
                files = result.get("files", [])
                if not files:
                    search_desc = []
                    if search_term:
                        search_desc.append(f"'{search_term}'")
                    if file_type:
                        search_desc.append(f"type '{file_type}'")
                    if year:
                        search_desc.append(f"from {year}")
                    
                    response_text = f"📁 No files found" + (f" matching {' '.join(search_desc)}" if search_desc else "") + "."
                else:
                    search_desc = []
                    if search_term:
                        search_desc.append(f"'{search_term}'")
                    if file_type:
                        search_desc.append(f"type '{file_type}'")
                    if year:
                        search_desc.append(f"from {year}")
                    
                    response_text = f"🔍 **Found {len(files)} file(s)" + (f" matching {' '.join(search_desc)}" if search_desc else "") + ":**\n\n"
                    
                    for i, file in enumerate(files, 1):
                        file_name = file.get('name', 'Unknown')
                        file_type_mime = file.get('mimeType', '')
                        modified_time = file.get('modifiedTime', 'Unknown')
                        web_view_link = file.get('webViewLink', '')
                        web_content_link = file.get('webContentLink', '')
                        thumbnail_link = file.get('thumbnailLink', '')
                        
                        # File type icon
                        if 'image' in file_type_mime:
                            icon = "🖼️"
                        elif 'video' in file_type_mime:
                            icon = "🎥"
                        elif 'document' in file_type_mime or 'pdf' in file_type_mime:
                            icon = "📄"
                        elif 'spreadsheet' in file_type_mime:
                            icon = "📊"
                        elif 'presentation' in file_type_mime:
                            icon = "📽️"
                        elif 'folder' in file_type_mime:
                            icon = "📁"
                        else:
                            icon = "📄"
                        
                        response_text += f"{i}. {icon} **{file_name}**\n"
                        response_text += f"   📅 Modified: {modified_time}\n"
                        
                        # Add links
                        if web_view_link:
                            response_text += f"   🔗 [View]({web_view_link})\n"
                        if web_content_link:
                            response_text += f"   ⬇️ [Download]({web_content_link})\n"
                        if thumbnail_link and 'image' in file_type_mime:
                            response_text += f"   🖼️ [Thumbnail]({thumbnail_link})\n"
                        
                        response_text += "\n"
                
                return {"success": True, "response": response_text, "tool": name}
            
            elif name == "drive_search_folders":
                folder_name = arguments.get("folder_name", "")
                max_results = arguments.get("max_results", 10)
                
                result = await google_oauth_service.search_drive_folders(
                    credentials=credentials,
                    folder_name=folder_name,
                    max_results=max_results
                )
                
                if "error" in result:
                    return {"success": False, "response": f"❌ Folder search failed: {result['error']}", "tool": name}
                
                folders = result.get("folders", [])
                if not folders:
                    response_text = f"I couldn't find any folders with the name '{folder_name}' in your Google Drive."
                else:
                    # User-friendly response format
                    folder = folders[0]  # Get the first folder
                    folder_name_result = folder.get('name', 'Unknown')
                    web_view_link = folder.get('webViewLink', '')
                    folder_id = folder.get('id', '')
                    
                    # Debug logging
                    logger.debug(f"Folder debug - ID: {folder_id}, webViewLink: {web_view_link}")
                    
                    if web_view_link:
                        response_text = f"Here's the link to the folder **\"{folder_name_result}\"**:\n\n"
                        response_text += f"🔗 <a href=\"{web_view_link}\" target=\"_blank\"><b>Open {folder_name_result}</b></a>\n\n"
                        response_text += f"**Direct URL:** {web_view_link}\n\n"
                        response_text += "You can click the link above or copy the URL to access your folder directly."
                    else:
                        # Fallback: construct the link manually from folder ID
                        if folder_id:
                            manual_link = f"https://drive.google.com/drive/folders/{folder_id}"
                            response_text = f"Here's the link to the folder **\"{folder_name_result}\"**:\n\n"
                            response_text += f"🔗 <a href=\"{manual_link}\" target=\"_blank\"><b>Open {folder_name_result}</b></a>\n\n"
                            response_text += f"**Direct URL:** {manual_link}\n\n"
                            response_text += "You can click the link above or copy the URL to access your folder directly."
                        else:
                            response_text = f"Found the folder **\"{folder_name_result}\"** but couldn't generate a direct link."
                
                return {"success": True, "response": response_text, "tool": name}
            
            else:
                return {"success": False, "error": f"Unknown Drive tool: {name}", "tool": name}
                
        except Exception as e:
            return {"success": False, "error": f"Drive tool error: {str(e)}", "tool": name}
    
    async def _handle_calendar_tool(self, name: str, credentials, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Google Calendar tool calls."""
        try:
            logger.info(f"Handling calendar tool '{name}'", extra={"arguments": arguments})
            if name == "calendar_list_events":
                calendar_id = arguments.get("calendar_id", "primary")
                max_results = arguments.get("max_results", 10)
                
                # Default to upcoming events unless specifically requested otherwise
                result = await google_oauth_service.get_calendar_events(
                    credentials=credentials, calendar_id=calendar_id, max_results=max_results, upcoming_only=True
                )
                
                if "error" in result:
                    return {"success": False, "response": f"❌ Calendar access failed: {result['error']}", "tool": name}
                
                events = result.get("events", [])
                if not events:
                    response_text = "📅 No calendar events found."
                else:
                    response_text = f"📅 **Found {len(events)} calendar events:**\n\n"
                    for i, event in enumerate(events, 1):
                        title = event.get('summary', 'No Title')
                        start_time = event.get('start', {})
                        
                        # Format time
                        start_date = start_time.get('dateTime', start_time.get('date', 'Unknown time'))
                        
                        response_text += f"{i}. **{title}**\n"
                        response_text += f"   🕐 Start: {start_date}\n"
                        
                        if event.get('location'):
                            response_text += f"   📍 Location: {event['location']}\n"
                        
                        response_text += "\n"
                
                return {"success": True, "response": response_text, "tool": name}
            
            elif name == "calendar_upcoming_events":
                days = arguments.get("days", 7)
                logger.debug(f"Getting upcoming calendar events for {days} days")
                
                # Get only upcoming events (future events from now)
                result = await google_oauth_service.get_calendar_events(
                    credentials=credentials, calendar_id="primary", max_results=10, upcoming_only=True
                )
                
                logger.debug(f"Calendar API result: {result}")
                
                if "error" in result:
                    logger.error(f"Calendar API error: {result['error']}")
                    return {"success": False, "response": f"❌ Failed to get upcoming events: {result['error']}", "tool": name}
                
                events = result.get("events", [])
                logger.info(f"Found {len(events)} calendar events")
                
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
                
                logger.debug(f"Returning calendar response: {response_text[:100]}...")
                return {"success": True, "response": response_text, "tool": name}
            
            else:
                return {"success": False, "error": f"Unknown Calendar tool: {name}", "tool": name}
                
        except Exception as e:
            logger.error(f"Calendar tool exception: {str(e)}", exc_info=True)
            import traceback
            # Traceback already included with exc_info=True above
            return {"success": False, "error": f"Calendar tool error: {str(e)}", "tool": name}
    
    async def get_available_tools_for_openai(self) -> List[Dict[str, Any]]:
        """Get tools formatted for OpenAI function calling."""
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
        """Execute a Google service tool with simplified interface."""
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
    """Get the global MCP client instance, ensuring it's connected."""
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
    """Get all available Google tools in raw MCP format."""
    client = await get_mcp_client()
    return await client.list_tools()
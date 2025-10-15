"""
Google Drive tool handlers for MCP client.

This module handles Google Drive-specific tool operations including file listing,
folder creation, searching, and accessing shared drives. Formats results with
file metadata, icons, and web links.
"""

from __future__ import annotations

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


async def handle_drive_tool(name: str, credentials, arguments: Dict[str, Any], google_oauth_service) -> Dict[str, Any]:
    """Handle Google Drive tool calls by routing to appropriate Drive service methods.

    Processes Google Drive-related tool requests including file listing, folder creation,
    searching, and accessing shared drives. Formats results with file metadata, icons,
    and web links for user-friendly display.

    Args:
        name (str): The name of the Drive tool to execute. Supported values are:
            - "drive_list_files": List files in Google Drive
            - "drive_create_folder": Create folder structure in Drive
            - "drive_list_folder_files": List files in a specific folder
            - "drive_shared_drives": List shared/team drives
            - "drive_search": Advanced search with filters for content, type, and year
            - "drive_search_folders": Search specifically for folders by name
        credentials: Google OAuth credentials object for authenticating API calls.
        arguments (Dict[str, Any]): Tool-specific arguments which may include:
            - query (str, optional): Search query for drive_list_files
            - max_results (int, optional): Maximum number of results to return
            - folder_path (str): Required for drive_create_folder and drive_list_folder_files
            - root_folder (str, optional): Root folder name for folder creation
            - search_term (str, optional): Search term for drive_search
            - file_type (str, optional): File type filter for drive_search
            - year (str, optional): Year filter for drive_search
            - folder_name (str): Required for drive_search_folders
        google_oauth_service: The Google OAuth service instance for making API calls.

    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): Whether the operation succeeded
            - response (str): Formatted response text with file/folder details
            - tool (str): The name of the tool that was executed
            - error (str, optional): Error message if success is False

    Raises:
        Exception: Caught internally and returned as error in response dict.
    """
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

                response_text = "📁 **Folder created successfully!**\n\n"
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

                response_text = "📁 No files found" + (f" matching {' '.join(search_desc)}" if search_desc else "") + "."
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
                logger.debug(f"🔍 Folder debug - ID: {folder_id}, webViewLink: {web_view_link}")

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

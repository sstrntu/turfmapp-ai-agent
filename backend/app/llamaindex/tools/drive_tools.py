"""
Google Drive Tools using LlamaIndex FunctionTool

Provides Google Drive operations (search files, list files, upload, etc.)
as LlamaIndex FunctionTools for file management tasks.
"""

from __future__ import annotations

import logging
from typing import List

from llama_index.core.tools import FunctionTool
from google.oauth2.credentials import Credentials

from ...services.google_drive_ops import (
    search_drive_files,
    search_drive_folders,
    get_drive_files,
    get_shared_drives,
)

logger = logging.getLogger(__name__)


def search_files(
    credentials: Credentials,
    search_term: str = "",
    file_type: str = "",
    year: str = "",
    max_results: int = 10
) -> str:
    """
    Search for files in Google Drive with advanced filters.

    Args:
        credentials: Google OAuth2 credentials
        search_term: Text to search for in file names or content
        file_type: Type of file to filter by. Options:
            - "photo", "photos", "image", "images" - Image files
            - "document", "doc", "docs" - Documents and PDFs
            - "video", "videos" - Video files
            - "folder", "folders" - Folders only
            - Any MIME type string
        year: Filter files by modification year (e.g., "2024", "2025")
        max_results: Maximum number of results to return (default: 10)

    Returns:
        str: Formatted string with file details or error message

    Example:
        >>> search_files(creds, "budget", "document", "2024", 5)
        "Found 3 files:

         File 1:
         Name: Q4 Budget Report.pdf
         ID: 1abc2def3ghi...
         Type: application/pdf
         Size: 2.5 MB
         Modified: 2024-12-15
         Link: https://drive.google.com/..."
    """
    import asyncio

    result = asyncio.run(search_drive_files(
        credentials=credentials,
        search_term=search_term,
        file_type=file_type,
        year=year,
        max_results=min(max_results, 50)
    ))

    if "error" in result:
        return f"Error searching Drive: {result['error']}"

    files = result.get("files", [])

    if not files:
        filters = []
        if search_term:
            filters.append(f"search term: '{search_term}'")
        if file_type:
            filters.append(f"type: '{file_type}'")
        if year:
            filters.append(f"year: {year}")
        filter_str = ", ".join(filters) if filters else "no filters"
        return f"No files found matching {filter_str}"

    output_lines = [f"Found {len(files)} files:\n"]

    for i, file in enumerate(files, 1):
        output_lines.append(f"File {i}:")
        output_lines.append(f"  Name: {file.get('name', 'N/A')}")
        output_lines.append(f"  ID: {file.get('id', 'N/A')}")
        output_lines.append(f"  Type: {file.get('mimeType', 'N/A')}")

        # Format file size
        size = file.get('size')
        if size:
            size_mb = int(size) / (1024 * 1024)
            output_lines.append(f"  Size: {size_mb:.2f} MB")

        output_lines.append(f"  Modified: {file.get('modifiedTime', 'N/A')}")
        output_lines.append(f"  Link: {file.get('webViewLink', 'N/A')}")
        output_lines.append("")

    return "\n".join(output_lines)


def search_folders(
    credentials: Credentials,
    folder_name: str,
    max_results: int = 10
) -> str:
    """
    Search for folders in Google Drive by name.

    Args:
        credentials: Google OAuth2 credentials
        folder_name: Name or partial name of folder to search for
        max_results: Maximum number of results to return (default: 10)

    Returns:
        str: Formatted string with folder details or error message

    Example:
        >>> search_folders(creds, "Projects", 5)
        "Found 2 folders:

         Folder 1:
         Name: Projects 2024
         ID: 1xyz2abc3def...
         Modified: 2024-12-20
         Link: https://drive.google.com/..."
    """
    import asyncio

    result = asyncio.run(search_drive_folders(
        credentials=credentials,
        folder_name=folder_name,
        max_results=min(max_results, 50)
    ))

    if "error" in result:
        return f"Error searching folders: {result['error']}"

    folders = result.get("folders", [])

    if not folders:
        return f"No folders found matching '{folder_name}'"

    output_lines = [f"Found {len(folders)} folders:\n"]

    for i, folder in enumerate(folders, 1):
        output_lines.append(f"Folder {i}:")
        output_lines.append(f"  Name: {folder.get('name', 'N/A')}")
        output_lines.append(f"  ID: {folder.get('id', 'N/A')}")
        output_lines.append(f"  Created: {folder.get('createdTime', 'N/A')}")
        output_lines.append(f"  Modified: {folder.get('modifiedTime', 'N/A')}")
        output_lines.append(f"  Link: {folder.get('webViewLink', 'N/A')}")
        output_lines.append("")

    return "\n".join(output_lines)


def list_recent_files(
    credentials: Credentials,
    max_results: int = 10
) -> str:
    """
    List recent files from Google Drive.

    Args:
        credentials: Google OAuth2 credentials
        max_results: Maximum number of files to return (default: 10)

    Returns:
        str: Formatted string with file details or error message

    Example:
        >>> list_recent_files(creds, 5)
        "Recent files (5 total):

         File 1:
         Name: Meeting Notes.docx
         Type: application/vnd.google-apps.document
         Modified: 2025-01-20
         Link: https://drive.google.com/..."
    """
    import asyncio

    result = asyncio.run(get_drive_files(
        credentials=credentials,
        query="",  # Empty query gets recent files
        max_results=min(max_results, 50)
    ))

    if "error" in result:
        return f"Error listing files: {result['error']}"

    files = result.get("files", [])

    if not files:
        return "No files found in Drive"

    output_lines = [f"Recent files ({len(files)} total):\n"]

    for i, file in enumerate(files, 1):
        output_lines.append(f"File {i}:")
        output_lines.append(f"  Name: {file.get('name', 'N/A')}")
        output_lines.append(f"  ID: {file.get('id', 'N/A')}")
        output_lines.append(f"  Type: {file.get('mimeType', 'N/A')}")
        output_lines.append(f"  Modified: {file.get('modifiedTime', 'N/A')}")
        output_lines.append(f"  Link: {file.get('webViewLink', 'N/A')}")
        output_lines.append("")

    return "\n".join(output_lines)


def list_shared_drives(
    credentials: Credentials,
    max_results: int = 10
) -> str:
    """
    List shared drives (Team Drives) the user has access to.

    Args:
        credentials: Google OAuth2 credentials
        max_results: Maximum number of drives to return (default: 10)

    Returns:
        str: Formatted string with shared drive details or error message

    Example:
        >>> list_shared_drives(creds)
        "Shared Drives (2 total):

         Drive 1:
         Name: Marketing Team
         ID: 0ABcd123...
         Created: 2024-01-15"
    """
    import asyncio

    result = asyncio.run(get_shared_drives(
        credentials=credentials,
        max_results=min(max_results, 50)
    ))

    if "error" in result:
        return f"Error listing shared drives: {result['error']}"

    drives = result.get("drives", [])

    if not drives:
        return "No shared drives found"

    output_lines = [f"Shared Drives ({len(drives)} total):\n"]

    for i, drive in enumerate(drives, 1):
        output_lines.append(f"Drive {i}:")
        output_lines.append(f"  Name: {drive.get('name', 'N/A')}")
        output_lines.append(f"  ID: {drive.get('id', 'N/A')}")
        output_lines.append(f"  Created: {drive.get('createdTime', 'N/A')}")

        capabilities = drive.get('capabilities', {})
        if capabilities:
            output_lines.append("  Capabilities:")
            if capabilities.get('canAddChildren'):
                output_lines.append("    - Can add files")
            if capabilities.get('canManageMembers'):
                output_lines.append("    - Can manage members")

        output_lines.append("")

    return "\n".join(output_lines)


def create_drive_tools(credentials: Credentials) -> List[FunctionTool]:
    """
    Create LlamaIndex FunctionTools for Google Drive operations.

    Args:
        credentials: Google OAuth2 credentials for the user

    Returns:
        List of FunctionTool instances for Drive operations
    """
    # Create partially applied functions with credentials
    def search_files_tool(
        search_term: str = "",
        file_type: str = "",
        year: str = "",
        max_results: int = 10
    ) -> str:
        """Search Drive files with filters. Use search_term for keywords, file_type for file types (photo/document/video/folder), year for filtering by year."""
        return search_files(credentials, search_term, file_type, year, max_results)

    def search_folders_tool(folder_name: str, max_results: int = 10) -> str:
        """Search for folders in Drive by name."""
        return search_folders(credentials, folder_name, max_results)

    def list_recent_tool(max_results: int = 10) -> str:
        """List recent files from Drive."""
        return list_recent_files(credentials, max_results)

    def list_drives_tool(max_results: int = 10) -> str:
        """List shared drives (Team Drives) the user has access to."""
        return list_shared_drives(credentials, max_results)

    # Create FunctionTools
    tools = [
        FunctionTool.from_defaults(
            fn=search_files_tool,
            name="search_drive_files",
            description=(
                "Search Google Drive files with advanced filters. "
                "Parameters: search_term (text to find), file_type (photo/document/video/folder), "
                "year (filter by modification year), max_results (limit). "
                "Returns file names, IDs, types, sizes, and links. "
                "Use this to find specific files in Drive."
            ),
        ),
        FunctionTool.from_defaults(
            fn=search_folders_tool,
            name="search_drive_folders",
            description=(
                "Search for folders in Google Drive by name. "
                "Returns folder names, IDs, creation/modification dates, and links. "
                "Use this to find specific folders in Drive."
            ),
        ),
        FunctionTool.from_defaults(
            fn=list_recent_tool,
            name="list_recent_drive_files",
            description=(
                "List recent files from Google Drive. "
                "Returns recently modified files with names, types, and links. "
                "Use this to see what files were recently accessed or modified."
            ),
        ),
        FunctionTool.from_defaults(
            fn=list_drives_tool,
            name="list_shared_drives",
            description=(
                "List shared drives (Team Drives) the user has access to. "
                "Returns drive names, IDs, and capabilities. "
                "Use this to see available team drives and shared spaces."
            ),
        ),
    ]

    logger.info(f"Created {len(tools)} Drive tools")
    return tools

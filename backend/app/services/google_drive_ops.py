"""
Google Drive Operations

This module handles Google Drive API operations including file operations,
folder management, search, and shared drives access.

Extracted from google_oauth.py (Phase 3 - January 2025)
"""

from __future__ import annotations

import io
import logging
from typing import Dict, Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

logger = logging.getLogger(__name__)


async def get_drive_files(credentials: Credentials, query: str = '', max_results: int = 10, refresh_func=None) -> Dict[str, Any]:
    """Retrieve Google Drive files matching the specified query."""
    try:
        if refresh_func:
            credentials = refresh_func(credentials)
        service = build('drive', 'v3', credentials=credentials)

        results = service.files().list(
            q=query,
            pageSize=max_results,
            fields="nextPageToken, files(id, name, mimeType, createdTime, modifiedTime, size, webViewLink, webContentLink, thumbnailLink)"
        ).execute()

        return {
            'files': results.get('files', []),
            'nextPageToken': results.get('nextPageToken')
        }

    except HttpError as e:
        logger.error(f"Error getting Drive files: {e}")
        return {'error': str(e), 'files': []}


async def search_drive_files(credentials: Credentials, search_term: str = '', file_type: str = '',
                            year: str = '', max_results: int = 10, refresh_func=None) -> Dict[str, Any]:
    """Perform advanced search on Google Drive with content, type, and date filters."""
    try:
        if refresh_func:
            credentials = refresh_func(credentials)
        service = build('drive', 'v3', credentials=credentials)

        # Build search query
        query_parts = []

        # Content/name search
        if search_term:
            query_parts.append(f"(fullText contains '{search_term}' OR name contains '{search_term}')")

        # File type filter
        if file_type:
            if file_type.lower() in ['photo', 'photos', 'image', 'images']:
                query_parts.append("mimeType contains 'image/'")
            elif file_type.lower() in ['document', 'doc', 'docs']:
                query_parts.append("(mimeType contains 'document' OR mimeType contains 'pdf')")
            elif file_type.lower() in ['video', 'videos']:
                query_parts.append("mimeType contains 'video/'")
            elif file_type.lower() in ['folder', 'folders']:
                query_parts.append("mimeType = 'application/vnd.google-apps.folder'")
            else:
                query_parts.append(f"mimeType contains '{file_type}'")

        # Year filter
        if year:
            start_date = f"{year}-01-01T00:00:00"
            end_date = f"{int(year)+1}-01-01T00:00:00"
            query_parts.append(f"modifiedTime >= '{start_date}' AND modifiedTime < '{end_date}'")

        # Exclude trashed files
        query_parts.append("trashed=false")

        # Combine query parts
        query = " AND ".join(query_parts) if query_parts else "trashed=false"

        logger.debug(f"🔍 Drive search query: {query}")

        results = service.files().list(
            q=query,
            pageSize=max_results,
            fields="nextPageToken, files(id, name, mimeType, createdTime, modifiedTime, size, webViewLink, webContentLink, thumbnailLink, parents)",
            orderBy="modifiedTime desc"
        ).execute()

        return {
            'files': results.get('files', []),
            'nextPageToken': results.get('nextPageToken'),
            'query': query
        }

    except HttpError as e:
        logger.error(f"Error searching Drive files: {e}")
        return {'error': str(e), 'files': []}


async def search_drive_folders(credentials: Credentials, folder_name: str, max_results: int = 10, refresh_func=None) -> Dict[str, Any]:
    """Search for folders in Google Drive by name."""
    try:
        if refresh_func:
            credentials = refresh_func(credentials)
        service = build('drive', 'v3', credentials=credentials)

        # Search for folders with the specified name
        query = f"name contains '{folder_name}' AND mimeType = 'application/vnd.google-apps.folder' AND trashed=false"

        logger.debug(f"🔍 Drive folder search query: {query}")

        results = service.files().list(
            q=query,
            pageSize=max_results,
            fields="nextPageToken, files(id, name, mimeType, createdTime, modifiedTime, webViewLink, parents)",
            orderBy="modifiedTime desc"
        ).execute()

        return {
            'folders': results.get('files', []),
            'nextPageToken': results.get('nextPageToken'),
            'query': query
        }

    except HttpError as e:
        logger.error(f"Error searching Drive folders: {e}")
        return {'error': str(e), 'folders': []}


async def create_folder_structure(credentials: Credentials, folder_path: str, root_folder: str = "TURFMAPP", refresh_func=None) -> str:
    """Create nested folder hierarchy in Google Drive."""
    try:
        if refresh_func:
            credentials = refresh_func(credentials)
        service = build('drive', 'v3', credentials=credentials)

        # Split path and add root folder
        path_parts = [root_folder] + [part.strip() for part in folder_path.split('/') if part.strip()]

        current_parent = None
        for folder_name in path_parts:
            folder_id = await get_or_create_folder(service, folder_name, current_parent)
            current_parent = folder_id

        return current_parent

    except Exception as e:
        logger.error(f"Error creating folder structure: {e}")
        raise


async def get_or_create_folder(service, folder_name: str, parent_id: str = None) -> str:
    """Find an existing folder by name and parent, or create it if not found."""
    try:
        # Search for existing folder
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"

        results = service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get('files', [])

        if files:
            return files[0]['id']

        # Create new folder
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            folder_metadata['parents'] = [parent_id]

        folder = service.files().create(body=folder_metadata, fields='id').execute()
        return folder.get('id')

    except Exception as e:
        logger.error(f"Error getting/creating folder '{folder_name}': {e}")
        raise


async def upload_file_to_drive(credentials: Credentials, file_content: bytes, filename: str,
                              folder_path: str = None, refresh_func=None, create_folder_func=None) -> Dict[str, Any]:
    """Upload file to specific folder in user's Drive."""
    try:
        if refresh_func:
            credentials = refresh_func(credentials)
        service = build('drive', 'v3', credentials=credentials)

        # Create folder structure if specified
        parent_folder_id = None
        if folder_path and create_folder_func:
            parent_folder_id = await create_folder_func(credentials, folder_path)

        # Check for existing file
        query = f"name='{filename}' and trashed=false"
        if parent_folder_id:
            query += f" and '{parent_folder_id}' in parents"

        results = service.files().list(q=query, fields="files(id, name)").execute()
        existing_files = results.get('files', [])

        file_metadata = {'name': filename}
        if parent_folder_id:
            file_metadata['parents'] = [parent_folder_id]

        media = MediaIoBaseUpload(
            io.BytesIO(file_content),
            mimetype='application/octet-stream',
            resumable=True
        )

        if existing_files:
            # Update existing file
            file_result = service.files().update(
                fileId=existing_files[0]['id'],
                body={'name': filename},
                media_body=media,
                fields='id,name,webViewLink,size,createdTime,modifiedTime'
            ).execute()
            action = "updated"
        else:
            # Create new file
            file_result = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,webViewLink,size,createdTime,modifiedTime'
            ).execute()
            action = "created"

        return {
            'success': True,
            'action': action,
            'file': file_result,
            'folder_path': folder_path
        }

    except Exception as e:
        logger.error(f"Error uploading file '{filename}': {e}")
        return {'success': False, 'error': str(e)}


async def delete_file_from_drive(credentials: Credentials, file_id: str, refresh_func=None) -> Dict[str, Any]:
    """Delete file from user's Drive."""
    try:
        if refresh_func:
            credentials = refresh_func(credentials)
        service = build('drive', 'v3', credentials=credentials)

        # Get file info before deletion
        file_info = service.files().get(fileId=file_id, fields='id,name').execute()

        # Delete file
        service.files().delete(fileId=file_id).execute()

        return {
            'success': True,
            'message': f"File '{file_info.get('name', 'Unknown')}' deleted successfully",
            'file_id': file_id
        }

    except Exception as e:
        logger.error(f"Error deleting file '{file_id}': {e}")
        return {'success': False, 'error': str(e)}


async def list_files_in_folder(credentials: Credentials, folder_path: str, refresh_func=None, create_folder_func=None) -> Dict[str, Any]:
    """List all files in a specific folder path."""
    try:
        if refresh_func:
            credentials = refresh_func(credentials)
        service = build('drive', 'v3', credentials=credentials)

        # Find folder by path
        if create_folder_func:
            folder_id = await create_folder_func(credentials, folder_path)
        else:
            raise ValueError("create_folder_func required")

        # List files in folder
        query = f"'{folder_id}' in parents and trashed=false"
        results = service.files().list(
            q=query,
            fields="files(id,name,size,createdTime,modifiedTime,webViewLink,mimeType)",
            orderBy="name"
        ).execute()

        return {
            'success': True,
            'files': results.get('files', []),
            'folder_path': folder_path
        }

    except Exception as e:
        logger.error(f"Error listing files in '{folder_path}': {e}")
        return {'success': False, 'error': str(e), 'files': []}


async def get_shared_drives(credentials: Credentials, max_results: int = 10, refresh_func=None) -> Dict[str, Any]:
    """Get shared drives (Team Drives) that the user has access to."""
    try:
        if refresh_func:
            credentials = refresh_func(credentials)
        service = build('drive', 'v3', credentials=credentials)

        # List shared drives
        results = service.drives().list(
            pageSize=max_results,
            fields="nextPageToken, drives(id, name, createdTime, capabilities, restrictions)"
        ).execute()

        return {
            'drives': results.get('drives', []),
            'nextPageToken': results.get('nextPageToken')
        }

    except HttpError as e:
        logger.error(f"Error getting shared drives: {e}")
        return {'error': str(e), 'drives': []}

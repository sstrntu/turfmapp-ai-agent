"""
Google OAuth Service - Main entry point for Google API integrations

Refactored (Phase 3 - January 2025):
- Core OAuth operations extracted to google_oauth_core.py
- Gmail operations extracted to google_gmail_ops.py
- Drive operations extracted to google_drive_ops.py
- Calendar operations extracted to google_calendar_ops.py

This file now acts as a facade providing backward compatibility.
"""

from __future__ import annotations

from typing import Optional, Dict, Any
from pydantic import BaseModel

from google.oauth2.credentials import Credentials

from .google_oauth_core import GoogleOAuthCore
from .google_gmail_ops import (
    get_gmail_messages as _get_gmail_messages,
    get_gmail_message_content as _get_gmail_message_content,
    extract_email_body as _extract_email_body,
)
from .google_drive_ops import (
    get_drive_files as _get_drive_files,
    search_drive_files as _search_drive_files,
    search_drive_folders as _search_drive_folders,
    create_folder_structure as _create_folder_structure,
    upload_file_to_drive as _upload_file_to_drive,
    delete_file_from_drive as _delete_file_from_drive,
    list_files_in_folder as _list_files_in_folder,
    get_shared_drives as _get_shared_drives,
)
from .google_calendar_ops import get_calendar_events as _get_calendar_events


class GoogleTokens(BaseModel):
    """Model for storing Google OAuth tokens."""

    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[float] = None


class GoogleAccount(BaseModel):
    """Model for storing Google account information."""

    email: str
    name: str
    picture: Optional[str] = None
    tokens: GoogleTokens
    nickname: Optional[str] = None
    is_primary: bool = False
    connected_at: float


class GoogleOAuthService:
    """Google OAuth and API service for Gmail, Drive, and Calendar integration."""

    def __init__(self):
        self._core = GoogleOAuthCore()
        # Expose core attributes for backward compatibility
        self.client_id = self._core.client_id
        self.client_secret = self._core.client_secret
        self.redirect_uri = self._core.redirect_uri
        self.scopes = self._core.scopes

    def _ensure_configured(self):
        """Ensure Google OAuth is properly configured."""
        return self._core._ensure_configured()

    def get_authorization_url(self, state: str = None) -> str:
        """Generate Google OAuth authorization URL with refresh token support."""
        return self._core.get_authorization_url(state)

    async def exchange_code_for_tokens(
        self, authorization_code: str, state: str = None
    ) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for access and refresh tokens."""
        return await self._core.exchange_code_for_tokens(authorization_code, state)

    async def _get_user_info(self, credentials: Credentials) -> Dict[str, Any]:
        """Get user information from Google."""
        return await self._core._get_user_info(credentials)

    def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Refresh access token using refresh token."""
        return self._core.refresh_access_token(refresh_token)

    def get_credentials_from_token(
        self, access_token: str, refresh_token: str = None
    ) -> Credentials:
        """Create Google credentials object from tokens."""
        return self._core.get_credentials_from_token(access_token, refresh_token)

    def refresh_credentials_if_needed(self, credentials: Credentials) -> Credentials:
        """Auto-refresh expired credentials."""
        return self._core.refresh_credentials_if_needed(credentials)

    # Gmail API methods
    async def get_gmail_messages(
        self, credentials: Credentials, query: str = "", max_results: int = 10
    ) -> Dict[str, Any]:
        """Retrieve Gmail messages with full content for the authenticated user."""
        return await _get_gmail_messages(credentials, query, max_results)

    def _extract_email_body(self, payload: Dict[str, Any]) -> str:
        """Extract and decode email body content from Gmail API payload."""
        return _extract_email_body(payload)

    async def get_gmail_message_content(
        self, credentials: Credentials, message_id: str
    ) -> Dict[str, Any]:
        """Retrieve the full content and metadata of a specific Gmail message."""
        return await _get_gmail_message_content(credentials, message_id)

    # Drive API methods
    async def get_drive_files(
        self, credentials: Credentials, query: str = "", max_results: int = 10
    ) -> Dict[str, Any]:
        """Retrieve Google Drive files matching the specified query."""
        return await _get_drive_files(
            credentials, query, max_results, self.refresh_credentials_if_needed
        )

    async def search_drive_files(
        self,
        credentials: Credentials,
        search_term: str = "",
        file_type: str = "",
        year: str = "",
        max_results: int = 10,
    ) -> Dict[str, Any]:
        """Perform advanced search on Google Drive with content, type, and date filters."""
        return await _search_drive_files(
            credentials,
            search_term,
            file_type,
            year,
            max_results,
            self.refresh_credentials_if_needed,
        )

    async def search_drive_folders(
        self, credentials: Credentials, folder_name: str, max_results: int = 10
    ) -> Dict[str, Any]:
        """Search for folders in Google Drive by name."""
        return await _search_drive_folders(
            credentials, folder_name, max_results, self.refresh_credentials_if_needed
        )

    async def create_folder_structure(
        self, credentials: Credentials, folder_path: str, root_folder: str = "TURFMAPP"
    ) -> str:
        """Create nested folder hierarchy in Google Drive."""
        return await _create_folder_structure(
            credentials, folder_path, root_folder, self.refresh_credentials_if_needed
        )

    async def _get_or_create_folder(
        self, service, folder_name: str, parent_id: str = None
    ) -> str:
        """Find an existing folder by name and parent, or create it if not found."""
        from .google_drive_ops import get_or_create_folder

        return await get_or_create_folder(service, folder_name, parent_id)

    async def upload_file_to_drive(
        self,
        credentials: Credentials,
        file_content: bytes,
        filename: str,
        folder_path: str = None,
    ) -> Dict[str, Any]:
        """Upload file to specific folder in user's Drive."""
        return await _upload_file_to_drive(
            credentials,
            file_content,
            filename,
            folder_path,
            self.refresh_credentials_if_needed,
            self.create_folder_structure,
        )

    async def delete_file_from_drive(
        self, credentials: Credentials, file_id: str
    ) -> Dict[str, Any]:
        """Delete file from user's Drive."""
        return await _delete_file_from_drive(
            credentials, file_id, self.refresh_credentials_if_needed
        )

    async def list_files_in_folder(
        self, credentials: Credentials, folder_path: str
    ) -> Dict[str, Any]:
        """List all files in a specific folder path."""
        return await _list_files_in_folder(
            credentials,
            folder_path,
            self.refresh_credentials_if_needed,
            self.create_folder_structure,
        )

    async def get_shared_drives(
        self, credentials: Credentials, max_results: int = 10
    ) -> Dict[str, Any]:
        """Get shared drives (Team Drives) that the user has access to."""
        return await _get_shared_drives(
            credentials, max_results, self.refresh_credentials_if_needed
        )

    # Calendar API methods
    async def get_calendar_events(
        self,
        credentials: Credentials,
        calendar_id: str = "primary",
        max_results: int = 10,
        upcoming_only: bool = True,
    ) -> Dict[str, Any]:
        """Get Google Calendar events for the authenticated user."""
        return await _get_calendar_events(
            credentials, calendar_id, max_results, upcoming_only
        )


# Global instance
google_oauth_service = GoogleOAuthService()

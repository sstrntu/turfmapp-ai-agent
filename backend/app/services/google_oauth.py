from __future__ import annotations

import io
import json
import logging
import os
from typing import Optional, Dict, Any
from pydantic import BaseModel

import httpx
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

from ..models.auth import PublicUser

logger = logging.getLogger(__name__)


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
    nickname: Optional[str] = None  # User-defined label like "Work", "Personal"
    is_primary: bool = False
    connected_at: float


class GoogleOAuthService:
    """Google OAuth and API service for Gmail, Drive, and Calendar integration."""
    
    def __init__(self):
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/auth/callback")
        
        # Required scopes for Gmail, Drive, and Calendar (match Google's actual response)
        self.scopes = [
            'openid',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile', 
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/drive.readonly', 
            'https://www.googleapis.com/auth/calendar.readonly'
        ]
    
    def _ensure_configured(self):
        """Ensure Google OAuth is properly configured."""
        if not self.client_id or not self.client_secret:
            raise ValueError("Google OAuth credentials not configured")
    
    def get_authorization_url(self, state: str = None) -> str:
        """Generate Google OAuth authorization URL with refresh token support."""
        self._ensure_configured()
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri]
                }
            },
            scopes=self.scopes
        )
        flow.redirect_uri = self.redirect_uri

        authorization_url, _ = flow.authorization_url(
            access_type='offline',        # Critical for refresh tokens!
            include_granted_scopes='true',
            prompt='select_account consent',  # Force account selection AND consent for re-auth
            state=state
        )

        return authorization_url
    
    async def exchange_code_for_tokens(self, authorization_code: str, state: str = None) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for access and refresh tokens."""
        self._ensure_configured()
        try:
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [self.redirect_uri]
                    }
                },
                scopes=self.scopes,
                state=state
            )
            flow.redirect_uri = self.redirect_uri
            
            # Exchange code for tokens
            flow.fetch_token(code=authorization_code)

            # Get user info
            credentials = flow.credentials
            user_info = await self._get_user_info(credentials)

            # Validate we have required tokens - especially refresh token for re-auth scenarios
            if not credentials.token:
                raise Exception("No access token received from Google")

            if not credentials.refresh_token:
                # This can happen when user re-authorizes - try to handle gracefully
                logger.warning(f"Warning: No refresh token received for {user_info.get('email', 'unknown')} - user may need to revoke app access first")
                # For now, we'll allow this but log it for monitoring

            return {
                'access_token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'expires_in': credentials.expiry.timestamp() if credentials.expiry else None,
                'user_info': user_info,
                'credentials': credentials.to_json()
            }
            
        except Exception as e:
            logger.error(f"Error exchanging code for tokens: {e}")
            return None
    
    async def _get_user_info(self, credentials: Credentials) -> Dict[str, Any]:
        """Get user information from Google."""
        try:
            # Build OAuth2 service
            service = build('oauth2', 'v2', credentials=credentials)
            user_info = service.userinfo().get().execute()
            
            return {
                'id': user_info.get('id'),
                'email': user_info.get('email'),
                'name': user_info.get('name'),
                'picture': user_info.get('picture'),
                'verified_email': user_info.get('verified_email', False)
            }
            
        except HttpError as e:
            logger.error(f"Error getting user info: {e}")
            return {}
    
    def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Refresh access token using refresh token."""
        self._ensure_configured()
        try:
            credentials = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            
            # Refresh the credentials
            credentials.refresh(httpx.Request())
            
            return {
                'access_token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'expires_in': credentials.expiry.timestamp() if credentials.expiry else None,
                'credentials': credentials.to_json()
            }
            
        except Exception as e:
            logger.error(f"Error refreshing access token: {e}")
            return None
    
    def get_credentials_from_token(self, access_token: str, refresh_token: str = None) -> Credentials:
        """Create Google credentials object from tokens."""
        self._ensure_configured()
        return Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret
        )
    
    def refresh_credentials_if_needed(self, credentials: Credentials) -> Credentials:
        """Auto-refresh expired credentials."""
        if credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(httpx.Request())
                logger.info(f"🔄 Refreshed expired Google credentials")
            except Exception as e:
                logger.error(f"❌ Failed to refresh credentials: {e}")
                raise
        return credentials
    
    # Gmail API methods
    async def get_gmail_messages(self, credentials: Credentials, query: str = '', max_results: int = 10) -> Dict[str, Any]:
        """Get Gmail messages for the authenticated user."""
        try:
            service = build('gmail', 'v1', credentials=credentials)
            
            # Get list of messages
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            message_details = []
            
            # Get details for each message
            for message in messages:
                msg = service.users().messages().get(
                    userId='me',
                    id=message['id'],
                    format='full'  # Get full message content including body
                ).execute()
                
                headers = msg.get('payload', {}).get('headers', [])
                header_dict = {h['name']: h['value'] for h in headers}
                
                # Extract email body content
                body_content = self._extract_email_body(msg.get('payload', {}))
                
                message_details.append({
                    'id': message['id'],
                    'threadId': msg.get('threadId'),
                    'from': header_dict.get('From', ''),
                    'subject': header_dict.get('Subject', ''),
                    'date': header_dict.get('Date', ''),
                    'snippet': msg.get('snippet', ''),
                    'body': body_content  # Include full body content
                })
            
            return {
                'messages': message_details,
                'resultSizeEstimate': results.get('resultSizeEstimate', 0)
            }
            
        except HttpError as e:
            logger.error(f"Error getting Gmail messages: {e}")
            return {'error': str(e), 'messages': []}
    
    def _extract_email_body(self, payload: Dict[str, Any]) -> str:
        """Extract email body content from Gmail API payload."""
        body_content = ""
        
        def decode_base64url(data: str) -> str:
            """Decode base64url encoded data."""
            try:
                import base64
                # Add padding if needed
                missing_padding = len(data) % 4
                if missing_padding:
                    data += '=' * (4 - missing_padding)
                # Replace URL-safe characters
                data = data.replace('-', '+').replace('_', '/')
                return base64.b64decode(data).decode('utf-8')
            except Exception as e:
                logger.error(f"Error decoding base64url: {e}")
                return ""
        
        def extract_text_from_part(part: Dict[str, Any]) -> str:
            """Extract text content from a message part."""
            mime_type = part.get('mimeType', '')
            body = part.get('body', {})
            
            if mime_type == 'text/plain':
                data = body.get('data', '')
                if data:
                    return decode_base64url(data)
            elif mime_type == 'text/html':
                data = body.get('data', '')
                if data:
                    # For HTML, we'll take it but prefer plain text
                    html_content = decode_base64url(data)
                    # Basic HTML tag removal for readability
                    import re
                    text_content = re.sub(r'<[^>]+>', '', html_content)
                    text_content = re.sub(r'\s+', ' ', text_content).strip()
                    return text_content
            elif mime_type.startswith('multipart/'):
                # Recursive extraction for multipart messages
                parts = part.get('parts', [])
                content_parts = []
                for subpart in parts:
                    subpart_content = extract_text_from_part(subpart)
                    if subpart_content:
                        content_parts.append(subpart_content)
                return '\n'.join(content_parts)
            
            return ""
        
        # Start extraction from the main payload
        body_content = extract_text_from_part(payload)
        
        # If no content found, try to get snippet as fallback
        if not body_content.strip():
            body_content = payload.get('snippet', '')
        
        return body_content.strip()
    
    async def get_gmail_message_content(self, credentials: Credentials, message_id: str) -> Dict[str, Any]:
        """Get full content of a Gmail message."""
        try:
            service = build('gmail', 'v1', credentials=credentials)
            
            message = service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            return {
                'id': message_id,
                'threadId': message.get('threadId'),
                'payload': message.get('payload'),
                'snippet': message.get('snippet')
            }
            
        except HttpError as e:
            logger.error(f"Error getting Gmail message content: {e}")
            return {'error': str(e)}
    
    # Drive API methods
    async def get_drive_files(self, credentials: Credentials, query: str = '', max_results: int = 10) -> Dict[str, Any]:
        """Get Google Drive files for the authenticated user."""
        try:
            credentials = self.refresh_credentials_if_needed(credentials)
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
    
    async def search_drive_files(self, credentials: Credentials, search_term: str = '', file_type: str = '', 
                                year: str = '', max_results: int = 10) -> Dict[str, Any]:
        """Advanced search for Google Drive files with filters for type, year, and content."""
        try:
            credentials = self.refresh_credentials_if_needed(credentials)
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
    
    async def search_drive_folders(self, credentials: Credentials, folder_name: str, max_results: int = 10) -> Dict[str, Any]:
        """Search specifically for folders in Google Drive."""
        try:
            credentials = self.refresh_credentials_if_needed(credentials)
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
    
    async def create_folder_structure(self, credentials: Credentials, folder_path: str, root_folder: str = "TURFMAPP") -> str:
        """Create nested folder structure in user's Drive (e.g., TURFMAPP/Projects/Client)."""
        try:
            credentials = self.refresh_credentials_if_needed(credentials)
            service = build('drive', 'v3', credentials=credentials)
            
            # Split path and add root folder
            path_parts = [root_folder] + [part.strip() for part in folder_path.split('/') if part.strip()]
            
            current_parent = None
            for folder_name in path_parts:
                folder_id = await self._get_or_create_folder(service, folder_name, current_parent)
                current_parent = folder_id
            
            return current_parent
            
        except Exception as e:
            logger.error(f"Error creating folder structure: {e}")
            raise
    
    async def _get_or_create_folder(self, service, folder_name: str, parent_id: str = None) -> str:
        """Get existing folder or create new one."""
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
    
    async def upload_file_to_drive(self, credentials: Credentials, file_content: bytes, filename: str, folder_path: str = None) -> Dict[str, Any]:
        """Upload file to specific folder in user's Drive."""
        try:
            credentials = self.refresh_credentials_if_needed(credentials)
            service = build('drive', 'v3', credentials=credentials)
            
            # Create folder structure if specified
            parent_folder_id = None
            if folder_path:
                parent_folder_id = await self.create_folder_structure(credentials, folder_path)
            
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
    
    async def delete_file_from_drive(self, credentials: Credentials, file_id: str) -> Dict[str, Any]:
        """Delete file from user's Drive."""
        try:
            credentials = self.refresh_credentials_if_needed(credentials)
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
    
    async def list_files_in_folder(self, credentials: Credentials, folder_path: str) -> Dict[str, Any]:
        """List all files in a specific folder path."""
        try:
            credentials = self.refresh_credentials_if_needed(credentials)
            service = build('drive', 'v3', credentials=credentials)
            
            # Find folder by path
            folder_id = await self.create_folder_structure(credentials, folder_path)
            
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
    
    async def get_shared_drives(self, credentials: Credentials, max_results: int = 10) -> Dict[str, Any]:
        """Get shared drives (Team Drives) that the user has access to."""
        try:
            credentials = self.refresh_credentials_if_needed(credentials)
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
    
    # Calendar API methods
    async def get_calendar_events(self, credentials: Credentials, calendar_id: str = 'primary', max_results: int = 10, upcoming_only: bool = True) -> Dict[str, Any]:
        """Get Google Calendar events for the authenticated user."""
        try:
            service = build('calendar', 'v3', credentials=credentials)
            
            # Build query parameters
            query_params = {
                'calendarId': calendar_id,
                'maxResults': max_results,
                'singleEvents': True,
                'orderBy': 'startTime'
            }
            
            # Add time filtering for upcoming events only
            if upcoming_only:
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc).isoformat()
                query_params['timeMin'] = now
                logger.debug(f"🗓️ Filtering calendar events from: {now}")
            
            events_result = service.events().list(**query_params).execute()
            
            return {
                'events': events_result.get('items', []),
                'nextPageToken': events_result.get('nextPageToken')
            }
            
        except HttpError as e:
            logger.error(f"Error getting Calendar events: {e}")
            return {'error': str(e), 'events': []}


# Global instance
google_oauth_service = GoogleOAuthService()
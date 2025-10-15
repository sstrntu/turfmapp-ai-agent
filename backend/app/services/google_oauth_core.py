"""
Google OAuth Core - Authentication and credential management

This module handles core Google OAuth operations including authorization,
token exchange, credential refresh, and user information retrieval.

Extracted from google_oauth.py (Phase 3 - January 2025)
"""

from __future__ import annotations

import logging
import os
from typing import Optional, Dict, Any

import httpx
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class GoogleOAuthCore:
    """Core OAuth operations for Google services."""

    def __init__(self):
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/auth/callback")

        # Required scopes for Gmail, Drive, and Calendar
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
            access_type='offline',
            include_granted_scopes='true',
            prompt='select_account consent',
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

            # Validate we have required tokens
            if not credentials.token:
                raise Exception("No access token received from Google")

            if not credentials.refresh_token:
                logger.warning(f"Warning: No refresh token received for {user_info.get('email', 'unknown')} - user may need to revoke app access first")

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
                logger.info("🔄 Refreshed expired Google credentials")
            except Exception as e:
                logger.error(f"❌ Failed to refresh credentials: {e}")
                raise
        return credentials

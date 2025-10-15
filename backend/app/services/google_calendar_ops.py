"""
Google Calendar Operations

This module handles Google Calendar API operations including event retrieval.

Extracted from google_oauth.py (Phase 3 - January 2025)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


async def get_calendar_events(credentials: Credentials, calendar_id: str = 'primary',
                             max_results: int = 10, upcoming_only: bool = True) -> Dict[str, Any]:
    """Get Google Calendar events for the authenticated user.

    Args:
        credentials (Credentials): Google OAuth2 credentials for authentication.
        calendar_id (str, optional): Calendar ID to retrieve events from. Defaults to 'primary'.
        max_results (int, optional): Maximum number of events to retrieve. Defaults to 10.
        upcoming_only (bool, optional): If True, only return future events. Defaults to True.

    Returns:
        Dict[str, Any]: Dictionary containing:
            - events (list): List of event objects
            - nextPageToken (str, optional): Token for pagination
            - error (str, optional): Error message if request fails

    Raises:
        HttpError: If Calendar API request fails (caught and logged).
    """
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

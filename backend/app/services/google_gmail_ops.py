"""
Google Gmail Operations

This module handles Gmail API operations including message retrieval,
content extraction, and body decoding.

Extracted from google_oauth.py (Phase 3 - January 2025)
"""

from __future__ import annotations

import base64
import logging
import re
from typing import Dict, Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


async def get_gmail_messages(credentials: Credentials, query: str = '', max_results: int = 10) -> Dict[str, Any]:
    """Retrieve Gmail messages with full content for the authenticated user.

    Fetches a list of Gmail messages matching the search query and retrieves full
    message details including headers and decoded body content for each message.

    Args:
        credentials (Credentials): Google OAuth2 credentials for authentication.
        query (str, optional): Gmail search query using Gmail search operators
            (e.g., "is:unread", "from:example@gmail.com"). Defaults to empty string
            which returns all messages.
        max_results (int, optional): Maximum number of messages to retrieve.
            Defaults to 10.

    Returns:
        Dict[str, Any]: Dictionary containing:
            - messages (list): List of message dictionaries with keys:
                - id (str): Message ID
                - threadId (str): Thread ID
                - from (str): Sender email address
                - subject (str): Email subject
                - date (str): Date header value
                - snippet (str): Short message preview
                - body (str): Full decoded email body
            - resultSizeEstimate (int): Estimated total matching messages
            - error (str, optional): Error message if request fails

    Raises:
        HttpError: If Gmail API request fails (caught and logged).
    """
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
            body_content = extract_email_body(msg.get('payload', {}))

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


def extract_email_body(payload: Dict[str, Any]) -> str:
    """Extract and decode email body content from Gmail API payload.

    This function recursively traverses the payload structure to extract text content
    from emails, handling both plain text and HTML formats, as well as multipart
    messages. Base64url encoded data is decoded and HTML tags are stripped from
    HTML content.

    Args:
        payload (Dict[str, Any]): The payload object from a Gmail API message response,
            containing the message structure and body data.

    Returns:
        str: The decoded and formatted email body text. Returns empty string if no
            content can be extracted. Falls back to snippet if main extraction fails.
    """
    body_content = ""

    def decode_base64url(data: str) -> str:
        """Decode base64url encoded data."""
        try:
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


async def get_gmail_message_content(credentials: Credentials, message_id: str) -> Dict[str, Any]:
    """Retrieve the full content and metadata of a specific Gmail message.

    Args:
        credentials (Credentials): Google OAuth2 credentials for authentication.
        message_id (str): The unique identifier of the message to retrieve.

    Returns:
        Dict[str, Any]: Dictionary containing:
            - id (str): Message ID
            - threadId (str): Thread ID this message belongs to
            - payload (dict): Complete message payload with headers and body
            - snippet (str): Short message preview
            - error (str, optional): Error message if request fails

    Raises:
        HttpError: If Gmail API request fails (caught and logged).
    """
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

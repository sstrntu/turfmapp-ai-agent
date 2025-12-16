"""
Gmail Tools using LlamaIndex FunctionTool

Provides Gmail operations (search, read messages) as LlamaIndex FunctionTools
that can be used by agents for email management tasks.
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any

from llama_index.core.tools import FunctionTool
from google.oauth2.credentials import Credentials

from ...services.google_gmail_ops import (
    get_gmail_messages,
    get_gmail_message_content,
)

logger = logging.getLogger(__name__)


def search_gmail_messages(
    credentials: Credentials,
    query: str = "",
    max_results: int = 10
) -> str:
    """
    Search Gmail messages using Gmail search operators.

    This function searches the user's Gmail inbox and returns matching messages
    with their details including subject, sender, date, and body content.

    Args:
        credentials: Google OAuth2 credentials for authentication
        query: Gmail search query (e.g., "is:unread", "from:example@gmail.com", "subject:important")
            Empty string returns recent messages. Common operators:
            - is:unread, is:read
            - from:sender@example.com
            - to:recipient@example.com
            - subject:keyword
            - has:attachment
            - after:YYYY/MM/DD, before:YYYY/MM/DD
        max_results: Maximum number of messages to return (default: 10, max: 50)

    Returns:
        str: Formatted string with message details including:
            - Message ID
            - From (sender)
            - Subject
            - Date
            - Snippet (preview)
            - Full body content
            Or error message if search fails

    Example:
        >>> search_gmail_messages(creds, "is:unread from:boss@company.com", 5)
        "Found 3 messages:

         Message 1:
         ID: 18f2a3b4c5d6e7f8
         From: boss@company.com
         Subject: Quarterly Review
         Date: Mon, 20 Jan 2025 10:30:00 -0800
         Body: Please review the attached document..."
    """
    import asyncio

    # Run async function
    result = asyncio.run(get_gmail_messages(
        credentials=credentials,
        query=query,
        max_results=min(max_results, 50)  # Cap at 50
    ))

    if "error" in result:
        return f"Error searching Gmail: {result['error']}"

    messages = result.get("messages", [])
    total = result.get("resultSizeEstimate", 0)

    if not messages:
        return f"No messages found matching query: '{query}'"

    # Format messages for LLM
    output_lines = [f"Found {len(messages)} messages (total matching: {total}):\n"]

    for i, msg in enumerate(messages, 1):
        output_lines.append(f"Message {i}:")
        output_lines.append(f"  ID: {msg.get('id', 'N/A')}")
        output_lines.append(f"  From: {msg.get('from', 'N/A')}")
        output_lines.append(f"  Subject: {msg.get('subject', 'N/A')}")
        output_lines.append(f"  Date: {msg.get('date', 'N/A')}")
        output_lines.append(f"  Snippet: {msg.get('snippet', 'N/A')}")

        # Include body content (truncated if too long)
        body = msg.get('body', '')
        if body:
            body_preview = body[:500] + "..." if len(body) > 500 else body
            output_lines.append(f"  Body: {body_preview}")

        output_lines.append("")  # Empty line between messages

    return "\n".join(output_lines)


def get_gmail_message_details(
    credentials: Credentials,
    message_id: str
) -> str:
    """
    Get detailed information about a specific Gmail message.

    Retrieves the full content and metadata of a single message by its ID.
    Useful for reading complete message content after searching.

    Args:
        credentials: Google OAuth2 credentials for authentication
        message_id: The unique ID of the message to retrieve

    Returns:
        str: Formatted string with complete message details:
            - Message ID
            - Thread ID
            - Complete payload with headers
            - Full body content
            Or error message if retrieval fails

    Example:
        >>> get_gmail_message_details(creds, "18f2a3b4c5d6e7f8")
        "Message Details:
         ID: 18f2a3b4c5d6e7f8
         Thread ID: 18f2a3b4c5d6e7f8
         Full content: [complete message body]"
    """
    import asyncio

    # Run async function
    result = asyncio.run(get_gmail_message_content(
        credentials=credentials,
        message_id=message_id
    ))

    if "error" in result:
        return f"Error retrieving message: {result['error']}"

    output_lines = ["Message Details:"]
    output_lines.append(f"  ID: {result.get('id', 'N/A')}")
    output_lines.append(f"  Thread ID: {result.get('threadId', 'N/A')}")
    output_lines.append(f"  Snippet: {result.get('snippet', 'N/A')}")

    # Extract full content from payload
    payload = result.get('payload', {})
    if payload:
        from ...services.google_gmail_ops import extract_email_body
        body = extract_email_body(payload)
        if body:
            output_lines.append(f"\nFull Content:\n{body}")

    return "\n".join(output_lines)


def create_gmail_tools(credentials: Credentials) -> List[FunctionTool]:
    """
    Create LlamaIndex FunctionTools for Gmail operations.

    Args:
        credentials: Google OAuth2 credentials for the user

    Returns:
        List of FunctionTool instances for Gmail operations
    """
    # Create partially applied functions with credentials
    def search_messages(query: str = "", max_results: int = 10) -> str:
        """Search Gmail messages. Use query parameter for filtering (e.g., 'is:unread', 'from:email@example.com')."""
        return search_gmail_messages(credentials, query, max_results)

    def get_message(message_id: str) -> str:
        """Get detailed information about a specific Gmail message by ID."""
        return get_gmail_message_details(credentials, message_id)

    # Create FunctionTools
    tools = [
        FunctionTool.from_defaults(
            fn=search_messages,
            name="search_gmail_messages",
            description=(
                "Search Gmail messages using Gmail search operators. "
                "Returns message details including subject, sender, date, and body content. "
                "Common query operators: 'is:unread', 'from:email@example.com', 'subject:keyword', "
                "'has:attachment', 'after:YYYY/MM/DD'. "
                "Use this to find emails based on sender, subject, date, or read status."
            ),
        ),
        FunctionTool.from_defaults(
            fn=get_message,
            name="get_gmail_message",
            description=(
                "Get detailed information about a specific Gmail message by its ID. "
                "Returns the full message content including complete body text. "
                "Use this after searching to get the complete content of a specific email."
            ),
        ),
    ]

    logger.info(f"Created {len(tools)} Gmail tools")
    return tools

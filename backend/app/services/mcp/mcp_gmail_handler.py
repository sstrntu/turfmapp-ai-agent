"""
Gmail tool handlers for MCP client.

This module handles Gmail-specific tool operations including searching emails,
retrieving messages, getting recent emails, and accessing important/starred messages.
Formats results into user-friendly response text with email details.
"""

from __future__ import annotations

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


async def handle_gmail_tool(name: str, credentials, arguments: Dict[str, Any], google_oauth_service) -> Dict[str, Any]:
    """Handle Gmail tool calls by routing to appropriate Gmail service methods.

    Processes Gmail-related tool requests including search, get message, recent emails,
    and important emails. Formats the results into user-friendly response text with
    message details, sender information, and content snippets.

    Args:
        name (str): The name of the Gmail tool to execute. Supported values are:
            - "gmail_search": Search Gmail messages with query parameters
            - "gmail_get_message": Get full content of a specific message
            - "gmail_recent": Get recent Gmail messages
            - "gmail_important": Get important/starred Gmail messages
        credentials: Google OAuth credentials object for authenticating API calls.
        arguments (Dict[str, Any]): Tool-specific arguments which may include:
            - query (str, optional): Search query for gmail_search
            - max_results (int, optional): Maximum number of results to return
            - message_id (str): Required for gmail_get_message
        google_oauth_service: The Google OAuth service instance for making API calls.

    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): Whether the operation succeeded
            - response (str): Formatted response text with email details
            - tool (str): The name of the tool that was executed
            - error (str, optional): Error message if success is False

    Raises:
        Exception: Caught internally and returned as error in response dict.
    """
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

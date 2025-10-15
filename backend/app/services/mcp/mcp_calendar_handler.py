"""
Google Calendar tool handlers for MCP client.

This module handles Google Calendar-specific tool operations including listing
events and fetching upcoming events. Formats results with event details including
title, start time, and location information.
"""

from __future__ import annotations

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


async def handle_calendar_tool(name: str, credentials, arguments: Dict[str, Any], google_oauth_service) -> Dict[str, Any]:
    """Handle Google Calendar tool calls by routing to appropriate Calendar service methods.

    Processes Google Calendar-related tool requests including listing events and
    fetching upcoming events. Formats results with event details including title,
    start time, and location information.

    Args:
        name (str): The name of the Calendar tool to execute. Supported values are:
            - "calendar_list_events": List calendar events from a specific calendar
            - "calendar_upcoming_events": Get upcoming events for the next N days
        credentials: Google OAuth credentials object for authenticating API calls.
        arguments (Dict[str, Any]): Tool-specific arguments which may include:
            - calendar_id (str, optional): Calendar ID to list events from (default: "primary")
            - max_results (int, optional): Maximum number of results to return
            - days (int, optional): Number of days to look ahead for upcoming events
        google_oauth_service: The Google OAuth service instance for making API calls.

    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): Whether the operation succeeded
            - response (str): Formatted response text with event details
            - tool (str): The name of the tool that was executed
            - error (str, optional): Error message if success is False

    Raises:
        Exception: Caught internally and returned as error in response dict.
    """
    try:
        logger.debug(f"🗓️ Handling calendar tool '{name}' with arguments: {arguments}")
        if name == "calendar_list_events":
            calendar_id = arguments.get("calendar_id", "primary")
            max_results = arguments.get("max_results", 10)

            # Default to upcoming events unless specifically requested otherwise
            result = await google_oauth_service.get_calendar_events(
                credentials=credentials, calendar_id=calendar_id, max_results=max_results, upcoming_only=True
            )

            if "error" in result:
                return {"success": False, "response": f"❌ Calendar access failed: {result['error']}", "tool": name}

            events = result.get("events", [])
            if not events:
                response_text = "📅 No calendar events found."
            else:
                response_text = f"📅 **Found {len(events)} calendar events:**\n\n"
                for i, event in enumerate(events, 1):
                    title = event.get('summary', 'No Title')
                    start_time = event.get('start', {})

                    # Format time
                    start_date = start_time.get('dateTime', start_time.get('date', 'Unknown time'))

                    response_text += f"{i}. **{title}**\n"
                    response_text += f"   🕐 Start: {start_date}\n"

                    if event.get('location'):
                        response_text += f"   📍 Location: {event['location']}\n"

                    response_text += "\n"

            return {"success": True, "response": response_text, "tool": name}

        elif name == "calendar_upcoming_events":
            days = arguments.get("days", 7)
            logger.debug(f"🗓️ Getting upcoming calendar events for {days} days")

            # Get only upcoming events (future events from now)
            result = await google_oauth_service.get_calendar_events(
                credentials=credentials, calendar_id="primary", max_results=10, upcoming_only=True
            )

            logger.debug(f"🗓️ Calendar API result: {result}")

            if "error" in result:
                logger.error(f"❌ Calendar API error: {result['error']}")
                return {"success": False, "response": f"❌ Failed to get upcoming events: {result['error']}", "tool": name}

            events = result.get("events", [])
            logger.debug(f"🗓️ Found {len(events)} calendar events")

            if not events:
                response_text = f"📅 No upcoming events in the next {days} days."
            else:
                response_text = f"📅 **Upcoming events (next {days} days):**\n\n"
                for i, event in enumerate(events, 1):
                    title = event.get('summary', 'No Title')
                    start_time = event.get('start', {})
                    start_date = start_time.get('dateTime', start_time.get('date', 'Unknown time'))

                    response_text += f"{i}. **{title}**\n"
                    response_text += f"   🕐 {start_date}\n\n"

            logger.debug(f"✅ Returning calendar response: {response_text[:100]}...")
            return {"success": True, "response": response_text, "tool": name}

        else:
            return {"success": False, "error": f"Unknown Calendar tool: {name}", "tool": name}

    except Exception as e:
        logger.error(f"❌ Calendar tool exception: {str(e)}")
        import traceback
        logger.error(f"❌ Calendar tool traceback: {traceback.format_exc()}")
        return {"success": False, "error": f"Calendar tool error: {str(e)}", "tool": name}

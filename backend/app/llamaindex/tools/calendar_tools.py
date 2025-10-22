"""
Google Calendar Tools using LlamaIndex FunctionTool

Provides Google Calendar operations (list events, search events) as LlamaIndex
FunctionTools for calendar and scheduling tasks.
"""

from __future__ import annotations

import logging
from typing import List
from datetime import datetime, timezone

from llama_index.core.tools import FunctionTool
from google.oauth2.credentials import Credentials

from ...services.google_calendar_ops import get_calendar_events

logger = logging.getLogger(__name__)


def list_upcoming_events(
    credentials: Credentials,
    max_results: int = 10,
    calendar_id: str = "primary"
) -> str:
    """
    List upcoming events from Google Calendar.

    Args:
        credentials: Google OAuth2 credentials
        max_results: Maximum number of events to return (default: 10)
        calendar_id: Calendar ID to query (default: "primary" for main calendar)

    Returns:
        str: Formatted string with event details or error message

    Example:
        >>> list_upcoming_events(creds, 5)
        "Upcoming events (5 total):

         Event 1:
         Summary: Team Meeting
         Start: 2025-01-21T10:00:00-08:00
         End: 2025-01-21T11:00:00-08:00
         Location: Conference Room A
         Link: https://calendar.google.com/..."
    """
    import asyncio

    result = asyncio.run(get_calendar_events(
        credentials=credentials,
        calendar_id=calendar_id,
        max_results=min(max_results, 50),
        upcoming_only=True
    ))

    if "error" in result:
        return f"Error listing calendar events: {result['error']}"

    events = result.get("events", [])

    if not events:
        return "No upcoming events found in calendar"

    output_lines = [f"Upcoming events ({len(events)} total):\n"]

    for i, event in enumerate(events, 1):
        output_lines.append(f"Event {i}:")
        output_lines.append(f"  Summary: {event.get('summary', 'N/A')}")

        # Handle start time
        start = event.get('start', {})
        start_time = start.get('dateTime', start.get('date', 'N/A'))
        output_lines.append(f"  Start: {start_time}")

        # Handle end time
        end = event.get('end', {})
        end_time = end.get('dateTime', end.get('date', 'N/A'))
        output_lines.append(f"  End: {end_time}")

        # Optional fields
        if event.get('location'):
            output_lines.append(f"  Location: {event.get('location')}")

        if event.get('description'):
            description = event.get('description', '')
            # Truncate long descriptions
            if len(description) > 200:
                description = description[:200] + "..."
            output_lines.append(f"  Description: {description}")

        if event.get('attendees'):
            attendee_emails = [a.get('email', '') for a in event.get('attendees', [])]
            output_lines.append(f"  Attendees: {', '.join(attendee_emails[:5])}")

        if event.get('htmlLink'):
            output_lines.append(f"  Link: {event.get('htmlLink')}")

        output_lines.append("")

    return "\n".join(output_lines)


def list_recent_events(
    credentials: Credentials,
    max_results: int = 10,
    calendar_id: str = "primary"
) -> str:
    """
    List recent events from Google Calendar (past and upcoming).

    Args:
        credentials: Google OAuth2 credentials
        max_results: Maximum number of events to return (default: 10)
        calendar_id: Calendar ID to query (default: "primary" for main calendar)

    Returns:
        str: Formatted string with event details or error message

    Example:
        >>> list_recent_events(creds, 5)
        "Recent events (5 total):

         Event 1:
         Summary: Project Review
         Start: 2025-01-20T14:00:00-08:00
         Status: Past event"
    """
    import asyncio

    result = asyncio.run(get_calendar_events(
        credentials=credentials,
        calendar_id=calendar_id,
        max_results=min(max_results, 50),
        upcoming_only=False  # Include past events
    ))

    if "error" in result:
        return f"Error listing recent calendar events: {result['error']}"

    events = result.get("events", [])

    if not events:
        return "No recent events found in calendar"

    output_lines = [f"Recent events ({len(events)} total):\n"]
    now = datetime.now(timezone.utc)

    for i, event in enumerate(events, 1):
        output_lines.append(f"Event {i}:")
        output_lines.append(f"  Summary: {event.get('summary', 'N/A')}")

        # Handle start time
        start = event.get('start', {})
        start_time = start.get('dateTime', start.get('date', 'N/A'))
        output_lines.append(f"  Start: {start_time}")

        # Handle end time
        end = event.get('end', {})
        end_time = end.get('dateTime', end.get('date', 'N/A'))
        output_lines.append(f"  End: {end_time}")

        # Determine if past or upcoming
        try:
            event_start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            if event_start < now:
                output_lines.append("  Status: Past event")
            else:
                output_lines.append("  Status: Upcoming event")
        except (ValueError, AttributeError):
            pass  # Can't parse date, skip status

        # Optional fields
        if event.get('location'):
            output_lines.append(f"  Location: {event.get('location')}")

        if event.get('htmlLink'):
            output_lines.append(f"  Link: {event.get('htmlLink')}")

        output_lines.append("")

    return "\n".join(output_lines)


def search_calendar_events(
    credentials: Credentials,
    search_term: str,
    max_results: int = 10,
    calendar_id: str = "primary"
) -> str:
    """
    Search for events in Google Calendar by summary or description.

    Note: This is a client-side search since Calendar API doesn't support
    server-side text search. For better performance with large calendars,
    consider limiting max_results.

    Args:
        credentials: Google OAuth2 credentials
        search_term: Text to search for in event summary or description
        max_results: Maximum number of events to fetch for searching (default: 10)
        calendar_id: Calendar ID to query (default: "primary" for main calendar)

    Returns:
        str: Formatted string with matching event details or error message

    Example:
        >>> search_calendar_events(creds, "team meeting", 20)
        "Found 3 matching events:

         Event 1:
         Summary: Weekly Team Meeting
         Start: 2025-01-21T10:00:00-08:00
         Match: Found in summary"
    """
    import asyncio

    # Fetch more events to search through
    result = asyncio.run(get_calendar_events(
        credentials=credentials,
        calendar_id=calendar_id,
        max_results=min(max_results * 2, 100),  # Fetch more to search
        upcoming_only=True
    ))

    if "error" in result:
        return f"Error searching calendar events: {result['error']}"

    events = result.get("events", [])

    if not events:
        return "No events found in calendar to search"

    # Filter events by search term
    search_lower = search_term.lower()
    matching_events = []

    for event in events:
        summary = event.get('summary', '').lower()
        description = event.get('description', '').lower()

        match_location = None
        if search_lower in summary:
            match_location = "summary"
        elif search_lower in description:
            match_location = "description"

        if match_location:
            matching_events.append((event, match_location))

        # Limit to max_results
        if len(matching_events) >= max_results:
            break

    if not matching_events:
        return f"No events found matching '{search_term}'"

    output_lines = [f"Found {len(matching_events)} matching events:\n"]

    for i, (event, match_location) in enumerate(matching_events, 1):
        output_lines.append(f"Event {i}:")
        output_lines.append(f"  Summary: {event.get('summary', 'N/A')}")

        # Handle start time
        start = event.get('start', {})
        start_time = start.get('dateTime', start.get('date', 'N/A'))
        output_lines.append(f"  Start: {start_time}")

        # Handle end time
        end = event.get('end', {})
        end_time = end.get('dateTime', end.get('date', 'N/A'))
        output_lines.append(f"  End: {end_time}")

        output_lines.append(f"  Match: Found in {match_location}")

        # Optional fields
        if event.get('location'):
            output_lines.append(f"  Location: {event.get('location')}")

        if event.get('htmlLink'):
            output_lines.append(f"  Link: {event.get('htmlLink')}")

        output_lines.append("")

    return "\n".join(output_lines)


def create_calendar_tools(credentials: Credentials) -> List[FunctionTool]:
    """
    Create LlamaIndex FunctionTools for Google Calendar operations.

    Args:
        credentials: Google OAuth2 credentials for the user

    Returns:
        List of FunctionTool instances for Calendar operations
    """
    # Create partially applied functions with credentials
    def list_upcoming_tool(max_results: int = 10, calendar_id: str = "primary") -> str:
        """List upcoming events from Google Calendar."""
        return list_upcoming_events(credentials, max_results, calendar_id)

    def list_recent_tool(max_results: int = 10, calendar_id: str = "primary") -> str:
        """List recent events from Google Calendar (past and upcoming)."""
        return list_recent_events(credentials, max_results, calendar_id)

    def search_events_tool(search_term: str, max_results: int = 10, calendar_id: str = "primary") -> str:
        """Search for events in Google Calendar by summary or description."""
        return search_calendar_events(credentials, search_term, max_results, calendar_id)

    # Create FunctionTools
    tools = [
        FunctionTool.from_defaults(
            fn=list_upcoming_tool,
            name="list_upcoming_calendar_events",
            description=(
                "List upcoming events from Google Calendar. "
                "Returns event summaries, start/end times, locations, attendees, and links. "
                "Use this to see what events are scheduled in the future."
            ),
        ),
        FunctionTool.from_defaults(
            fn=list_recent_tool,
            name="list_recent_calendar_events",
            description=(
                "List recent events from Google Calendar (both past and upcoming). "
                "Returns event summaries with start/end times and status (past/upcoming). "
                "Use this to see recent calendar activity or review past events."
            ),
        ),
        FunctionTool.from_defaults(
            fn=search_events_tool,
            name="search_calendar_events",
            description=(
                "Search for events in Google Calendar by keywords in summary or description. "
                "Returns matching events with details and indicates where the match was found. "
                "Use this to find specific events or meetings by topic or keywords."
            ),
        ),
    ]

    logger.info(f"Created {len(tools)} Calendar tools")
    return tools

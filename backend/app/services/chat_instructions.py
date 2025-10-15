"""
Shared helpers for constructing system/developer instructions that guide model
behavior regardless of which provider (OpenAI, Anthropic, etc.) is used.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional

BASE_TOOL_RULES = """
CRITICAL TOOL USAGE RULE:
- Gmail, Drive, and Calendar tools are ONLY for personal data (emails, files, calendar events)
- NEVER use these tools for general knowledge questions, sports scores, news, weather, or any non-personal data
- For general knowledge questions, use web search or answer from your training data
- Examples of what NOT to use Google tools for: "Who is the top scorer?", "What's the weather?", "Latest news"

CONVERSATION CONTEXT RULES:
1. The current user question is marked as "CURRENT USER QUESTION:" - THIS is what you must respond to
2. Use conversation history for context, but ALWAYS address the current question directly
3. Never return a previous answer when asked a new question, even if they seem similar
4. For time-sensitive data (sports scores, news, weather), always perform fresh searches regardless of history
5. If the current question asks about personal data (emails, calendar, files), use the appropriate tools even if similar questions were asked before
""".strip()

WEB_SEARCH_RULES = """
You have tools available. Use them when they would provide better, more current information than your training data. Use web search for current information: sports scores, news, weather, current season data, latest facts, or when users ask 'who is', 'what is the latest', 'this season', 'this year'.""".strip()

GOOGLE_SERVICE_RULES = """
You have access to Google service tools (Gmail, Drive, Calendar) that can help users with their personal data.

CRITICAL RULE: These tools are ONLY for personal data (emails, files, calendar events). NEVER use these tools for general knowledge questions, sports scores, news, weather, or any non-personal data queries.

Gmail tools (ONLY for personal emails):
- gmail_recent: Get recent Gmail messages
- gmail_search: Search Gmail messages with query parameters
- gmail_get_message: Get full content of a specific Gmail message
- gmail_important: Get important/starred Gmail messages

Drive tools (ONLY for personal files):
- drive_list_files: List files in Google Drive
- drive_create_folder: Create folder structure in Google Drive
- drive_list_folder_files: List files in a specific Drive folder

Calendar tools (ONLY for personal schedule):
- calendar_list_events: List Google Calendar events
- calendar_upcoming_events: Get upcoming calendar events

Examples of when to use Google tools:
- "Show me my recent emails"
- "What files do I have in my Drive?"
- "What's on my calendar today?"
- "Find emails from John"

Examples of when NOT to use Google tools:
- "Who is the top scorer in J1?" (general knowledge - use web search instead)
- "Who is the top J2 scorer in 2025 season?" (general knowledge - use web search instead)
- "What is the capital of France?" (general knowledge)
- "Tell me about the latest news" (general knowledge - use web search instead)
- "What's the weather like?" (general knowledge - use web search instead)

For general knowledge questions, use web search or answer from your training data.
""".strip()


def build_system_instructions(
    *,
    tools: Optional[List[Dict[str, Any]]] = None,
    developer_instructions: Optional[str] = None,
    assistant_context: Optional[str] = None,
) -> str:
    """
    Build a consolidated system instruction string based on available tools and
    caller-provided context. Returns an empty string if no instructions apply.
    """
    instructions: List[str] = [BASE_TOOL_RULES]

    if developer_instructions:
        instructions.append(developer_instructions)

    if assistant_context:
        instructions.append(assistant_context)

    tool_list = tools or []
    if tool_list:
        if any(tool.get("type") in {"web_search_preview", "web_search"} for tool in tool_list):
            instructions.append(WEB_SEARCH_RULES)

        if any(tool.get("name", "").startswith(("gmail_", "drive_", "calendar_")) for tool in tool_list):
            instructions.append(GOOGLE_SERVICE_RULES)

    # Filter out empty sections and join with double newlines
    filtered = [section.strip() for section in instructions if section and section.strip()]
    return "\n\n".join(filtered)

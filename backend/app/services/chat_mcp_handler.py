"""
MCP Request Handler - AI-driven tool selection and execution

This module handles Google MCP requests using AI-driven tool selection.
Processes user requests, selects appropriate tools, executes them, and
analyzes results with AI to provide intelligent responses.

Extracted from chat_tool_handler.py (Phase 3 - January 2025)
"""

from __future__ import annotations

import json
import logging
import re
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


async def handle_google_mcp_request(
    chat_api_client,
    user_message: str,
    conversation_history: List[Dict[str, Any]],
    user_id: str,
    enabled_tools: Dict[str, bool],
    available_tools: List[Dict[str, Any]],
    **kwargs
) -> Dict[str, Any]:
    """Handle Google MCP request using AI-driven tool selection.

    Processes user requests for Google services by:
    1. Using AI to select the most appropriate tool(s) for the user's request
    2. Executing the selected tools via the Google MCP client
    3. Analyzing and summarizing results with AI
    4. Providing intelligent fallback responses when tools aren't enabled

    The function supports parallel tool execution and provides contextual
    suggestions when required tools are not enabled.

    Args:
        chat_api_client: ChatApiClient instance for AI-driven tool selection.
        user_message (str): The user's natural language request or question.
        conversation_history (List[Dict[str, Any]]): Previous messages in the
            conversation for context. Each message should have 'role' and 'content'.
        user_id (str): Unique identifier for the user making the request. Used
            for authentication with Google services.
        enabled_tools (Dict[str, bool]): Dictionary of enabled Google services.
            Keys: 'gmail', 'calendar', 'drive'. Values: True if enabled.
        available_tools (List[Dict[str, Any]]): List of available tool definitions
            built from enabled_tools.
        **kwargs: Additional keyword arguments for future extensibility.

    Returns:
        Dict[str, Any]: Response dictionary containing:
            - success (bool): Whether the request was successful
            - response (str): The formatted response message for the user
            - tools_used (List[str], optional): List of tools that were executed
            - suggested_tools (List[str], optional): Suggested tools when none enabled
            - sources (List, optional): Source references for the response

    Raises:
        Exception: Catches and logs all exceptions, returning error response dict.

    Example:
        >>> result = await handle_google_mcp_request(
        ...     chat_api_client=api_client,
        ...     user_message="What's my latest email?",
        ...     conversation_history=[],
        ...     user_id="user123",
        ...     enabled_tools={'gmail': True, 'calendar': False, 'drive': False},
        ...     available_tools=[...]
        ... )
        >>> result['success']
        True
    """
    try:
        if not available_tools:
            # Provide intelligent response based on what tools the user likely needs
            message_lower = user_message.lower()
            if any(keyword in message_lower for keyword in ['email', 'gmail', 'message', 'inbox']):
                return {
                    "success": False,
                    "response": "I'd love to help you with your emails! To access your Gmail, please enable Gmail access by clicking the Gmail icon (📧) in the interface. Once connected, I can help you check your latest emails, search for specific messages, and summarize your inbox.",
                    "suggested_tools": ["gmail"]
                }
            elif any(keyword in message_lower for keyword in ['calendar', 'meeting', 'event', 'schedule']):
                return {
                    "success": False,
                    "response": "I can help you with your calendar! Please enable Calendar access by clicking the Calendar icon (📅) in the interface to check your upcoming meetings and events.",
                    "suggested_tools": ["calendar"]
                }
            elif any(keyword in message_lower for keyword in ['file', 'drive', 'document']):
                return {
                    "success": False,
                    "response": "I can help you with your files! Please enable Google Drive access by clicking the Drive icon (📁) in the interface to browse your documents and files.",
                    "suggested_tools": ["drive"]
                }
            else:
                return {"success": False, "response": "No Google tools were enabled. Please enable the tools you'd like to use (Gmail 📧, Calendar 📅, or Drive 📁) in the interface."}

        # Use AI to select and call the appropriate tools
        logger.debug(f"🤖 Using AI-driven tool selection with {len(available_tools)} available tools")

        # Get Google MCP client
        from .mcp_client import google_mcp_client

        # Create system prompt for tool selection
        tool_selection_prompt = f"""You are helping a user with their Google services (Gmail, Calendar, Drive).

User question: "{user_message}"

Available tools:
{chr(10).join([f"- {tool['function']['name']}: {tool['function']['description']}" for tool in available_tools])}

Select the most appropriate tool(s) and parameters to answer the user's question. Be precise with parameters:
- For 'first/latest/newest' email questions: use gmail_recent with max_results=1
- For 'recent emails' questions: use gmail_recent with max_results=3-5
- For search questions: use gmail_search with appropriate query
"""

        # Let AI select tools using function calling
        messages = [
            {"role": "system", "content": tool_selection_prompt},
            {"role": "user", "content": user_message}
        ]

        tool_selection_result = await chat_api_client.call_responses_api(
            messages=messages,
            tools=available_tools,
            user_id=user_id
        )

        logger.debug(f"🤖 Tool selection result: {tool_selection_result}")

        # Extract function calls from the response
        tool_results = []
        function_calls = []

        # Process API response to extract function calls
        output_items = tool_selection_result.get("output", [])
        for item in output_items:
            if isinstance(item, dict):
                if item.get("type") in ["function_call", "tool_call"]:
                    # Direct function call format
                    function_calls.append({
                        "function": {
                            "name": item.get("name"),
                            "arguments": json.loads(item.get("arguments", "{}")) if isinstance(item.get("arguments"), str) else item.get("arguments", {})
                        }
                    })
                elif item.get("type") == "message":
                    content = item.get("content", [])
                    for content_item in content:
                        if content_item.get("type") == "tool_use":
                            function_calls.append({
                                "function": {
                                    "name": content_item.get("name"),
                                    "arguments": content_item.get("input", {})
                                }
                            })

        logger.debug(f"🤖 Function calls parsed: {function_calls}")

        logger.debug(f"🤖 Extracted {len(function_calls)} function calls")

        # Execute the selected tools
        for func_call in function_calls:
            try:
                if isinstance(func_call.get("function"), dict):
                    function_info = func_call["function"]
                    tool_name = function_info.get("name")
                    arguments = function_info.get("arguments", {})
                else:
                    continue

                # Prepare parameters for MCP call
                params = {"user_id": user_id}
                params.update(arguments)

                logger.debug(f"🔧 Calling {tool_name} with params: {params}")
                result = await google_mcp_client.call_tool(tool_name, params)

                logger.debug(f"🔧 Raw result from {tool_name}: {result}")

                tool_results.append({
                    "tool": tool_name,
                    "success": result.get("success", False) if isinstance(result, dict) else False,
                    "response": result.get("response", "") if isinstance(result, dict) else str(result),
                    "error": result.get("error") if isinstance(result, dict) else None
                })

            except Exception as e:
                logger.error(f"❌ Error calling {tool_name}: {e}")
                tool_results.append({
                    "tool": tool_name,
                    "success": False,
                    "response": "",
                    "error": str(e)
                })

        # If no function calls were made, fall back to default behavior
        if not function_calls and available_tools:
            logger.info("🔄 No function calls detected, using fallback logic")
            # Default to gmail_recent for Gmail questions
            if enabled_tools.get('gmail'):
                params = {"user_id": user_id, "max_results": 1 if 'first' in user_message.lower() else 5}
                try:
                    result = await google_mcp_client.call_tool("gmail_recent", params)
                    tool_results.append({
                        "tool": "gmail_recent",
                        "success": result.get("success", False) if isinstance(result, dict) else False,
                        "response": result.get("response", "") if isinstance(result, dict) else str(result),
                        "error": result.get("error") if isinstance(result, dict) else None
                    })
                except Exception as e:
                    logger.error(f"❌ Fallback error: {e}")
                    tool_results.append({
                        "tool": "gmail_recent",
                        "success": False,
                        "response": "",
                        "error": str(e)
                    })

            # Default Drive fallback for Drive questions
            elif enabled_tools.get('drive'):
                # Simple fallback logic like Gmail
                user_msg_lower = user_message.lower()

                # Detect folder search vs general file search
                if any(word in user_msg_lower for word in ['folder', 'directory']):
                    # Extract potential folder name from the message (like Gmail extracts "first")
                    words = [w for w in user_message.split() if w not in ['find', 'the', 'folder', 'directory', 'get', 'me']]
                    folder_name = ' '.join(words) if words else ""

                    params = {"user_id": user_id, "folder_name": folder_name, "max_results": 10}
                    drive_tool = "drive_search_folders"
                else:
                    # Default to file listing (like gmail_recent)
                    params = {"user_id": user_id, "max_results": 10}
                    drive_tool = "drive_list_files"

                logger.info(f"🔄 Drive fallback: using {drive_tool}")

                try:
                    result = await google_mcp_client.call_tool(drive_tool, params)
                    tool_results.append({
                        "tool": drive_tool,
                        "success": result.get("success", False) if isinstance(result, dict) else False,
                        "response": result.get("response", "") if isinstance(result, dict) else str(result),
                        "error": result.get("error") if isinstance(result, dict) else None
                    })
                except Exception as e:
                    logger.error(f"❌ Drive fallback error: {e}")
                    tool_results.append({
                        "tool": drive_tool,
                        "success": False,
                        "response": "",
                        "error": str(e)
                    })

        # Combine successful results
        successful_results = [r for r in tool_results if r["success"]]

        if not successful_results:
            return {
                "success": False,
                "response": "I couldn't retrieve data from your Google services. Please check your permissions and try again."
            }

        # Special handling for folder searches - return directly without AI processing
        for result in successful_results:
            if result["tool"] == "drive_search_folders" and result.get("response"):
                logger.debug("🔄 Returning folder search result directly without AI analysis")
                return {
                    "success": True,
                    "response": result["response"],
                    "tools_used": [result["tool"]]
                }

        # Collect data for AI analysis
        tools_used = []
        collected_data = []

        for result in successful_results:
            tool_name = result["tool"]
            tools_used.append(tool_name)

            if result["response"]:
                service_type = "Gmail" if tool_name.startswith('gmail') else \
                             "Calendar" if tool_name.startswith('calendar') else \
                             "Drive" if tool_name.startswith('drive') else "Unknown"
                collected_data.append({
                    "service": service_type,
                    "tool": tool_name,
                    "data": result["response"]
                })

        if not collected_data:
            return {
                "success": False,
                "response": "The Google services returned empty results."
            }

        # Use AI to analyze and respond to the user's question with the collected data
        try:
            logger.debug(f"🤖 Starting AI analysis for user question: '{user_message}'")
            logger.debug(f"🤖 Collected data items: {len(collected_data)}")

            analysis_prompt = f"""
User Question: {user_message}

Retrieved Data from Google Services:
{chr(10).join([f"{item['service']}: {item['data']}" for item in collected_data])}

Please analyze the retrieved data and provide a helpful, concise answer to the user's question. Focus on:
1. Directly answering what the user asked
2. Summarizing key information rather than listing raw data
3. Being conversational and helpful
4. Highlighting important dates, names, or action items if relevant

CRITICAL: When URLs or links are provided in the data, you MUST include them EXACTLY as provided. NEVER truncate, shorten, or summarize URLs. Always show complete clickable links.

Respond as if you're having a natural conversation with the user."""

            # Call the responses API for analysis
            analysis_messages = [
                {"role": "system", "content": analysis_prompt},
                {"role": "user", "content": "Please analyze and summarize this information to answer the user's question."}
            ]

            logger.debug(f"🤖 Calling AI analysis API with {len(analysis_messages)} messages")
            analysis_result = await chat_api_client.call_responses_api(
                messages=analysis_messages,
                user_id=user_id
            )
            logger.debug(f"🤖 AI analysis result: {analysis_result}")

            # Extract the AI analysis text from the correct response field
            if analysis_result and analysis_result.get("output"):
                # Handle the nested response structure: output[0]['content'][0]['text']
                output = analysis_result.get("output", [])
                if output and len(output) > 0:
                    content = output[0].get("content", [])
                    if content and len(content) > 0:
                        final_response = content[0].get("text", "")
                        logger.info(f"✅ Successfully extracted AI analysis: {final_response}")
                    else:
                        final_response = ""
                else:
                    final_response = ""

            if not final_response and analysis_result and analysis_result.get("output_text"):
                # Fallback for different API response formats
                final_response = analysis_result["output_text"]

            if not final_response:
                # Fallback to basic formatting if AI analysis fails
                response_parts = []
                for item in collected_data:
                    response_parts.append(f"📧 **{item['service']}**: {item['data']}")
                final_response = "\n\n".join(response_parts)

        except Exception as e:
            logger.error(f"❌ Error in AI analysis: {e}")
            # Fallback to basic formatting
            response_parts = []
            for item in collected_data:
                response_parts.append(f"📧 **{item['service']}**: {item['data']}")
            final_response = "\n\n".join(response_parts)

        return {
            "success": True,
            "response": final_response,
            "tools_used": tools_used,
            "sources": []
        }

    except Exception as e:
        logger.error(f"❌ Error in handle_google_mcp_request: {e}")
        return {
            "success": False,
            "response": f"Error accessing Google services: {str(e)}"
        }


def extract_gmail_search_query(user_message: str) -> str:
    """Extract search query from user message for Gmail search.

    Parses natural language user messages to extract meaningful search terms
    for Gmail queries. Uses pattern matching to identify common search patterns
    (e.g., "emails about X", "find emails from Y") and strips common prefixes
    to produce clean search queries.

    Args:
        user_message (str): The user's natural language message containing a
            search request. Can be in various formats like "find emails about X",
            "show me messages from Y", etc.

    Returns:
        str: Extracted search query string, limited to 100 characters. Returns
            the cleaned search terms without common prefixes like "show me",
            "find", "search", etc.

    Example:
        >>> extract_gmail_search_query("find emails about project deadline")
        'project deadline'
        >>> extract_gmail_search_query("emails from john@example.com")
        'john@example.com'
    """
    message_lower = user_message.lower()

    # Look for common search patterns
    search_patterns = [
        r'emails? about (.+)',
        r'find emails? (.+)',
        r'search for (.+)',
        r'emails? from (.+)',
        r'messages? about (.+)',
    ]

    for pattern in search_patterns:
        match = re.search(pattern, message_lower)
        if match:
            return match.group(1).strip()

    # Fallback: use the whole message but remove common prefixes
    query = message_lower
    prefixes_to_remove = [
        'show me', 'find', 'search', 'get', 'emails about', 'messages about',
        'my emails', 'my messages', 'emails', 'messages'
    ]

    for prefix in prefixes_to_remove:
        if query.startswith(prefix):
            query = query[len(prefix):].strip()
            break

    return query[:100]  # Limit query length

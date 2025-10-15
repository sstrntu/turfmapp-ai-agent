"""
Chat Tool Handler - Tool Execution and Google MCP Integration

This module handles all tool-related functionality for the chat service, including:
- Google MCP tool integration (Gmail, Drive, Calendar)
- AI-driven tool selection and execution
- Function call parsing and result handling
- Tool availability checking and permission management

Architecture:
- Integrates with ChatApiClient for AI-driven tool selection
- Uses google_mcp_client for Google service tool execution
- Supports parallel tool execution
- Provides intelligent fallback behavior
"""

from __future__ import annotations

import json
import logging
import re
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class ChatToolHandler:
    """Handler for chat tool execution and Google MCP integration."""

    def __init__(self, chat_api_client):
        """Initialize the ChatToolHandler with required dependencies.

        Sets up the tool handler with a ChatApiClient instance that will be used
        for AI-driven tool selection and function calling capabilities.

        Args:
            chat_api_client: ChatApiClient instance that provides access to the
                AI API for tool selection and message processing. Must support
                call_responses_api method for function calling.

        Returns:
            None

        Example:
            >>> from app.services.chat_api_client import ChatApiClient
            >>> api_client = ChatApiClient()
            >>> handler = ChatToolHandler(api_client)
        """
        self.chat_api_client = chat_api_client

    def build_google_function_tools(self, enabled_tools: Dict[str, bool]) -> List[Dict[str, Any]]:
        """Build function tool definitions for enabled Google services.

        Constructs a list of function tool definitions based on which Google services
        are enabled. Each service (Gmail, Calendar, Drive) provides multiple tool
        definitions with their parameters and descriptions for AI function calling.

        Args:
            enabled_tools (Dict[str, bool]): Dictionary mapping service names to their
                enabled state. Supported keys are 'gmail', 'calendar', and 'drive'.
                Example: {'gmail': True, 'calendar': False, 'drive': True}

        Returns:
            List[Dict[str, Any]]: List of tool definitions in the format expected by
                AI function calling APIs. Each tool definition includes:
                - type: Always 'function'
                - function: Object containing name, description, and parameters
                Returns empty list if no tools are enabled.

        Example:
            >>> handler = ChatToolHandler(api_client)
            >>> tools = handler.build_google_function_tools({'gmail': True, 'drive': False})
            >>> len(tools)  # Returns number of Gmail tools
            4
        """
        available_tools: List[Dict[str, Any]] = []

        if not enabled_tools:
            return available_tools

        if enabled_tools.get("gmail"):
            available_tools.extend([
                {
                    "type": "function",
                    "function": {
                        "name": "gmail_recent",
                        "description": "Get the most recent Gmail messages in chronological order. Use this when users ask about 'latest', 'recent', 'first', 'newest', or 'last' emails. Perfect for questions like 'what is my first email about?' or 'show me my latest message'. This tool retrieves emails by recency, not by search criteria.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "max_results": {
                                    "type": "integer",
                                    "description": "Number of emails to retrieve. Use 1 for 'first/latest/newest', 3-5 for 'recent emails', up to 10 for broader requests.",
                                    "default": 5,
                                    "minimum": 1,
                                    "maximum": 50,
                                }
                            },
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "gmail_search",
                        "description": "Search Gmail messages using specific queries. Use this when users want to find emails about specific topics, from specific people, or containing certain keywords. Do NOT use for recent/latest emails - use gmail_recent instead. Perfect for 'find emails from John', 'emails about project', or 'messages containing meeting'.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "Gmail search query. Extract the main search terms from user's request. For 'emails from John' use 'John', for 'about project deadline' use 'project deadline'.",
                                },
                                "max_results": {
                                    "type": "integer",
                                    "description": "Number of emails to retrieve",
                                    "default": 10,
                                    "minimum": 1,
                                    "maximum": 50,
                                },
                            },
                            "required": ["query"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "gmail_get_message",
                        "description": "Retrieve the full content of a specific Gmail message. Use when the user references a particular email and needs the details.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "message_id": {
                                    "type": "string",
                                    "description": "Gmail message ID to retrieve",
                                },
                            },
                            "required": ["message_id"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "gmail_important",
                        "description": "List important or starred Gmail messages. Use when the user requests important, starred, or priority emails.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "max_results": {
                                    "type": "integer",
                                    "description": "Number of important emails to retrieve",
                                    "default": 5,
                                    "minimum": 1,
                                    "maximum": 50,
                                }
                            },
                        },
                    },
                },
            ])

        if enabled_tools.get("calendar"):
            available_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": "calendar_upcoming_events",
                        "description": "Get upcoming calendar events and meetings. Use for scheduling questions, meeting inquiries, or calendar requests.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "max_results": {"type": "integer", "default": 5}
                            },
                        },
                    },
                }
            )
            available_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": "calendar_list_events",
                        "description": "List Google Calendar events from a specific calendar. Use when the user asks about events on a certain calendar or timeframe.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "calendar_id": {
                                    "type": "string",
                                    "description": "Calendar ID to list events from",
                                    "default": "primary",
                                },
                                "max_results": {
                                    "type": "integer",
                                    "description": "Number of events to list",
                                    "default": 10,
                                    "minimum": 1,
                                    "maximum": 50,
                                },
                            },
                        },
                    },
                }
            )

        if enabled_tools.get("drive"):
            available_tools.extend([
                {
                    "type": "function",
                    "function": {
                        "name": "drive_list_files",
                        "description": "List files in Google Drive. Use when users ask about their files, documents, or Drive content. Returns up to the requested number of files with metadata.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "Optional Drive search query to filter results",
                                },
                                "max_results": {
                                    "type": "integer",
                                    "description": "Number of files to list",
                                    "default": 10,
                                    "minimum": 1,
                                    "maximum": 50,
                                },
                            },
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "drive_search",
                        "description": "Advanced search for files in Google Drive with filters for content, file type, and year. Perfect for queries like 'photos of Team A in 2022' or 'documents about project'.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "search_term": {
                                    "type": "string",
                                    "description": "Search term for file names or content",
                                },
                                "file_type": {
                                    "type": "string",
                                    "description": "File type filter such as 'documents', 'images', or exact mime type",
                                },
                                "year": {
                                    "type": "string",
                                    "description": "Optional year filter (e.g., '2024')",
                                },
                                "max_results": {
                                    "type": "integer",
                                    "description": "Number of files to return",
                                    "default": 10,
                                    "minimum": 1,
                                    "maximum": 50,
                                },
                            },
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "drive_search_folders",
                        "description": "Search for folders in Google Drive by name. Use when the user is looking for a specific folder or directory.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "folder_name": {
                                    "type": "string",
                                    "description": "Name of the folder to search for",
                                },
                                "max_results": {
                                    "type": "integer",
                                    "description": "Number of folders to return",
                                    "default": 10,
                                    "minimum": 1,
                                    "maximum": 50,
                                },
                            },
                            "required": ["folder_name"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "drive_list_folder_files",
                        "description": "List files in a specific Google Drive folder. Use when the user references a known folder.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "folder_path": {
                                    "type": "string",
                                    "description": "Drive folder path to list files from",
                                },
                                "max_results": {
                                    "type": "integer",
                                    "description": "Number of files to return",
                                    "default": 10,
                                    "minimum": 1,
                                    "maximum": 50,
                                },
                            },
                            "required": ["folder_path"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "drive_create_folder",
                        "description": "Create a folder structure in Google Drive. Use when the user explicitly asks to create folders or organize files.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "folder_path": {
                                    "type": "string",
                                    "description": "Folder path to create (supports nested paths)",
                                },
                                "root_folder": {
                                    "type": "string",
                                    "description": "Optional root folder override",
                                    "default": "TURFMAPP",
                                },
                            },
                            "required": ["folder_path"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "drive_shared_drives",
                        "description": "List shared drives (Team Drives) that the user can access. Use when they ask about shared or team drives.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "max_results": {
                                    "type": "integer",
                                    "description": "Number of shared drives to list",
                                    "default": 10,
                                    "minimum": 1,
                                    "maximum": 50,
                                },
                            },
                        },
                    },
                },
            ])

        return available_tools

    async def handle_google_mcp_request(
        self,
        user_message: str,
        conversation_history: List[Dict[str, Any]],
        user_id: str,
        enabled_tools: Dict[str, bool],
        **kwargs
    ) -> Dict[str, Any]:
        """Handle Google MCP request using AI-driven tool selection.

        Processes user requests for Google services by:
        1. Building available tool definitions based on enabled services
        2. Using AI to select the most appropriate tool(s) for the user's request
        3. Executing the selected tools via the Google MCP client
        4. Analyzing and summarizing results with AI
        5. Providing intelligent fallback responses when tools aren't enabled

        The function supports parallel tool execution and provides contextual
        suggestions when required tools are not enabled.

        Args:
            user_message (str): The user's natural language request or question.
            conversation_history (List[Dict[str, Any]]): Previous messages in the
                conversation for context. Each message should have 'role' and 'content'.
            user_id (str): Unique identifier for the user making the request. Used
                for authentication with Google services.
            enabled_tools (Dict[str, bool]): Dictionary of enabled Google services.
                Keys: 'gmail', 'calendar', 'drive'. Values: True if enabled.
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
            >>> result = await handler.handle_google_mcp_request(
            ...     user_message="What's my latest email?",
            ...     conversation_history=[],
            ...     user_id="user123",
            ...     enabled_tools={'gmail': True, 'calendar': False, 'drive': False}
            ... )
            >>> result['success']
            True
        """
        try:
            # Create function definitions for available tools based on enabled_tools
            available_tools = self.build_google_function_tools(enabled_tools)

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

            tool_selection_result = await self.chat_api_client.call_responses_api(
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
                    logger.debug(f"🔄 Returning folder search result directly without AI analysis")
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
                analysis_result = await self.chat_api_client.call_responses_api(
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

    def extract_gmail_search_query(self, user_message: str) -> str:
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
            >>> handler.extract_gmail_search_query("find emails about project deadline")
            'project deadline'
            >>> handler.extract_gmail_search_query("emails from john@example.com")
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

    async def handle_tool_calls(self, user_id: str, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Handle tool calls from the AI assistant with MCP integration.

        Processes a list of tool calls generated by the AI assistant, routing each
        call to the appropriate execution backend:
        - Google MCP client for Google services (Gmail, Drive, Calendar)
        - Traditional tool manager for other tools

        Ensures the MCP client is connected before executing Google tools and
        handles errors gracefully by returning error results instead of raising
        exceptions.

        Args:
            user_id (str): Unique identifier for the user making the request. Used
                for authentication and authorization with tool backends.
            tool_calls (List[Dict[str, Any]]): List of tool call dictionaries from
                the AI assistant. Each should contain:
                - id: Unique identifier for the tool call
                - function: Dict with 'name' and 'arguments' (string or dict)

        Returns:
            List[Dict[str, Any]]: List of tool execution results. Each result contains:
                - tool_call_id (str): The ID of the tool call
                - tool_name (str): Name of the executed tool
                - result (Dict[str, Any]): Execution result with 'success' and either
                  'response' or 'error' fields

        Raises:
            Does not raise exceptions. All errors are caught and returned as error
            results in the output list.

        Example:
            >>> tool_calls = [{
            ...     'id': 'call_123',
            ...     'function': {
            ...         'name': 'gmail_recent',
            ...         'arguments': '{"max_results": 5}'
            ...     }
            ... }]
            >>> results = await handler.handle_tool_calls('user123', tool_calls)
            >>> results[0]['result']['success']
            True
        """
        tool_results = []

        # Import here to avoid circular dependency
        from .mcp_client import google_mcp_client
        from .tool_manager import tool_manager

        for tool_call in tool_calls:
            try:
                tool_name = tool_call.get("function", {}).get("name")
                tool_args = tool_call.get("function", {}).get("arguments", "{}")

                # Parse arguments
                if isinstance(tool_args, str):
                    tool_args = json.loads(tool_args)

                # Check if this is a Google MCP tool
                google_tools = [
                    "gmail_search", "gmail_get_message", "gmail_recent", "gmail_important",
                    "drive_list_files", "drive_create_folder", "drive_list_folder_files", "drive_shared_drives", "drive_search", "drive_search_folders",
                    "calendar_list_events", "calendar_upcoming_events"
                ]

                if tool_name in google_tools:
                    # Use MCP client for Google services
                    logger.debug(f"🔧 Using MCP client for tool: {tool_name}")
                    logger.debug(f"🔧 Tool arguments: {tool_args}")
                    logger.debug(f"🔧 User ID: {user_id}")
                    try:
                        # Ensure MCP client is connected
                        await google_mcp_client.connect()

                        # Add user_id to arguments for MCP
                        tool_args["user_id"] = user_id
                        logger.debug(f"🔧 Final tool arguments: {tool_args}")

                        # Execute via MCP
                        result = await google_mcp_client.call_tool(tool_name, tool_args)

                        logger.debug(f"🔧 MCP result for {tool_name}: {result}")

                        # Special debug logging for folder search
                        if tool_name == "drive_search_folders" and result.get("success"):
                            logger.debug(f"🔍 FOLDER SEARCH RESULT: {result.get('response', 'No response')[:500]}")
                            if len(result.get('response', '')) > 500:
                                logger.debug(f"🔍 FOLDER SEARCH (continued): {result.get('response', '')[500:]}")

                    except Exception as e:
                        logger.error(f"❌ MCP tool execution failed for {tool_name}: {e}")
                        import traceback
                        traceback.print_exc()
                        result = {
                            "success": False,
                            "error": f"MCP tool execution failed: {str(e)}"
                        }

                else:
                    # Use traditional tool manager for non-Google tools
                    logger.debug(f"🔧 Using traditional tool manager for: {tool_name}")
                    result = await tool_manager.execute_tool(tool_name, user_id, **tool_args)

                tool_results.append({
                    "tool_call_id": tool_call.get("id"),
                    "tool_name": tool_name,
                    "result": result
                })

            except Exception as e:
                logger.error(f"❌ Tool execution failed for {tool_name}: {e}")
                tool_results.append({
                    "tool_call_id": tool_call.get("id"),
                    "tool_name": tool_call.get("function", {}).get("name", "unknown"),
                    "result": {
                        "success": False,
                        "error": f"Tool execution failed: {str(e)}"
                    }
                })

        return tool_results


# Global instance for convenience
chat_tool_handler = None  # Will be initialized after ChatApiClient is available

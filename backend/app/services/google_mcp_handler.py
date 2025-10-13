"""
Google MCP Handler Module

Handles all Google MCP (Model Context Protocol) related operations including:
- Tool selection and execution for Gmail, Calendar, and Drive
- AI-driven tool selection
- Parameter extraction and validation
- Response formatting and aggregation

Extracted from chat_service.py to improve maintainability and separation of concerns.
"""

from __future__ import annotations

import logging
import json
from typing import List, Dict, Any

from .mcp_client import google_mcp_client

logger = logging.getLogger(__name__)


class GoogleMCPHandler:
    """Handles Google MCP tool selection and execution."""
    
    def __init__(self, call_responses_api_func):
        """
        Initialize handler with reference to API call function.
        
        Args:
            call_responses_api_func: Function to call the Responses API
        """
        self.call_responses_api = call_responses_api_func
    
    def get_available_tools(self, enabled_tools: Dict[str, bool]) -> List[Dict[str, Any]]:
        """
        Build list of available tools based on enabled services.
        
        Args:
            enabled_tools: Dictionary of enabled tool flags (gmail, calendar, drive)
            
        Returns:
            List of tool definitions in OpenAI function format
        """
        available_tools = []
        
        if enabled_tools.get('gmail'):
            available_tools.extend(self._get_gmail_tools())
        
        if enabled_tools.get('calendar'):
            available_tools.extend(self._get_calendar_tools())
        
        if enabled_tools.get('drive'):
            available_tools.extend(self._get_drive_tools())
        
        return available_tools
    
    def _get_gmail_tools(self) -> List[Dict[str, Any]]:
        """Get Gmail tool definitions."""
        return [
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
                                "maximum": 50
                            }
                        }
                    }
                }
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
                                "description": "Gmail search query. Extract the main search terms from user's request. For 'emails from John' use 'John', for 'about project deadline' use 'project deadline'."
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Number of emails to retrieve",
                                "default": 10,
                                "minimum": 1,
                                "maximum": 50
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]
    
    def _get_calendar_tools(self) -> List[Dict[str, Any]]:
        """Get Calendar tool definitions."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "calendar_upcoming_events",
                    "description": "Get upcoming calendar events and meetings. Use for scheduling questions, meeting inquiries, or calendar requests.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "max_results": {"type": "integer", "default": 5}
                        }
                    }
                }
            }
        ]
    
    def _get_drive_tools(self) -> List[Dict[str, Any]]:
        """Get Drive tool definitions."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "drive_list_files",
                    "description": "List files in Google Drive. Use for file-related questions or document requests.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "max_results": {"type": "integer", "default": 10}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "drive_shared_drives",
                    "description": "List shared drives (Team Drives) that the user has access to. Use when user asks about shared drives, team drives, or organizational drives.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "max_results": {"type": "integer", "default": 10}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "drive_search",
                    "description": "Advanced search for FILES (not folders) in Google Drive with filters for content, file type, and year. Perfect for queries like 'photos of Team A in 2022' or 'documents about project'. Returns clickable links to files. Do NOT use for folder searches - use drive_search_folders instead.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "search_term": {"type": "string", "description": "Search term to look for in file names and content"},
                            "file_type": {"type": "string", "description": "File type filter: 'photos/images', 'documents', 'videos', 'folders'"},
                            "year": {"type": "string", "description": "Year filter (e.g., '2022')"},
                            "max_results": {"type": "integer", "default": 10}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "drive_search_folders",
                    "description": "Search ONLY for folders/directories in Google Drive by name. Use when user asks for 'folder', 'directory', mentions a folder name, or when the item they're looking for is known to be a folder (like episode folders, project folders, etc). Returns clickable folder links. ALWAYS use this instead of drive_search when looking for folders.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "folder_name": {"type": "string", "description": "Name of the folder to search for"},
                            "max_results": {"type": "integer", "default": 10}
                        }
                    }
                }
            }
        ]
    
    def get_no_tools_response(self, user_message: str) -> Dict[str, Any]:
        """
        Generate intelligent response when no tools are enabled.
        
        Args:
            user_message: User's message
            
        Returns:
            Response dict with suggested tools
        """
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
            return {
                "success": False,
                "response": "No Google tools were enabled. Please enable the tools you'd like to use (Gmail 📧, Calendar 📅, or Drive 📁) in the interface."
            }
    
    async def execute_tool_calls(
        self,
        function_calls: List[Dict[str, Any]],
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Execute list of tool calls.
        
        Args:
            function_calls: List of function call definitions
            user_id: User ID for authentication
            
        Returns:
            List of tool execution results
        """
        tool_results = []
        
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
                
                logger.debug(f"Calling {tool_name} with params: {params}")
                result = await google_mcp_client.call_tool(tool_name, params)
                
                logger.debug(f"Raw result from {tool_name}: {result}")
                
                tool_results.append({
                    "tool": tool_name,
                    "success": result.get("success", False) if isinstance(result, dict) else False,
                    "response": result.get("response", "") if isinstance(result, dict) else str(result),
                    "error": result.get("error") if isinstance(result, dict) else None
                })
                
                # Special debug logging for folder search
                if tool_name == "drive_search_folders" and result.get("success"):
                    logger.debug(f"Folder search result: {result.get('response', 'No response')[:500]}")
                    if len(result.get('response', '')) > 500:
                        logger.debug(f"Folder search (continued): {result.get('response', '')[500:]}")
                
            except Exception as e:
                logger.error(f"Error calling {tool_name}: {e}", exc_info=True)
                tool_results.append({
                    "tool": tool_name,
                    "success": False,
                    "response": "",
                    "error": str(e)
                })
        
        return tool_results
    
    async def handle_fallback_tools(
        self,
        user_message: str,
        enabled_tools: Dict[str, bool],
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Handle fallback tool execution when AI doesn't make function calls.
        
        Args:
            user_message: User's message
            enabled_tools: Enabled tool flags
            user_id: User ID
            
        Returns:
            List of tool results
        """
        logger.debug("No function calls detected, using fallback logic")
        tool_results = []
        
        # Gmail fallback
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
                logger.error(f"Fallback error: {e}", exc_info=True)
                tool_results.append({
                    "tool": "gmail_recent",
                    "success": False,
                    "response": "",
                    "error": str(e)
                })
        
        # Drive fallback
        elif enabled_tools.get('drive'):
            user_msg_lower = user_message.lower()
            
            # Detect folder search vs general file search
            if any(word in user_msg_lower for word in ['folder', 'directory']):
                words = [w for w in user_message.split() if w not in ['find', 'the', 'folder', 'directory', 'get', 'me']]
                folder_name = ' '.join(words) if words else ""
                
                params = {"user_id": user_id, "folder_name": folder_name, "max_results": 10}
                drive_tool = "drive_search_folders"
            else:
                params = {"user_id": user_id, "max_results": 10}
                drive_tool = "drive_list_files"
            
            logger.debug(f"Drive fallback: using {drive_tool}")
            
            try:
                result = await google_mcp_client.call_tool(drive_tool, params)
                tool_results.append({
                    "tool": drive_tool,
                    "success": result.get("success", False) if isinstance(result, dict) else False,
                    "response": result.get("response", "") if isinstance(result, dict) else str(result),
                    "error": result.get("error") if isinstance(result, dict) else None
                })
            except Exception as e:
                logger.error(f"Drive fallback error: {e}", exc_info=True)
                tool_results.append({
                    "tool": drive_tool,
                    "success": False,
                    "response": "",
                    "error": str(e)
                })
        
        return tool_results
    
    def parse_function_calls(self, api_response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse function calls from API response.
        
        Args:
            api_response: Response from call_responses_api
            
        Returns:
            List of parsed function calls
        """
        function_calls = []
        output_items = api_response.get("output", [])
        
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
        
        logger.debug(f"Parsed {len(function_calls)} function calls")
        return function_calls
    
    async def analyze_with_ai(
        self,
        user_message: str,
        collected_data: List[Dict[str, Any]],
        user_id: str
    ) -> str:
        """
        Use AI to analyze collected data and generate response.
        
        Args:
            user_message: Original user question
            collected_data: Data collected from tools
            user_id: User ID
            
        Returns:
            AI-generated response text
        """
        try:
            logger.debug(f"Starting AI analysis for user question: '{user_message}'")
            logger.debug(f"Collected data items: {len(collected_data)}")
            
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

            analysis_messages = [
                {"role": "system", "content": analysis_prompt},
                {"role": "user", "content": "Please analyze and summarize this information to answer the user's question."}
            ]
            
            logger.debug(f"Calling AI analysis API with {len(analysis_messages)} messages")
            analysis_result = await self.call_responses_api(
                messages=analysis_messages,
                user_id=user_id
            )
            logger.debug(f"AI analysis result: {analysis_result}")
            
            # Extract AI analysis text from response
            if analysis_result and analysis_result.get("output"):
                output = analysis_result.get("output", [])
                if output and len(output) > 0:
                    content = output[0].get("content", [])
                    if content and len(content) > 0:
                        final_response = content[0].get("text", "")
                        logger.info(f"Successfully extracted AI analysis")
                        return final_response
            
            if analysis_result and analysis_result.get("output_text"):
                return analysis_result["output_text"]
            
            # Fallback to basic formatting
            response_parts = []
            for item in collected_data:
                response_parts.append(f"📧 **{item['service']}**: {item['data']}")
            return "\n\n".join(response_parts)
            
        except Exception as e:
            logger.error(f"Error in AI analysis: {e}", exc_info=True)
            # Fallback to basic formatting
            response_parts = []
            for item in collected_data:
                response_parts.append(f"📧 **{item['service']}**: {item['data']}")
            return "\n\n".join(response_parts)
    
    async def handle_google_mcp_request(
        self,
        user_message: str,
        conversation_history: List[Dict[str, Any]],
        user_id: str,
        enabled_tools: Dict[str, bool],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Handle Google MCP request using AI-driven tool selection.
        
        Args:
            user_message: User's message
            conversation_history: Previous conversation messages
            user_id: User ID
            enabled_tools: Dictionary of enabled tools (gmail, calendar, drive)
            **kwargs: Additional arguments
            
        Returns:
            Response dictionary with success status, response text, and metadata
        """
        try:
            # Get available tools based on what's enabled
            available_tools = self.get_available_tools(enabled_tools)
            
            if not available_tools:
                return self.get_no_tools_response(user_message)
            
            # Use AI to select and call appropriate tools
            logger.debug(f"Using AI-driven tool selection with {len(available_tools)} available tools")
            
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

            messages = [
                {"role": "system", "content": tool_selection_prompt},
                {"role": "user", "content": user_message}
            ]
            
            tool_selection_result = await self.call_responses_api(
                messages=messages,
                tools=available_tools,
                user_id=user_id
            )
            
            logger.debug(f"Tool selection result: {tool_selection_result}")
            
            # Parse function calls from response
            function_calls = self.parse_function_calls(tool_selection_result)
            logger.debug(f"Extracted {len(function_calls)} function calls")
            
            # Execute the selected tools
            tool_results = await self.execute_tool_calls(function_calls, user_id)
            
            # If no function calls were made, use fallback
            if not function_calls and available_tools:
                tool_results = await self.handle_fallback_tools(user_message, enabled_tools, user_id)
            
            # Filter successful results
            successful_results = [r for r in tool_results if r["success"]]
            
            if not successful_results:
                return {
                    "success": False,
                    "response": "I couldn't retrieve data from your Google services. Please check your permissions and try again."
                }
            
            # Special handling for folder searches - return directly
            for result in successful_results:
                if result["tool"] == "drive_search_folders" and result.get("response"):
                    logger.debug("Returning folder search result directly without AI analysis")
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
            
            # Use AI to analyze and respond
            final_response = await self.analyze_with_ai(user_message, collected_data, user_id)
            
            return {
                "success": True,
                "response": final_response,
                "tools_used": tools_used,
                "sources": []
            }
            
        except Exception as e:
            logger.error(f"Error in handle_google_mcp_request: {e}", exc_info=True)
            return {
                "success": False,
                "response": f"Error accessing Google services: {str(e)}"
            }

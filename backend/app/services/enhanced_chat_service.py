"""
Enhanced Chat Service - Core Business Logic for AI Chat Operations

This service provides the primary business logic for chat functionality, including:
- Multi-model AI integration (GPT-4O, O1, GPT-5-mini via OpenAI Responses API)  
- Conversation management with persistent storage
- Sources extraction and metadata enrichment
- Database fallback patterns for resilience
- Response parsing and error handling

Architecture:
- Service layer pattern separating business logic from API endpoints
- Database-first with in-memory fallback for development/testing
- Async operations for performance with external API calls
- Comprehensive error handling and graceful degradation

Recent improvements (August 2025):
- Fixed sources extraction and metadata preservation
- Enhanced GPT-5-mini support with 4000 token limit
- Improved incomplete response handling
- Auto-generated conversation titles from first message
"""

from __future__ import annotations

import os
import asyncio
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import httpx

from ..database import ConversationService, UserService
from ..utils.chat_utils import stringify_text, extract_sources_from_response, format_chat_history
from ..api.v1.preferences import user_preferences
from .tool_manager import tool_manager
from .mcp_client_simple import google_mcp_client, get_all_google_tools


class EnhancedChatService:
    """Enhanced chat service with comprehensive API integration."""
    
    def __init__(self):
        self.responses_api_key = os.getenv("OPENAI_API_KEY", "")
        self.responses_base_url = "https://api.openai.com/v1/responses"
        
        # Fallback storage for when database fails
        self.fallback_conversations: Dict[str, List[Dict[str, Any]]] = {}
        self.fallback_conversation_metadata: Dict[str, Dict[str, Any]] = {}
    
    async def use_database_fallback(self, func_name: str, *args, **kwargs):
        """Try database operation, fall back to in-memory storage if it fails."""
        try:
            # Get the static method from ConversationService
            method = getattr(ConversationService, func_name)
            if asyncio.iscoroutinefunction(method):
                return await method(*args, **kwargs)
            else:
                return method(*args, **kwargs)
        except Exception as e:
            print(f"Database {func_name} failed: {e}, using fallback")
            return None
    
    async def get_conversation_history(self, conversation_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Retrieve conversation history with fallback support."""
        # Try database first
        db_result = await self.use_database_fallback(
            "get_conversation_messages", conversation_id
        )
        
        if db_result:
            return db_result
        
        # Use fallback storage
        return self.fallback_conversations.get(conversation_id, [])
    
    async def save_message_to_conversation(
        self, 
        conversation_id: str, 
        user_id: str, 
        role: str, 
        content: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Save message with fallback support."""
        try:
            # Try database first
            db_result = await self.use_database_fallback(
                "add_message", 
                conversation_id, 
                role, 
                content, 
                metadata
            )
            
            if db_result:
                return True
        except Exception as e:
            print(f"Database save failed: {e}")
        
        # Use fallback storage
        if conversation_id not in self.fallback_conversations:
            self.fallback_conversations[conversation_id] = []
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        self.fallback_conversations[conversation_id].append(message)
        return True
    
    async def create_conversation(self, user_id: str, title: Optional[str] = None) -> str:
        """Create new conversation with fallback support."""
        conversation_id = str(uuid.uuid4())
        
        try:
            # Try database first
            db_result = await self.use_database_fallback(
                "create_conversation", user_id, title
            )
            
            if db_result:
                return str(db_result.get("id", conversation_id))
        except Exception as e:
            print(f"Database create conversation failed: {e}")
        
        # Use fallback storage
        self.fallback_conversation_metadata[conversation_id] = {
            "user_id": user_id,
            "title": title or "New Conversation",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        self.fallback_conversations[conversation_id] = []
        return conversation_id
    
    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user preferences for chat configuration."""
        return user_preferences.get(user_id, {
            "model": "gpt-4o",
            "include_reasoning": False,
            "text_format": "text",
            "text_verbosity": "medium",
            "reasoning_effort": "medium"
        })
    
    async def _handle_google_mcp_request(
        self,
        user_message: str,
        conversation_history: List[Dict[str, Any]],
        user_id: str,
        enabled_tools: Dict[str, bool],
        **kwargs
    ) -> Dict[str, Any]:
        """Handle Google MCP request using AI-driven tool selection."""
        try:
            # Create function definitions for available tools based on enabled_tools
            available_tools = []
            
            if enabled_tools.get('gmail'):
                # Gmail tools with rich descriptions
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
                ])
            
            if enabled_tools.get('calendar'):
                available_tools.append({
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
                })
                
            if enabled_tools.get('drive'):
                available_tools.append({
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
                })
            
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
            print(f"🤖 Using AI-driven tool selection with {len(available_tools)} available tools")
            
            # Get Google MCP client
            from .mcp_client_simple import google_mcp_client
            
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
            
            tool_selection_result = await self.call_responses_api(
                messages=messages,
                tools=available_tools,
                user_id=user_id
            )
            
            print(f"🤖 Tool selection result: {tool_selection_result}")
            
            # Extract function calls from the response
            import json
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
            
            print(f"🤖 Function calls parsed: {function_calls}")
            
            print(f"🤖 Extracted {len(function_calls)} function calls")
            
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
                    
                    print(f"🔧 Calling {tool_name} with params: {params}")
                    result = await google_mcp_client.call_tool(tool_name, params)
                    
                    print(f"🔧 Raw result from {tool_name}: {result}")
                    
                    tool_results.append({
                        "tool": tool_name,
                        "success": result.get("success", False) if isinstance(result, dict) else False,
                        "response": result.get("response", "") if isinstance(result, dict) else str(result),
                        "error": result.get("error") if isinstance(result, dict) else None
                    })
                    
                except Exception as e:
                    print(f"❌ Error calling {tool_name}: {e}")
                    tool_results.append({
                        "tool": tool_name,
                        "success": False,
                        "response": "",
                        "error": str(e)
                    })
            
            # If no function calls were made, fall back to default behavior
            if not function_calls and available_tools:
                print("🔄 No function calls detected, using fallback logic")
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
                        print(f"❌ Fallback error: {e}")
                        tool_results.append({
                            "tool": "gmail_recent", 
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
                print(f"🤖 Starting AI analysis for user question: '{user_message}'")
                print(f"🤖 Collected data items: {len(collected_data)}")
                
                analysis_prompt = f"""
User Question: {user_message}

Retrieved Data from Google Services:
{chr(10).join([f"{item['service']}: {item['data']}" for item in collected_data])}

Please analyze the retrieved data and provide a helpful, concise answer to the user's question. Focus on:
1. Directly answering what the user asked
2. Summarizing key information rather than listing raw data
3. Being conversational and helpful
4. Highlighting important dates, names, or action items if relevant

Respond as if you're having a natural conversation with the user."""

                # Call the responses API for analysis
                analysis_messages = [
                    {"role": "system", "content": analysis_prompt},
                    {"role": "user", "content": "Please analyze and summarize this information to answer the user's question."}
                ]
                
                print(f"🤖 Calling AI analysis API with {len(analysis_messages)} messages")
                analysis_result = await self.call_responses_api(
                    messages=analysis_messages,
                    user_id=user_id
                )
                print(f"🤖 AI analysis result: {analysis_result}")
                
                # Extract the AI analysis text from the correct response field
                if analysis_result and analysis_result.get("output"):
                    # Handle the nested response structure: output[0]['content'][0]['text']
                    output = analysis_result.get("output", [])
                    if output and len(output) > 0:
                        content = output[0].get("content", [])
                        if content and len(content) > 0:
                            final_response = content[0].get("text", "")
                            print(f"✅ Successfully extracted AI analysis: {final_response}")
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
                print(f"❌ Error in AI analysis: {e}")
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
            print(f"❌ Error in _handle_google_mcp_request: {e}")
            return {
                "success": False,
                "response": f"Error accessing Google services: {str(e)}"
            }
    
    def _extract_gmail_search_query(self, user_message: str) -> str:
        """Extract search query from user message for Gmail search."""
        message_lower = user_message.lower()
        
        # Look for common search patterns
        search_patterns = [
            r'emails? about (.+)',
            r'find emails? (.+)',
            r'search for (.+)',
            r'emails? from (.+)',
            r'messages? about (.+)',
        ]
        
        import re
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
        """Handle tool calls from the AI assistant with MCP integration."""
        tool_results = []
        
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
                    "drive_list_files", "drive_create_folder", "drive_list_folder_files",
                    "calendar_list_events", "calendar_upcoming_events"
                ]
                
                if tool_name in google_tools:
                    # Use MCP client for Google services
                    print(f"🔧 Using MCP client for tool: {tool_name}")
                    print(f"🔧 Tool arguments: {tool_args}")
                    print(f"🔧 User ID: {user_id}")
                    try:
                        # Ensure MCP client is connected
                        await google_mcp_client.connect()
                        
                        # Add user_id to arguments for MCP
                        tool_args["user_id"] = user_id
                        print(f"🔧 Final tool arguments: {tool_args}")
                        
                        # Execute via MCP
                        result = await google_mcp_client.call_tool(tool_name, tool_args)
                        
                        print(f"🔧 MCP result for {tool_name}: {result}")
                        
                    except Exception as e:
                        print(f"❌ MCP tool execution failed for {tool_name}: {e}")
                        import traceback
                        traceback.print_exc()
                        result = {
                            "success": False,
                            "error": f"MCP tool execution failed: {str(e)}"
                        }
                
                else:
                    # Use traditional tool manager for non-Google tools
                    print(f"🔧 Using traditional tool manager for: {tool_name}")
                    result = await tool_manager.execute_tool(tool_name, user_id, **tool_args)
                
                tool_results.append({
                    "tool_call_id": tool_call.get("id"),
                    "tool_name": tool_name,
                    "result": result
                })
                
            except Exception as e:
                print(f"❌ Tool execution failed for {tool_name}: {e}")
                tool_results.append({
                    "tool_call_id": tool_call.get("id"),
                    "tool_name": tool_call.get("function", {}).get("name", "unknown"),
                    "result": {
                        "success": False,
                        "error": f"Tool execution failed: {str(e)}"
                    }
                })
        
        return tool_results
    
    async def call_responses_api(
        self, 
        messages: List[Dict[str, Any]], 
        model: str = "gpt-4o",
        include_reasoning: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Call the OpenAI Responses API with proper format."""
        print(f"📡 call_responses_api called with {len(messages)} messages, model={model}")
        headers = {
            "Authorization": f"Bearer {self.responses_api_key}",
            "Content-Type": "application/json"
        }
        
        # Convert messages to conversation context string (Responses API format)
        conversation_context = ""
        
        # Add conversation history
        for i, msg in enumerate(messages[:-1]):  # All but the last message
            role = msg["role"].title()
            conversation_context += f"{role}: {msg['content']}\n\n"
        
        # Emphasize the current user question
        if messages:
            current_msg = messages[-1]
            if current_msg.get("role") == "user":
                conversation_context += f"CURRENT USER QUESTION: {current_msg['content']}\n\n"
            else:
                role = current_msg["role"].title()
                conversation_context += f"{role}: {current_msg['content']}\n\n"
        
        # Build payload for Responses API
        # GPT-5-mini needs more tokens for web search and reasoning
        default_tokens = 4000 if model == "gpt-5-mini" else 1500
        payload = {
            "model": model,
            "input": conversation_context.strip(),
            "max_output_tokens": kwargs.get("max_tokens", default_tokens),
        }
        
        # Add temperature for supported models
        if model not in ["gpt-5-mini"] and "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]
        elif model not in ["gpt-5-mini"]:
            payload["temperature"] = 0.7
        
        # Handle tools properly - Responses API format
        if "tools" in kwargs and kwargs["tools"]:
            tools = kwargs["tools"]
            print(f"🔧 Processing tools in API call: {tools}")
            # Filter out invalid string-based tools
            if isinstance(tools, list) and tools:
                if isinstance(tools[0], str):
                    print(f"⚠️ Removing invalid tools format: {tools}")
                else:
                    # Convert from Chat Completions format to Responses API format
                    responses_api_tools = []
                    for tool in tools[:5]:  # Limit to 5 tools
                        if tool.get("type") == "function":
                            func = tool.get("function", {})
                            responses_tool = {
                                "type": "function",
                                "name": func.get("name"),
                                "description": func.get("description"),
                                "parameters": func.get("parameters", {})
                            }
                            responses_api_tools.append(responses_tool)
                        elif tool.get("type") == "web_search_preview":
                            # Handle web search tools for Responses API
                            web_search_tool = {
                                "type": "web_search_preview",
                                "user_location": tool.get("user_location", {"type": "approximate"}),
                                "search_context_size": tool.get("search_context_size", "medium")
                            }
                            responses_api_tools.append(web_search_tool)
                            print(f"🌐 Added web search tool to Responses API payload")
                        elif tool.get("type") == "image_generation":
                            # Handle image generation tools for Responses API
                            image_gen_tool = {
                                "type": "image_generation",
                                "size": tool.get("size", "auto"),
                                "quality": tool.get("quality", "auto"),
                                "output_format": tool.get("output_format", "png"),
                                "background": tool.get("background", "auto"),
                                "moderation": tool.get("moderation", "auto"),
                                "partial_images": tool.get("partial_images", 3)
                            }
                            responses_api_tools.append(image_gen_tool)
                            print(f"🎨 Added image generation tool to Responses API payload")
                    
                    payload["tools"] = responses_api_tools
                    payload["tool_choice"] = kwargs.get("tool_choice", "auto")
                    payload["parallel_tool_calls"] = True
                    print(f"🔧 Added tools to payload (Responses API format): {payload['tools']}")
        else:
            print(f"🔧 No tools provided in API call")
        
        # Add instructions for additional context
        instructions = []
        
        # Add critical tool usage rule at the top
        instructions.append("""
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
""")
        
        if "developer_instructions" in kwargs and kwargs["developer_instructions"]:
            instructions.append(kwargs["developer_instructions"])
        if "assistant_context" in kwargs and kwargs["assistant_context"]:
            instructions.append(kwargs["assistant_context"])
        
        # Add web search tool instructions if available
        web_search_available = any(tool.get("type") == "web_search_preview" for tool in payload.get("tools", []))
        if web_search_available:
            web_search_instructions = """
You have tools available. Use them when they would provide better, more current information than your training data. Use web search for current information: sports scores, news, weather, current season data, latest facts, or when users ask 'who is', 'what is the latest', 'this season', 'this year'."""
            instructions.append(web_search_instructions)

        # Add Google service tool instructions if available
        google_tools_available = any(tool.get("name", "").startswith(("gmail_", "drive_", "calendar_")) for tool in payload.get("tools", []))
        if google_tools_available:
            google_instructions = f"""
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
"""
            instructions.append(google_instructions)
        
        if instructions:
            payload["instructions"] = "\n\n".join(instructions)
        
        # Add reasoning for o1 models
        if include_reasoning and model in ["o1", "o1-mini", "o1-preview"]:
            payload["reasoning"] = True
        
        try:
            api_timeout = 60.0 if payload.get("tools") else 30.0
            async with httpx.AsyncClient(timeout=httpx.Timeout(api_timeout, connect=15.0)) as client:
                response = await client.post(
                    self.responses_base_url,
                    headers=headers,
                    json=payload
                )
                
                if response.status_code != 200:
                    raise Exception(f"API request failed: {response.status_code} {response.text}")
                
                data = response.json()
                print(f"📡 API response data: {data}")
                
                # Handle async responses (poll for completion)
                status_val = data.get("status")
                response_id = data.get("id")
                
                if status_val in {"in_progress", "queued"} and response_id:
                    attempts_remaining = 8
                    while status_val in {"in_progress", "queued"} and attempts_remaining > 0:
                        await asyncio.sleep(0.25)
                        poll = await client.get(
                            f"https://api.openai.com/v1/responses/{response_id}",
                            headers=headers
                        )
                        if poll.status_code == 200:
                            data = poll.json()
                            status_val = data.get("status")
                        attempts_remaining -= 1
                
                return data
                
        except httpx.HTTPError as e:
            raise Exception(f"API request failed: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error: {e}")
    
    async def process_chat_request(
        self, 
        user_id: str, 
        message: str, 
        conversation_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Process a complete chat request with history and context."""
        # Get or create conversation
        if not conversation_id:
            # Generate title from user's first message (truncate to 50 chars)
            title = message[:50] + "..." if len(message) > 50 else message
            conversation_id = await self.create_conversation(user_id, title)
        
        # Get conversation history
        history = await self.get_conversation_history(conversation_id, user_id)
        
        # Get user preferences
        preferences = self.get_user_preferences(user_id)
        
        # Merge preferences with request parameters
        model = kwargs.get("model", preferences.get("model", "gpt-4o"))
        include_reasoning = kwargs.get("include_reasoning", preferences.get("include_reasoning", False))
        
        # Format messages for API with smart context management
        formatted_history = format_chat_history(history, max_context=20)
        
        # Add current user message
        current_message = {"role": "user", "content": message}
        all_messages = formatted_history + [current_message]
        
        # Save user message first
        await self.save_message_to_conversation(
            conversation_id, user_id, "user", message
        )
        
        # Check if Google MCP tools are explicitly requested
        google_mcp_tools = None
        if 'tools' in kwargs and kwargs['tools']:
            for tool in kwargs['tools']:
                if tool.get('type') == 'google_mcp':
                    google_mcp_tools = tool.get('enabled_tools', {})
                    break
        
        if google_mcp_tools and any(google_mcp_tools.values()):
            print(f"🔧 Google MCP tools explicitly requested: {google_mcp_tools}")
            
            # Handle Google MCP tools directly
            try:
                mcp_result = await self._handle_google_mcp_request(
                    user_message=message,
                    conversation_history=formatted_history,
                    user_id=user_id,
                    enabled_tools=google_mcp_tools,
                    **kwargs
                )
                
                if mcp_result.get("success"):
                    assistant_content = mcp_result.get("response", "")
                    
                    # Save assistant message
                    await self.save_message_to_conversation(
                        conversation_id, user_id, "assistant", assistant_content,
                        {
                            "google_mcp_used": True,
                            "enabled_tools": google_mcp_tools,
                            "tools_used": mcp_result.get("tools_used", []),
                            "model": model
                        }
                    )
                    
                    # Create response messages
                    user_message = {
                        "id": str(uuid.uuid4()),
                        "role": "user", 
                        "content": message,
                        "created_at": datetime.utcnow().isoformat()
                    }
                    
                    assistant_message = {
                        "id": str(uuid.uuid4()),
                        "role": "assistant",
                        "content": assistant_content,
                        "created_at": datetime.utcnow().isoformat()
                    }
                    
                    return {
                        "conversation_id": conversation_id,
                        "user_message": user_message,
                        "assistant_message": assistant_message,
                        "reasoning": None,
                        "sources": mcp_result.get("sources", [])
                    }
                else:
                    print("❌ Google MCP failed, falling back to original behavior")
            except Exception as e:
                print(f"❌ Google MCP error: {e}, falling back to original behavior")

        # Use original behavior - direct API call like the original repo
        print("🚀 Using original behavior - calling Responses API directly")
        
        # Prepare tools for API call (from original repo logic - use web search tools if requested)
        tools_to_include = kwargs.get("tools", [])
        
        # Call API directly (original repo behavior)
        try:
            api_response = await self.call_responses_api(
                messages=all_messages,
                model=model,
                include_reasoning=include_reasoning,
                tools=tools_to_include,
                **{k: v for k, v in kwargs.items() if k not in ["model", "include_reasoning", "tools"]}
            )
            
            # Extract assistant response from Responses API format (original repo logic)
            assistant_content = ""
            reasoning = None
            sources = []  # Initialize sources list
            
            # Parse Responses API output with debugging for GPT-5-mini
            print(f"🔍 API Response for model {model}:", api_response)
            
            # Check if there are any tool calls in the response
            if "tool_calls" in api_response:
                print(f"🔧 Tool calls found in response: {api_response['tool_calls']}")
            else:
                print(f"🔧 No tool calls found in response")
            
            # Check the output structure for function calls
            output_items = api_response.get("output", [])
            print(f"🔧 Output items: {len(output_items) if output_items else 0}")
            
            # Handle function calls from the API response (original repo logic)
            function_calls = []
            for i, item in enumerate(output_items):
                if isinstance(item, dict):
                    item_type = item.get("type")
                    print(f"🔧 Output item {i}: type={item_type}")
                    if item_type == "function_call":
                        print(f"🔧 Function call found: {item}")
                        function_calls.append(item)
                    elif item_type == "tool_call":
                        print(f"🔧 Tool call found: {item}")
                        function_calls.append(item)
                    elif item_type == "message":
                        content = item.get("content", [])
                        print(f"🔧 Message content: {content}")
                        
                        # Extract text from message content and collect annotations
                        if content and isinstance(content, list):
                            for content_item in content:
                                if isinstance(content_item, dict) and content_item.get("type") == "output_text":
                                    text = content_item.get("text", "")
                                    if text:
                                        assistant_content = text
                                        print(f"🔧 Extracted message text: {text[:100]}...")
                                        
                                        # Extract sources from annotations (URL citations)
                                        annotations = content_item.get("annotations", [])
                                        if annotations:
                                            print(f"🔧 Found {len(annotations)} annotations")
                                            for annotation in annotations:
                                                if annotation.get("type") == "url_citation":
                                                    url = annotation.get("url", "")
                                                    title = annotation.get("title", "")
                                                    if url:
                                                        # Extract domain for favicon
                                                        from urllib.parse import urlparse
                                                        try:
                                                            parsed = urlparse(url)
                                                            domain = parsed.netloc
                                                            
                                                            source = {
                                                                "url": url,
                                                                "title": title if title else domain,
                                                                "site": domain,
                                                                "favicon": f"https://www.google.com/s2/favicons?domain={domain}&sz=64"
                                                            }
                                                            sources.append(source)
                                                            print(f"🔧 Added source: {domain}")
                                                        except Exception as e:
                                                            print(f"❌ Failed to parse URL {url}: {e}")
                                        break
            
            # Only get default response text if we haven't set assistant_content from function calls
            if not assistant_content:
                assistant_content = self.stringify_text(api_response.get("output_text") or "")
            
            # Extract sources from URLs in text content (like original repo)
            if isinstance(assistant_content, str) and assistant_content and not sources:
                import re
                from urllib.parse import urlparse
                
                # Find URLs in the response text
                raw_urls = re.findall(r"https?://[^\s)]+", assistant_content)
                print(f"🔍 Found {len(raw_urls)} URLs in response text")
                seen = set()
                for u in raw_urls:
                    cleaned = u.rstrip('.,);]')
                    if cleaned in seen:
                        continue
                    seen.add(cleaned)
                    try:
                        parsed = urlparse(cleaned)
                        if parsed.scheme in {"http", "https"} and parsed.netloc:
                            source = {
                                "url": cleaned,
                                "title": parsed.netloc,
                                "site": parsed.netloc,
                                "favicon": f"https://www.google.com/s2/favicons?domain={parsed.netloc}&sz=64"
                            }
                            sources.append(source)
                            print(f"🔧 Added URL source: {parsed.netloc}")
                    except Exception as e:
                        print(f"❌ Failed to parse URL {cleaned}: {e}")
                        continue
                
                # Limit sources
                if sources:
                    sources = sources[:8]
                    print(f"✅ Extracted {len(sources)} sources from URLs")
            
            # Handle incomplete responses (like GPT-5-mini hitting token limit)
            status = api_response.get("status")
            if status == "incomplete":
                assistant_content += "\n\n*[Response was truncated due to length limits]*"
            
            # Extract reasoning if available
            if include_reasoning and "reasoning" in api_response:
                reasoning = api_response["reasoning"]
            
            print(f"🔍 Final assistant content length: {len(assistant_content) if assistant_content else 0}")
            
        except Exception as e:
            print(f"❌ API call failed: {e}")
            assistant_content = f"I apologize, but I encountered an error while processing your request: {str(e)}"
            reasoning = None
            sources = []
        
        # Save assistant message
        await self.save_message_to_conversation(
            conversation_id, user_id, "assistant", assistant_content,
            {
                "model": model,
                "include_reasoning": include_reasoning,
                "original_api_used": True,
                "sources": sources
            }
        )
        
        # Create response messages
        user_message = {
            "id": str(uuid.uuid4()),
            "role": "user", 
            "content": message,
            "created_at": datetime.utcnow().isoformat()
        }
        
        assistant_message = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": assistant_content,
            "created_at": datetime.utcnow().isoformat()
        }
        
        return {
            "conversation_id": conversation_id,
            "user_message": user_message,
            "assistant_message": assistant_message,
            "reasoning": reasoning,
            "sources": sources
        }
    
    def stringify_text(self, text) -> str:
        """Helper method to stringify text."""
        if isinstance(text, str):
            return text
        elif isinstance(text, list):
            return "".join(str(item) for item in text)
        return str(text)
    
    async def get_conversation_list(self, user_id: str) -> List[Dict[str, Any]]:
        """Get list of conversations for a user."""
        try:
            # Try database first
            db_result = await self.use_database_fallback(
                "get_user_conversations", user_id
            )
            
            if db_result:
                return db_result
        except Exception as e:
            print(f"Database get conversations failed: {e}")
        
        # Use fallback storage
        conversations = []
        for conv_id, metadata in self.fallback_conversation_metadata.items():
            if metadata.get("user_id") == user_id:
                conversations.append({
                    "conversation_id": conv_id,
                    "title": metadata.get("title", "Untitled"),
                    "created_at": metadata.get("created_at"),
                    "updated_at": metadata.get("updated_at"),
                    "message_count": len(self.fallback_conversations.get(conv_id, []))
                })
        
        return conversations
    
    async def delete_conversation(self, conversation_id: str, user_id: str) -> bool:
        """Delete a conversation."""
        try:
            # Try database first
            db_result = await self.use_database_fallback(
                "delete_conversation", conversation_id
            )
            
            if db_result:
                return True
        except Exception as e:
            print(f"Database delete conversation failed: {e}")
        
        # Use fallback storage
        if conversation_id in self.fallback_conversations:
            # Verify ownership
            metadata = self.fallback_conversation_metadata.get(conversation_id, {})
            if metadata.get("user_id") == user_id:
                del self.fallback_conversations[conversation_id]
                del self.fallback_conversation_metadata[conversation_id]
                return True
        
        return False
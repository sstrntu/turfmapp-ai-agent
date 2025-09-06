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
from .conversation_context_agent import conversation_context_agent
from .master_agent import master_agent


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
        headers = {
            "Authorization": f"Bearer {self.responses_api_key}",
            "Content-Type": "application/json"
        }
        
        # Convert messages to conversation context string (Responses API format)
        conversation_context = ""
        for msg in messages:
            role = msg["role"].title()
            conversation_context += f"{role}: {msg['content']}\n\n"
        
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
""")
        
        if "developer_instructions" in kwargs and kwargs["developer_instructions"]:
            instructions.append(kwargs["developer_instructions"])
        if "assistant_context" in kwargs and kwargs["assistant_context"]:
            instructions.append(kwargs["assistant_context"])
        
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
        
        # Format messages for API
        formatted_history = format_chat_history(history, max_context=10)
        
        # Add current user message
        current_message = {"role": "user", "content": message}
        all_messages = formatted_history + [current_message]
        
        # Save user message first
        await self.save_message_to_conversation(
            conversation_id, user_id, "user", message
        )
        
        # Use Master Agent for intelligent conversation orchestration
        try:
            print("🧠 Using Master Agent for intelligent conversation orchestration")
            
            master_result = await master_agent.process_user_request(
                user_message=message,
                conversation_history=formatted_history, 
                user_id=user_id,
                mcp_client=google_mcp_client
            )
            
            if master_result.get("success"):
                # Master agent successfully handled the query
                assistant_content = master_result.get("response", "")
                
                # Save assistant message
                await self.save_message_to_conversation(
                    conversation_id, user_id, "assistant", assistant_content,
                    {
                        "agent_used": "master_agent",
                        "intent": master_result.get("intent"),
                        "tools_used": master_result.get("tools_used", []),
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
                    "sources": []
                }
            else:
                print("🧠 Master agent failed, falling back to context agent")
                
        except Exception as e:
            print(f"❌ Master agent error: {e}")
            print("🧠 Falling back to context agent")
        
        # Fallback: Check if the conversation context agent should handle this query
        if await conversation_context_agent.should_use_agent_for_query(message, formatted_history):
            print("🤖 Using Conversation Context Agent for intelligent query handling")
            
            try:
                agent_result = await conversation_context_agent.handle_contextual_query(
                    message, formatted_history, user_id, google_mcp_client
                )
                
                if agent_result.get('success'):
                    # Agent successfully handled the query
                    assistant_content = agent_result.get('response', '')
                    
                    # Save assistant message
                    await self.save_message_to_conversation(
                        conversation_id, user_id, "assistant", assistant_content,
                        {
                            "agent_used": "conversation_context_agent",
                            "service": agent_result.get('service'),
                            "tool_used": agent_result.get('tool_used'),
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
                        "sources": []
                    }
                elif agent_result.get('use_default_llm'):
                    print("🤖 Context agent recommends using default LLM flow")
                    # Continue with normal LLM processing below
                else:
                    print(f"🤖 Context agent failed: {agent_result.get('error', 'Unknown error')}")
                    # Continue with normal LLM processing below
                    
            except Exception as e:
                print(f"❌ Context agent error: {e}")
                # Continue with normal LLM processing below
        
        # Provide all available tools to the LLM and let it decide what to use
        tools_to_include = kwargs.get("tools", [])
        
        # Get existing tool names to avoid duplicates
        if tools_to_include is None:
            tools_to_include = []
            
        existing_tool_names = {tool.get("function", {}).get("name") for tool in tools_to_include if tool.get("type") == "function"}
        
        # Check if this is a general knowledge question that shouldn't use Google tools
        is_general_knowledge = self._is_general_knowledge_question(message)
        
        # Always include all MCP tools - let the LLM decide what to use
        try:
            print("🔧 Getting all MCP tools for LLM to choose from")
            mcp_tools = await get_all_google_tools()
            
            if mcp_tools is None:
                print("❌ get_all_google_tools() returned None")
                mcp_tools = []
            elif not isinstance(mcp_tools, list):
                print(f"❌ get_all_google_tools() returned non-list: {type(mcp_tools)}")
                mcp_tools = []
            
            print(f"🔧 Available MCP tools count: {len(mcp_tools)}")
            
            # Add MCP tools - filter out Google tools for general knowledge questions
            for mcp_tool in mcp_tools:
                if not isinstance(mcp_tool, dict):
                    continue
                    
                tool_name = mcp_tool.get("name")
                if tool_name and tool_name not in existing_tool_names:
                    # Skip Google tools for general knowledge questions
                    if is_general_knowledge and tool_name.startswith(('gmail_', 'drive_', 'calendar_')):
                        print(f"🔧 Skipping Google tool '{tool_name}' for general knowledge question")
                        continue
                        
                    # Convert MCP tool format to OpenAI function format
                    openai_tool = {
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "description": mcp_tool.get("description"),
                            "parameters": mcp_tool.get("inputSchema")
                        }
                    }
                    tools_to_include.append(openai_tool)
                    existing_tool_names.add(tool_name)
            
            print(f"🔧 Included {len([t for t in tools_to_include if t.get('function', {}).get('name', '').startswith(('gmail_', 'drive_', 'calendar_'))])} Google MCP tools")
            
        except Exception as e:
            print(f"❌ Failed to get MCP tools: {e}")
            print("⚠️  Google services unavailable due to MCP client failure")
        
        print(f"🔧 Total tools available to LLM: {len(tools_to_include)}")
        
        # Call API
        try:
            api_response = await self.call_responses_api(
                messages=all_messages,
                model=model,
                include_reasoning=include_reasoning,
                tools=tools_to_include,
                **{k: v for k, v in kwargs.items() if k not in ["model", "include_reasoning", "tools"]}
            )
            
            # Extract assistant response from Responses API format
            assistant_content = ""
            reasoning = None
            
            # Parse Responses API output with debugging
            print(f"🔍 API Response for model {model} (keys only): {api_response.keys()}")
            print(f"🔍 API Response content: {api_response.get('content', 'No content field')}")
            print(f"🔍 API Response output: {api_response.get('output', 'No output field')}")
            if 'choices' in api_response:
                print(f"🔍 API Response choices: {api_response.get('choices', [])}")
            print(f"🔍 Full API Response: {api_response}")
            
            # Check if there are any tool calls in the response
            if "tool_calls" in api_response:
                print(f"🔧 Tool calls found in response: {api_response['tool_calls']}")
            else:
                print(f"🔧 No tool calls found in response")
            
            # Check the output structure for function calls
            output_items = api_response.get("output", [])
            print(f"🔧 Output items: {len(output_items) if output_items else 0}")
            print(f"🔧 Full API response structure: {api_response.keys()}")
            
            # Handle function calls from the API response
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
            
            # Process function calls if any were found
            if function_calls:
                print(f"🔧 Processing {len(function_calls)} function calls...")
                
                # Convert function calls to tool call format for processing
                tool_calls = []
                for func_call in function_calls:
                    if func_call.get("status") == "completed":
                        tool_calls.append({
                            "id": func_call.get("call_id", func_call.get("id")),
                            "function": {
                                "name": func_call.get("name"),
                                "arguments": func_call.get("arguments", "{}")
                            }
                        })
                
                if tool_calls:
                    # Execute the tool calls
                    tool_results = await self.handle_tool_calls(user_id, tool_calls)
                    print(f"🔧 Tool execution results: {tool_results}")
                    
                    # Format tool results for AI response
                    if tool_results:
                        results_summary = []
                        for result in tool_results:
                            tool_result = result.get("result", {})
                            tool_name = result.get("tool_name", "Tool")
                            
                            # All tools now return formatted responses in the "response" field
                            if "response" in tool_result:
                                results_summary.append(tool_result["response"])
                            elif tool_result.get("success"):
                                # Fallback for tools that don't provide formatted responses
                                results_summary.append(f"✅ {tool_name} executed successfully")
                            else:
                                # Handle errors
                                error_msg = tool_result.get("error", "Unknown error")
                                results_summary.append(f"❌ {tool_name} failed: {error_msg}")
                        
                        if results_summary:
                            assistant_content = "\n".join(results_summary)
                        else:
                            assistant_content = "I attempted to use tools to help with your request, but didn't find the expected results."
                    else:
                        assistant_content = "I tried to access your Gmail but encountered an issue. Please make sure you're authenticated with Google."
            
            # Only get default response text if we haven't set assistant_content from function calls
            if not assistant_content:
                assistant_content = stringify_text(api_response.get("output_text") or "")
            
            # Handle incomplete responses (like GPT-5-mini hitting token limit)
            status = api_response.get("status")
            if status == "incomplete":
                incomplete_reason = api_response.get("incomplete_details", {}).get("reason", "unknown")
                print(f"⚠️ Incomplete response for {model}: {incomplete_reason}")
                
                if incomplete_reason == "max_output_tokens":
                    # Try to extract partial content from the output array
                    output_items = api_response.get("output", [])
                    if isinstance(output_items, list):
                        # Look for any text content in the output items
                        text_parts = []
                        web_searches = []
                        
                        for item in output_items:
                            if not isinstance(item, dict):
                                continue
                            
                            item_type = item.get("type")
                            if item_type == "output_text":
                                text_parts.append(stringify_text(item.get("text", "")))
                            elif item_type == "web_search_call" and item.get("status") == "completed":
                                # Extract search query to show what was being researched
                                query = item.get("action", {}).get("query", "")
                                if query:
                                    web_searches.append(query)
                        
                        if text_parts:
                            assistant_content = "".join(text_parts)
                        elif web_searches:
                            # If no text but web searches were performed, create a helpful message
                            assistant_content = f"I was researching your question about: {', '.join(web_searches[:3])}... but my response was cut off due to length. Please try asking a more specific question."
            
            if not assistant_content:
                # Try alternative response formats for different models
                output_items = api_response.get("output", [])
                
                # GPT-5-mini might use different response format
                if model == "gpt-5-mini" and not output_items:
                    # Check for choices format (similar to chat completions)
                    choices = api_response.get("choices", [])
                    if choices and isinstance(choices, list):
                        first_choice = choices[0]
                        if isinstance(first_choice, dict):
                            # Try message.content format
                            message = first_choice.get("message", {})
                            if isinstance(message, dict):
                                assistant_content = stringify_text(message.get("content", ""))
                            # Try text format
                            if not assistant_content:
                                assistant_content = stringify_text(first_choice.get("text", ""))
                
                # Standard output parsing for other models
                if not assistant_content and isinstance(output_items, list):
                    parts = []
                    for item in output_items:
                        if not isinstance(item, dict):
                            continue
                        item_type = item.get("type")
                        if item_type == "output_text":
                            parts.append(stringify_text(item.get("text")))
                            continue
                        if item_type == "message":
                            for block in item.get("content", []) or []:
                                if not isinstance(block, dict):
                                    continue
                                block_type = block.get("type")
                                if block_type == "output_text":
                                    parts.append(stringify_text(block.get("text")))
                    assistant_content = "".join(parts)
            
            # Extract reasoning if available (from working version)
            if include_reasoning:
                reasoning_data = api_response.get("reasoning", {})
                if isinstance(reasoning_data, dict):
                    reasoning = reasoning_data.get("summary", "")
            
            # Ensure content is not empty
            if not assistant_content:
                assistant_content = "I received your message but couldn't generate a proper response. Please try again."
            else:
                assistant_content = stringify_text(assistant_content)
            
            # Extract sources from content (URLs) - restored from working version
            sources = []
            if isinstance(assistant_content, str) and assistant_content:
                import re
                from urllib.parse import urlparse
                
                raw_urls = re.findall(r"https?://[^\s)]+", assistant_content)
                print(f"🔍 Found {len(raw_urls)} URLs in content")
                seen = set()
                for u in raw_urls:
                    cleaned = u.rstrip('.,);]')
                    if cleaned in seen:
                        continue
                    seen.add(cleaned)
                    try:
                        parsed = urlparse(cleaned)
                        if parsed.scheme in {"http", "https"} and parsed.netloc:
                            # Try multiple favicon services for better reliability
                            favicon_urls = [
                                f"https://www.google.com/s2/favicons?domain={parsed.netloc}&sz=64",
                                f"https://favicon.io/favicon/{parsed.netloc}/64",
                                f"https://t1.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url={parsed.netloc}&size=64"
                            ]
                            
                            sources.append({
                                "url": cleaned,
                                "site": parsed.netloc,
                                "favicon": favicon_urls[0],  # Use first one as primary
                                "favicon_fallbacks": favicon_urls[1:],  # Store fallbacks
                            })
                    except Exception:
                        continue
                        
                if sources:
                    sources = sources[:8]
                    print(f"✅ Extracted {len(sources)} sources: {[s['site'] for s in sources]}")
                    
                    # Enrich sources with thumbnails (Open Graph images)
                    try:
                        async with httpx.AsyncClient(timeout=httpx.Timeout(2.0, connect=1.0)) as _client:
                            sem = asyncio.Semaphore(3)
                            async def enrich(s: dict) -> None:
                                try:
                                    async with sem:
                                        r = await _client.get(s["url"], follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
                                    if r.status_code >= 200 and r.status_code < 400:
                                        html = r.text[:120000]
                                        t = re.search(r"<title[^>]*>([\s\S]*?)</title>", html, re.IGNORECASE)
                                        if t:
                                            title_val = re.sub(r"\s+", " ", t.group(1).strip())
                                            s["title"] = title_val
                                        m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
                                        if not m:
                                            m = re.search(r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
                                        if m:
                                            img_url = m.group(1)
                                            if img_url:
                                                if img_url.startswith('//'):
                                                    img_url = f"https:{img_url}"
                                                elif img_url.startswith('/'):
                                                    from urllib.parse import urljoin
                                                    img_url = urljoin(s["url"], img_url)
                                                s["thumbnail"] = img_url
                                except Exception:
                                    return
                            await asyncio.gather(*(enrich(s) for s in sources[:3]))
                    except Exception:
                        pass
                else:
                    sources = []
                    print("ℹ️ No sources found in content")
            
            # Save assistant message
            await self.save_message_to_conversation(
                conversation_id, 
                user_id, 
                "assistant", 
                assistant_content,
                {
                    "sources": sources,
                    "model": model,
                    "api_response": api_response
                }
            )
            
            # Create response messages in working format
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
            
            # Debug logging for response
            print(f"🔍 Final response sources: {sources}")
            print(f"🔍 Sources type: {type(sources)}")
            print(f"🔍 Sources length: {len(sources) if sources else 'None'}")
            
            return {
                "conversation_id": conversation_id,
                "user_message": user_message,
                "assistant_message": assistant_message,
                "reasoning": reasoning,
                "sources": sources
            }
            
        except Exception as e:
            # Save error message for debugging
            error_message = f"I apologize, but I encountered an error processing your request: {str(e)}"
            await self.save_message_to_conversation(
                conversation_id, 
                user_id, 
                "assistant", 
                error_message,
                {"error": str(e)}
            )
            
            return {
                "conversation_id": conversation_id,
                "user_message": {"role": "user", "content": message},
                "assistant_message": {"role": "assistant", "content": error_message},
                "sources": [],
                "error": str(e)
            }
    
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
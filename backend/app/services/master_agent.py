"""
Master Agent - Intelligent conversation orchestration and response generation

This agent acts as the "brain" of the system, understanding user intent, 
planning actions, calling tools, analyzing results, and crafting intelligent responses.
"""

from __future__ import annotations

import json
import re
import time
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

class MasterAgent:
    """Intelligent master agent that orchestrates the entire conversation flow."""
    
    def __init__(self):
        self.conversation_memory = {}
        
    async def process_user_request(
        self, 
        user_message: str, 
        conversation_history: List[Dict[str, Any]], 
        user_id: str,
        mcp_client
    ) -> Dict[str, Any]:
        """Process user request using intelligent 3-tier decision system."""
        
        print(f"🧠 Master Agent processing: '{user_message[:50]}...'")
        
        # Import the intelligent universal classifier and analytics (avoid circular imports)
        from .intelligent_classifier import intelligent_classifier
        from .tool_analytics import tool_analytics
        from .response_evaluator import response_evaluator
        
        # Get user preferences
        user_settings = self._get_user_settings(user_id)
        
        # Check if auto tool usage is disabled
        if not user_settings.tool_preferences.auto_tool_usage:
            print("🔒 Auto tool usage disabled by user preferences")
            return {
                "success": False,
                "response": "",
                "approach": "user_disabled_tools",
                "classification": {"classification": "USER_DISABLED", "confidence": 1.0},
                "tools_used": []
            }
        
        # Start timing for analytics
        start_time = time.time()
        
        # Classify the request using intelligent universal classifier
        classification = await intelligent_classifier.classify_request(user_message, conversation_history)
        
        print(f"🔍 Classification: {classification['classification']} (confidence: {classification['confidence']:.2f}, tier: {classification['tier_used']})")
        print(f"🔍 Reasoning: {classification['reasoning']}")
        
        # Handle based on classification
        if classification["classification"] == "GENERAL_KNOWLEDGE":
            # Handle general knowledge using Responses API - let GPT decide if it needs web search
            print("🧠 General knowledge query - using Responses API (GPT can use web search if needed)")
            
            # Use enhanced chat service to call Responses API
            from .enhanced_chat_service import EnhancedChatService
            chat_service = EnhancedChatService()
            
            # Format messages for Responses API
            messages = []
            for msg in conversation_history[-5:]:  # Last 5 for context
                if msg.get("role") in ["user", "assistant"]:
                    messages.append(msg)
            messages.append({"role": "user", "content": user_message})
            
            # Call Responses API - let GPT decide if it needs web search
            try:
                api_result = await chat_service.call_responses_api(
                    messages=messages,
                    model="gpt-4o",
                    include_reasoning=False,
                    max_tokens=800
                )
            except Exception as e:
                print(f"❌ Responses API error: {e}")
                api_result = None
            
            if api_result and api_result.get("content"):
                response = api_result["content"]
                web_search_used = "web_search" in str(api_result.get("tool_calls", []))
                
                result = {
                    "success": True,
                    "response": response,
                    "approach": "general_knowledge_with_responses_api",
                    "classification": classification,
                    "tools_used": ["web_search"] if web_search_used else []
                }
                
                print(f"🧠 General knowledge result - Web search used: {web_search_used}")
                
            else:
                # Fallback to direct LLM
                response = await self._answer_with_llm_only(user_message, conversation_history)
                result = {
                    "success": True,
                    "response": response,
                    "approach": "general_knowledge_fallback",
                    "classification": classification,
                    "tools_used": []
                }
            
            # Log classification decision and evaluate response (async)
            asyncio.create_task(self._evaluate_and_learn(
                user_message, response, result["approach"], result["tools_used"], 
                start_time, user_id, classification
            ))
            
            return result
        
        elif classification["classification"] == "CURRENT_INFO":
            # Handle current information requests using Responses API (has web search built-in)
            print("🌐 Current information query - using Responses API with web search capability")
            
            # Use enhanced chat service to call Responses API with web search
            from .enhanced_chat_service import EnhancedChatService
            chat_service = EnhancedChatService()
            
            # Format messages for Responses API
            messages = []
            for msg in conversation_history[-5:]:  # Last 5 for context
                if msg.get("role") in ["user", "assistant"]:
                    messages.append(msg)
            messages.append({"role": "user", "content": user_message})
            
            # Call Responses API - let GPT decide if it needs web search
            try:
                api_result = await chat_service.call_responses_api(
                    messages=messages,
                    model="gpt-4o",
                    include_reasoning=False,
                    max_tokens=1000
                )
            except Exception as e:
                print(f"❌ Responses API error: {e}")
                api_result = None
            
            if api_result and api_result.get("content"):
                response = api_result["content"]
                web_search_used = "web_search" in str(api_result.get("tool_calls", []))
                
                result = {
                    "success": True,
                    "response": response,
                    "approach": "responses_api_with_web_search",
                    "classification": classification,
                    "tools_used": ["web_search"] if web_search_used else []
                }
                
                print(f"🌐 Responses API result - Web search used: {web_search_used}")
                
            else:
                # Fallback if Responses API fails
                response = "I'm having trouble accessing current information right now. Please try again or check authoritative sources for the latest data."
                result = {
                    "success": True,
                    "response": response,
                    "approach": "current_info_fallback",
                    "classification": classification,
                    "tools_used": []
                }
            
            # Evaluate and learn (async)
            asyncio.create_task(self._evaluate_and_learn(
                user_message, response, result["approach"], result["tools_used"], 
                start_time, user_id, classification
            ))
            
            return result
        
        elif classification["classification"] == "PERSONAL_DATA":
            # Filter suggested tools based on user preferences
            allowed_tools = self._filter_tools_by_preferences(
                classification["suggested_tools"], user_settings
            )
            
            if not allowed_tools:
                print("🔒 No tools allowed by user preferences")
                return {
                    "success": False,
                    "response": "",
                    "approach": "tools_disabled_by_user",
                    "classification": classification,
                    "tools_used": []
                }
            
            # Limit number of tools based on user preference
            max_tools = user_settings.tool_preferences.max_tools_per_query
            limited_tools = allowed_tools[:max_tools]
            
            print(f"🔧 Using tools for personal data: {limited_tools} (filtered from {classification['suggested_tools']})")
            
            response = await self._execute_tool_based_request(
                user_message, 
                conversation_history,
                user_id,
                mcp_client,
                limited_tools
            )
            
            # Evaluate response quality and log analytics
            result = {
                "success": True,
                "response": response,
                "approach": "tool_based",
                "classification": classification,
                "tools_used": classification["suggested_tools"]
            }
            
            # Evaluate and improve (async)
            asyncio.create_task(self._evaluate_and_learn(
                user_message, response, "tool_based", classification["suggested_tools"], 
                start_time, user_id, classification
            ))
            
            return result
        
        elif classification["classification"] == "CONTEXT_DEPENDENT":
            # Analyze context to determine if tools are needed
            context_analysis = self._analyze_conversation_context(conversation_history)
            
            if context_analysis and any(keyword in context_analysis for keyword in ["Has recent email data", "Has recent Drive data", "Has recent Calendar data"]):
                # Use existing context, no tools needed
                response = await self._answer_from_existing_context(user_message, conversation_history)
                result = {
                    "success": True,
                    "response": response,
                    "approach": "context_analysis",
                    "classification": classification,
                    "tools_used": []
                }
                
                # Evaluate and improve (async)
                asyncio.create_task(self._evaluate_and_learn(
                    user_message, response, "context_analysis", [], 
                    start_time, user_id, classification
                ))
                
                return result
            else:
                # Fall back to LLM analysis
                print("🔍 Context-dependent request needs LLM analysis")
                return await self._intelligent_tool_planning_and_execution(
                    user_message, conversation_history, user_id, mcp_client
                )
        
        else:  # AMBIGUOUS
            # Use comprehensive LLM analysis (Tier 3)
            print("🔍 Ambiguous request needs comprehensive LLM analysis")
            return await self._intelligent_tool_planning_and_execution(
                user_message, conversation_history, user_id, mcp_client
            )
    
    async def _execute_tool_based_request(
        self, 
        user_message: str,
        conversation_history: List[Dict[str, Any]], 
        user_id: str,
        mcp_client,
        suggested_tools: List[str]
    ) -> str:
        """Execute a request using specific suggested tools."""
        
        # Create a simple tool execution plan
        tool_results = []
        
        for tool_name in suggested_tools:
            # Extract search parameters from user message
            tool_params = self._extract_tool_parameters(user_message, tool_name)
            tool_params["user_id"] = user_id
            
            print(f"🔧 Executing tool: {tool_name} with params: {tool_params}")
            
            try:
                result = await mcp_client.call_tool(tool_name, tool_params)
                tool_results.append({
                    "tool": tool_name,
                    "params": tool_params,
                    "result": result,
                    "success": result.get("success", False)
                })
                print(f"🔧 Tool {tool_name} result: {result.get('success', False)}")
                
            except Exception as e:
                print(f"❌ Tool {tool_name} failed: {e}")
                tool_results.append({
                    "tool": tool_name,
                    "params": tool_params,
                    "result": {"success": False, "error": str(e)},
                    "success": False
                })
        
        # Synthesize response from tool results
        return await self._synthesize_tool_results(user_message, tool_results, conversation_history)
    
    async def _intelligent_tool_planning_and_execution(
        self,
        user_message: str,
        conversation_history: List[Dict[str, Any]],
        user_id: str,
        mcp_client
    ) -> Dict[str, Any]:
        """Use comprehensive LLM analysis for complex/ambiguous requests."""
        
        # Get available tools
        available_tools = await self._get_available_tools(mcp_client)
        
        # Use existing intelligent tool planning method
        tool_plan = await self._intelligent_tool_planning(
            user_message, conversation_history, available_tools
        )
        
        if not tool_plan.get("needs_tools", False):
            # No tools needed according to LLM analysis
            response = await self._answer_from_existing_context(user_message, conversation_history)
            return {
                "success": True,
                "response": response,
                "approach": "llm_analysis_no_tools",
                "classification": {"classification": "GENERAL_KNOWLEDGE", "confidence": 0.8},
                "tools_used": []
            }
        
        # Execute tools and analyze results
        response = await self._execute_and_analyze_iteratively(
            tool_plan, user_message, conversation_history, user_id, mcp_client
        )
        
        return {
            "success": True,
            "response": response,
            "approach": "llm_analysis_with_tools",
            "classification": {"classification": "PERSONAL_DATA", "confidence": 0.7},
            "tools_used": [step["tool"] for step in tool_plan.get("tool_sequence", [])]
        }
    
    def _extract_tool_parameters(self, user_message: str, tool_name: str) -> Dict[str, Any]:
        """Extract parameters for tool execution from user message."""
        params = {}
        message_lower = user_message.lower()
        
        if "gmail" in tool_name:
            # Extract search query for Gmail tools
            if "recent" in tool_name or "recent" in message_lower or "latest" in message_lower:
                params["max_results"] = 5
            else:
                # Try to extract search terms
                query = self._extract_smart_search_query(user_message)
                if query:
                    params["query"] = query
                    params["max_results"] = 5
                else:
                    params["max_results"] = 5
        
        elif "drive" in tool_name:
            # Drive parameters
            params["max_results"] = 10
        
        elif "calendar" in tool_name:
            # Calendar parameters
            if "upcoming" in tool_name or "upcoming" in message_lower or "next" in message_lower:
                params["max_results"] = 5
            else:
                params["max_results"] = 10
        
        return params
    
    async def _synthesize_tool_results(
        self, 
        user_message: str, 
        tool_results: List[Dict[str, Any]], 
        conversation_history: List[Dict[str, Any]]
    ) -> str:
        """Synthesize a response from tool execution results."""
        
        # Combine successful tool results
        combined_data = ""
        successful_tools = []
        
        for tool_result in tool_results:
            if tool_result.get("success") and tool_result["result"].get("success"):
                successful_tools.append(tool_result["tool"])
                if "response" in tool_result["result"]:
                    combined_data += f"\n--- {tool_result['tool']} result ---\n"
                    combined_data += str(tool_result["result"]["response"])
                    combined_data += "\n"
        
        if not combined_data:
            return "I tried to gather the information you requested, but the tools didn't return any useful data. Please try rephrasing your question or check your Google account permissions."
        
        print(f"🧠 Synthesizing response from {len(successful_tools)} successful tools")
        
        # Use LLM to analyze and synthesize response
        analysis_result = await self._analyze_content_with_llm(
            content=combined_data,
            analysis_type="question_answering",
            user_query=user_message
        )
        
        if analysis_result and analysis_result.get("answer"):
            return f"Based on your {', '.join(successful_tools)}: {analysis_result['answer']}"
        elif analysis_result and analysis_result.get("raw_analysis"):
            return analysis_result["raw_analysis"]
        else:
            # Fallback to raw data with summary
            return f"I gathered information from your {', '.join(successful_tools)}:\n\n{combined_data[:1000]}..."
    
    async def _get_available_tools(self, mcp_client) -> Dict[str, Dict[str, Any]]:
        """Get all available tools from MCP client with descriptions."""
        try:
            # Import the function to get MCP tools
            from .mcp_client_simple import get_all_google_tools
            
            tools = await get_all_google_tools()
            tool_map = {}
            
            for tool in tools:
                tool_map[tool.get("name")] = {
                    "description": tool.get("description"),
                    "input_schema": tool.get("inputSchema"),
                    "category": self._categorize_tool(tool.get("name"))
                }
            
            return tool_map
            
        except Exception as e:
            print(f"❌ Error getting available tools: {e}")
            return {
                "gmail_search": {"description": "Search Gmail emails", "category": "email"},
                "gmail_recent": {"description": "Get recent Gmail emails", "category": "email"},
                "drive_list_files": {"description": "List Google Drive files", "category": "files"}
            }
    
    def _categorize_tool(self, tool_name: str) -> str:
        """Categorize tools by type for better decision making."""
        if "gmail" in tool_name.lower():
            return "email"
        elif "drive" in tool_name.lower():
            return "files"
        elif "calendar" in tool_name.lower():
            return "calendar"
        else:
            return "other"
    
    async def _intelligent_tool_planning(
        self, 
        user_message: str, 
        conversation_history: List[Dict[str, Any]], 
        available_tools: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Use LLM to intelligently plan which tools to use and how."""
        
        # Create context about conversation history
        recent_context = self._analyze_conversation_context(conversation_history)
        
        # Build tool descriptions for LLM
        tool_descriptions = []
        for tool_name, tool_info in available_tools.items():
            tool_descriptions.append(f"- {tool_name}: {tool_info['description']} (Category: {tool_info['category']})")
        
        tools_text = "\n".join(tool_descriptions)
        
        system_prompt = f"""You are an intelligent assistant that needs to decide which tools to use to answer a user's question.

Available Tools:
{tools_text}

Conversation Context: {recent_context}

User Question: "{user_message}"

CONTEXT ANALYSIS:
- Pay close attention to pronouns like "they", "them", "it", "those" which refer to items mentioned in recent conversation
- If the user asks "what are they?" or similar, they're asking for details about something mentioned in the previous conversation
- Check if the conversation context contains recent topics that the user might be referring to
- Look for follow-up patterns like "tell me more", "what does it say", "details", "what's that about"

CRITICAL DECISION RULES:
1. GENERAL KNOWLEDGE QUESTIONS: If the user asks about general knowledge (sports, history, science, definitions, etc.), DO NOT use tools. Answer directly.
2. EXISTING CONTEXT: If the user asks about something already discussed in the conversation, DO NOT use tools. Use existing context.
3. PERSONAL DATA REQUESTS: Use Gmail/Drive/Calendar tools when user asks about their personal data (emails, files, calendar events).
4. FOLLOW-UP QUESTIONS: If user asks follow-up questions (using pronouns or "tell me more"), analyze the conversation context to determine if personal data was discussed - if so, use appropriate tools.
5. CURRENT INFORMATION: For current information that's not personal data, use web search if available, otherwise answer from general knowledge.
6. CONTEXT ANALYSIS: Always analyze the conversation history to understand what the user is referring to, especially with pronouns and follow-up questions.

ANALYZE THE USER'S QUESTION:
1. Is this a general knowledge question that I can answer without tools?
2. Is the user asking about something already discussed in our conversation?
3. Is the user asking about their personal data (emails, files, calendar)?
4. Is this a follow-up question referring to something from recent conversation?
5. Does the user need current information that requires web search?

TOOL USAGE GUIDELINES:
- gmail_search: Use when user asks about their emails, inbox, or when follow-up questions refer to email content from recent conversation
- gmail_get_message: Use if you need the FULL content of a specific email and gmail_search doesn't provide enough detail
- drive_*: Use when user asks about their files, documents, or when follow-up questions refer to file content
- calendar_*: Use when user asks about their schedule, meetings, or when follow-up questions refer to calendar events
- web_search: Use for current information that's not personal data (news, weather, current events, etc.)
- If user asks "what are they?" and conversation context shows recent discussions about personal data, use appropriate tools
- Use the simplest approach that answers the user's question

FOLLOW-UP DETECTION:
- Use intelligent analysis to understand what pronouns and follow-up phrases refer to
- Analyze conversation context to determine if user is referring to personal data or general knowledge
- Look for contextual clues about what was discussed previously
- If follow-up + personal data context = use appropriate tools
- If follow-up + general knowledge context = answer from existing context
- Be intelligent about context analysis - don't rely on simple pattern matching

SMART SEARCH QUERY GUIDELINES:
- When user asks about a PROJECT/TOPIC/CONTENT, search for the core subject name, not specific descriptive keywords
- Extract the main entity being discussed (project names, content titles, document types, etc.)
- Remove episode numbers, version numbers, and descriptive words that might limit results
- For content/project questions, use the primary name rather than full descriptive phrases
- For business topics, use the core subject matter rather than specific action words
- Avoid overly specific search terms that might miss relevant emails
- Think: Is this a sender name, or a topic/project/content being discussed? Topics need broader, more inclusive searches.
- Priority: Cast a wide net to find all related discussions rather than exact phrase matches.

Return your decision as VALID JSON (no comments or extra formatting):
{{
    "needs_tools": true/false,
    "reasoning": "explanation of your decision including context analysis",
    "tool_sequence": [
        {{
            "tool": "tool_name",
            "params": {{}},
            "purpose": "why using this tool"
        }}
    ],
    "expected_outcome": "what we expect to achieve"
}}

IMPORTANT: 
- Return only valid JSON
- No comments, explanations, or text outside the JSON structure
- For general knowledge questions, set needs_tools to false
- For follow-up questions, check if recent context contains personal data references
- If follow-up + personal data context, use appropriate tools
- If follow-up + general knowledge context, answer from existing context
"""

        try:
            # Use the LLM analysis method we already have
            analysis_result = await self._analyze_content_with_llm(
                content=system_prompt,
                analysis_type="tool_planning",
                user_query=user_message
            )
            
            if analysis_result:
                return analysis_result
            else:
                # Fallback to basic logic
                return self._basic_tool_planning(user_message, recent_context, available_tools)
                
        except Exception as e:
            print(f"❌ LLM tool planning failed: {e}")
            return self._basic_tool_planning(user_message, recent_context, available_tools)
    
    def _analyze_conversation_context(self, history: List[Dict[str, Any]]) -> str:
        """Analyze conversation history to understand what data we already have and recent topics."""
        context_summary = []
        recent_topics = []
        
        # Analyze last 5 messages for better context
        for msg in history[-5:]:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role == "assistant":
                # Check for data types
                if any(keyword in content.lower() for keyword in ["email", "gmail"]):
                    context_summary.append("Has recent email data")
                elif "drive" in content.lower():
                    context_summary.append("Has recent Drive data")
                elif "calendar" in content.lower():
                    context_summary.append("Has recent Calendar data")
                
                # Extract key topics mentioned in assistant responses
                if "jubilo" in content.lower():
                    recent_topics.append("Jubilo email discussions")
                if "frame.io" in content.lower():
                    recent_topics.append("Frame.io comments")
                if "made in j.league" in content.lower():
                    recent_topics.append("Made in J.League episode content")
                if "comments" in content.lower():
                    recent_topics.append("Comments or feedback discussions")
            
            elif role == "user":
                # Track user questions to understand conversation flow
                user_content = content.lower()
                if "what are they" in user_content or "what are those" in user_content:
                    context_summary.append("User asking for clarification on previous response")
                if "frame.io" in user_content:
                    recent_topics.append("User mentioned Frame.io")
                if "jubilo" in user_content:
                    recent_topics.append("User asked about Jubilo")
        
        # Combine context summary
        context_parts = []
        if context_summary:
            context_parts.extend(context_summary)
        if recent_topics:
            context_parts.append(f"Recent topics: {', '.join(set(recent_topics))}")
            
        return "; ".join(context_parts) if context_parts else "No recent data context"
    
    def _basic_tool_planning(
        self, 
        user_message: str, 
        context: str, 
        available_tools: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Basic fallback tool planning when LLM is not available."""
        
        message_lower = user_message.lower()
        
        # Check for general knowledge questions that don't need tools
        general_knowledge_patterns = [
            r'who is.*(top|best|leading).*',
            r'what is.*(league|championship|competition)',
            r'who won.*(championship|title|award)',
            r'what happened.*in.*\d{4}',
            r'who is.*(famous|well-known).*person',
            r'what is.*capital.*of',
            r'how many.*people.*in',
            r'what is.*population.*of',
            r'who invented.*',
            r'when was.*invented',
            r'what is.*definition.*of',
            r'explain.*(concept|theory|principle)',
            r'what does.*mean',
            r'how does.*work',
            r'why is.*important',
            r'what is.*weather',
            r'what time.*is.*it',
            r'what day.*is.*it',
            r'what year.*is.*it',
            r'who is.*(president|leader|ceo)',
            r'what is.*(currency|language)',
            r'how much.*(cost|price)',
            r'where is.*located'
        ]
        
        # Check if this is a general knowledge question
        is_general_knowledge = any(re.search(pattern, message_lower) for pattern in general_knowledge_patterns)
        
        if is_general_knowledge:
            return {
                "needs_tools": False,
                "reasoning": "General knowledge question that can be answered without tools",
                "tool_sequence": [],
                "expected_outcome": "Answer from general knowledge"
            }
        
        # If asking about existing context, don't use tools
        if context and any(keyword in message_lower for keyword in ["what is", "tell me about", "explain"]):
            return {
                "needs_tools": False,
                "reasoning": "User asking about existing conversation content",
                "tool_sequence": [],
                "expected_outcome": "Answer from existing context"
            }
        
        # More specific email-related patterns - only trigger for actual email requests
        email_request_patterns = [
            r'show.*my.*email',
            r'get.*my.*email',
            r'check.*my.*inbox',
            r'find.*email.*about',
            r'search.*email.*for',
            r'what.*email.*do.*i.*have',
            r'list.*my.*emails',
            r'recent.*emails',
            r'new.*emails',
            r'unread.*emails',
            r'important.*emails'
        ]
        
        # Check for specific email requests
        is_email_request = any(re.search(pattern, message_lower) for pattern in email_request_patterns)
        
        if is_email_request:
            # Smart search query extraction
            search_query = self._extract_smart_search_query(user_message)
            
            return {
                "needs_tools": True,
                "reasoning": "User requesting specific email information",
                "tool_sequence": [
                    {
                        "tool": "gmail_recent" if "recent" in message_lower else "gmail_search",
                        "params": {"query": search_query, "max_results": 5} if search_query else {"max_results": 5},
                        "purpose": "Get email information"
                    }
                ],
                "expected_outcome": "Email data to answer user's question"
            }
        
        return {
            "needs_tools": False,
            "reasoning": "General question that can be answered without tools",
            "tool_sequence": [],
            "expected_outcome": "Answer from general knowledge"
        }
    
    def _extract_smart_search_query(self, user_message: str) -> str:
        """Extract intelligent search query from user message."""
        import re
        
        message = user_message.lower()
        
        # Patterns for topic/project extraction
        patterns = [
            r'comments for (.+?)\??$',
            r'feedback on (.+?)\??$',
            r'about (.+?)\??$',
            r'regarding (.+?)\??$',
            r'for (.+?) ep\d+',  # For episode references
            r'made in (.+?)(?:\s+ep\d+)?',  # For "Made in X" projects
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message)
            if match:
                topic = match.group(1).strip()
                
                # Clean up common words that don't help search
                topic = re.sub(r'\s+(ep\d+|episode\s*\d+|comments?|feedback)\s*$', '', topic, flags=re.IGNORECASE)
                
                # For "Made in J.League", extract just "J.League" or keep full name
                if 'made in j.league' in topic.lower():
                    return 'J.League'
                
                return topic
        
        # Fallback: extract key terms
        key_terms = []
        if 'j.league' in message or 'j league' in message:
            key_terms.append('J.League')
        if 'frame.io' in message:
            key_terms.append('frame.io')
        if 'jubilo' in message:
            key_terms.append('Jubilo')
            
        return ' OR '.join(key_terms) if key_terms else ""
    
    async def _execute_and_analyze_iteratively(
        self,
        tool_plan: Dict[str, Any],
        user_message: str,
        conversation_history: List[Dict[str, Any]],
        user_id: str,
        mcp_client
    ) -> str:
        """Execute tools and analyze results to determine if question is answered."""
        
        # Handle case where LLM response was raw text instead of JSON
        if "raw_analysis" in tool_plan and not tool_plan.get("needs_tools"):
            # Try to parse the raw analysis
            raw_text = tool_plan["raw_analysis"]
            import json
            try:
                # Try to extract JSON from raw text
                start = raw_text.find('{')
                end = raw_text.rfind('}') + 1
                if start >= 0 and end > start:
                    json_text = raw_text[start:end]
                    # Remove comments
                    import re
                    json_text = re.sub(r'//.*', '', json_text)
                    json_text = re.sub(r'/\*.*?\*/', '', json_text, flags=re.DOTALL)
                    parsed_plan = json.loads(json_text)
                    tool_plan.update(parsed_plan)
            except:
                print(f"❌ Could not parse raw analysis, using existing context")
        
        if not tool_plan.get("needs_tools", False):
            # No tools needed, analyze existing conversation
            return await self._answer_from_existing_context(user_message, conversation_history)
        
        # Execute tools in sequence
        all_tool_results = []
        
        for tool_step in tool_plan.get("tool_sequence", []):
            tool_name = tool_step["tool"]
            tool_params = tool_step["params"].copy()  # Copy to avoid modifying original
            
            # Resolve dynamic parameters from previous results
            tool_params = self._resolve_dynamic_params(tool_params, all_tool_results)
            tool_params["user_id"] = user_id
            
            print(f"🔧 Executing tool: {tool_name} with params: {tool_params}")
            
            try:
                result = await mcp_client.call_tool(tool_name, tool_params)
                all_tool_results.append({
                    "tool": tool_name,
                    "params": tool_params,
                    "result": result,
                    "purpose": tool_step["purpose"]
                })
                
                print(f"🔧 Tool {tool_name} result: {result.get('success', False)}")
                
            except Exception as e:
                print(f"❌ Tool {tool_name} failed: {e}")
                all_tool_results.append({
                    "tool": tool_name,
                    "params": tool_params,
                    "result": {"success": False, "error": str(e)},
                    "purpose": tool_step["purpose"]
                })
        
        # Analyze if we have enough information to answer the question
        return await self._analyze_and_synthesize_response(
            user_message, all_tool_results, conversation_history
        )
    
    def _resolve_dynamic_params(self, tool_params: Dict[str, Any], previous_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Resolve dynamic parameters based on previous tool results."""
        resolved_params = tool_params.copy()
        
        # Look for placeholder values that need to be resolved
        for param_key, param_value in tool_params.items():
            if isinstance(param_value, str):
                # Handle common placeholder patterns
                if param_value in ["id_of_the_found_message", "extracted_message_id"]:
                    # Look for message ID in previous Gmail search results
                    for prev_result in previous_results:
                        if prev_result["tool"] == "gmail_search" and prev_result["result"].get("success"):
                            # Extract message ID from Gmail search result
                            result_data = prev_result["result"]
                            if "response" in result_data:
                                # Try to extract message ID from response text
                                message_id = self._extract_message_id_from_response(result_data["response"])
                                if message_id:
                                    resolved_params[param_key] = message_id
                                    print(f"🔧 Resolved {param_key}: {param_value} → {message_id}")
                                    break
                
                elif "file_id" in param_value or "folder_id" in param_value:
                    # Handle Drive file/folder ID resolution
                    for prev_result in previous_results:
                        if "drive" in prev_result["tool"] and prev_result["result"].get("success"):
                            # Could extract file/folder IDs from Drive results
                            pass
        
        return resolved_params
    
    def _extract_message_id_from_response(self, response_text: str) -> str:
        """Extract Gmail message ID from search response text."""
        import re
        
        # Look for patterns like "Message ID: xyz123" or similar
        patterns = [
            r'Message ID:\s*([a-zA-Z0-9_-]+)',
            r'ID:\s*([a-zA-Z0-9_-]+)',
            r'"id":\s*"([a-zA-Z0-9_-]+)"',
            r'message_id:\s*([a-zA-Z0-9_-]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # If no specific pattern found, look for the first Gmail message ID format
        # Gmail message IDs are typically long alphanumeric strings
        match = re.search(r'\b([a-zA-Z0-9_-]{16,})\b', response_text)
        if match:
            potential_id = match.group(1)
            # Basic validation - Gmail message IDs are usually quite long
            if len(potential_id) >= 16:
                return potential_id
        
        return None
    
    async def _answer_from_existing_context(
        self, 
        user_message: str, 
        conversation_history: List[Dict[str, Any]]
    ) -> str:
        """Answer user's question using existing conversation context."""
        
        # For pronoun questions like "what are they?", we need the most recent context
        user_lower = user_message.lower()
        is_pronoun_question = any(pronoun in user_lower for pronoun in [
            "what are they", "what are those", "what are these", "tell me more about them",
            "what do they", "who are they", "where are they"
        ])
        
        # Extract relevant content from conversation history
        relevant_content = ""
        
        if is_pronoun_question:
            # For pronoun questions, get the last few assistant messages for better context
            print(f"🧠 Detected pronoun question, analyzing recent conversation context")
            recent_messages = []
            for msg in conversation_history[-4:]:  # Last 4 messages for pronoun resolution
                if msg.get("role") in ["assistant", "user"]:
                    role = msg.get("role")
                    content = msg.get("content", "")
                    recent_messages.append(f"{role.title()}: {content}")
            
            relevant_content = "\n\n".join(recent_messages)
        else:
            # For other questions, find the most relevant assistant response
            for msg in conversation_history:
                if msg.get("role") == "assistant" and len(msg.get("content", "")) > 100:
                    relevant_content = msg.get("content", "")
                    break
        
        if not relevant_content:
            return "I don't have enough context from our conversation to answer your question. Could you provide more details?"
        
        print(f"🧠 Analyzing existing context for user question (context length: {len(relevant_content)})")
        
        # Use LLM to answer based on existing content
        analysis_result = await self._analyze_content_with_llm(
            content=relevant_content,
            analysis_type="question_answering",
            user_query=user_message
        )
        
        if analysis_result and analysis_result.get("answer"):
            return analysis_result["answer"]
        elif analysis_result and analysis_result.get("raw_analysis"):
            return analysis_result["raw_analysis"]
        else:
            return "I have the relevant information but couldn't analyze it properly. Please rephrase your question."
    
    async def _analyze_and_synthesize_response(
        self,
        user_message: str,
        tool_results: List[Dict[str, Any]],
        conversation_history: List[Dict[str, Any]]
    ) -> str:
        """Analyze tool results and determine if they answer the user's question adequately."""
        
        # Combine all successful tool results
        combined_data = ""
        successful_tools = []
        
        for tool_result in tool_results:
            if tool_result["result"].get("success"):
                successful_tools.append(tool_result["tool"])
                if "response" in tool_result["result"]:
                    combined_data += f"\n--- {tool_result['tool']} result ---\n"
                    combined_data += str(tool_result["result"]["response"])
                    combined_data += "\n"
        
        if not combined_data:
            return "I tried to gather the information you requested, but the tools didn't return any useful data. Please try rephrasing your question."
        
        print(f"🧠 Analyzing tool results to answer user question (data length: {len(combined_data)})")
        
        # Use LLM to analyze if results answer the question
        analysis_result = await self._analyze_content_with_llm(
            content=combined_data,
            analysis_type="question_answering",
            user_query=user_message
        )
        
        print(f"🧠 LLM analysis result: {analysis_result}")
        
        if analysis_result and analysis_result.get("answer"):
            answer = analysis_result['answer']
            date_validation = analysis_result.get("date_validation", "")
            
            print(f"🧠 Extracted answer: {answer[:200]}...")
            print(f"🧠 Date validation: {date_validation}")
            
            # Check for date validation issues
            if date_validation and ("outdated" in date_validation.lower() or "invalid" in date_validation.lower()):
                return f"I found some calendar data, but it appears to be outdated: {answer}. {date_validation}. You may want to check your calendar for more recent events."
            else:
                return f"Based on the data I gathered using {', '.join(successful_tools)}: {answer}"
        elif analysis_result and analysis_result.get("raw_analysis"):
            print(f"🧠 Using raw analysis fallback")
            return analysis_result["raw_analysis"]
        else:
            print(f"🧠 No structured analysis available, providing raw data")
            return f"I gathered data using {', '.join(successful_tools)}, but couldn't analyze it to answer your specific question. Here's what I found:\n\n{combined_data[:500]}..."
    
    def _analyze_user_intent(self, message: str, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze user intent using context and natural language understanding."""
        
        message_lower = message.lower()
        
        # Get recent context
        recent_context = self._extract_recent_context(history)
        
        # Intent categories
        intent_analysis = {
            "primary_intent": "unknown",
            "confidence": 0.0,
            "context_type": None,
            "requires_data": False,
            "requires_analysis": False,
            "entities_mentioned": [],
            "action_type": "informational"
        }
        
        # Analysis patterns
        if any(pattern in message_lower for pattern in [
            "what do i need to do", "what should i do", "what are my next steps",
            "what action", "what's required", "what do i need to", "todo", "action items"
        ]):
            intent_analysis.update({
                "primary_intent": "action_planning",
                "confidence": 0.95,
                "requires_analysis": True,
                "action_type": "analysis"
            })
            
        elif any(pattern in message_lower for pattern in [
            "summarize", "what is this about", "key points", "main points", 
            "what's important", "analyze", "overview"
        ]):
            intent_analysis.update({
                "primary_intent": "content_analysis", 
                "confidence": 0.9,
                "requires_analysis": True,
                "action_type": "analysis"
            })
            
        elif any(pattern in message_lower for pattern in [
            "what is it about", "tell me more", "what does it say", "details",
            "what is the", "what does the", "about", "explain"
        ]):
            intent_analysis.update({
                "primary_intent": "content_inquiry",
                "confidence": 0.85,
                "requires_analysis": True,
                "action_type": "explanation"
            })
            
        elif any(pattern in message_lower for pattern in [
            "show me", "get me", "find", "search", "latest", "recent"
        ]):
            intent_analysis.update({
                "primary_intent": "data_retrieval",
                "confidence": 0.8,
                "requires_data": True,
                "action_type": "retrieval"
            })
        
        # Determine context type from history
        if recent_context["has_email_content"]:
            intent_analysis["context_type"] = "email"
            intent_analysis["entities_mentioned"] = recent_context["entities"]
            
            # CRITICAL: If we have email content and user is asking about it, 
            # override data_retrieval with content_inquiry to analyze existing context
            if (intent_analysis["primary_intent"] == "data_retrieval" and 
                any(pattern in message_lower for pattern in [
                    "about", "what is", "what does", "tell me about", "jubilo", "email about"
                ])):
                intent_analysis.update({
                    "primary_intent": "content_inquiry",
                    "confidence": 0.9,
                    "requires_data": False,
                    "requires_analysis": True,
                    "action_type": "explanation"
                })
                
        elif recent_context["has_drive_content"]:
            intent_analysis["context_type"] = "drive"
        elif recent_context["has_calendar_content"]:
            intent_analysis["context_type"] = "calendar"
            
        return intent_analysis
    
    def _extract_recent_context(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract context from recent conversation history."""
        context = {
            "has_email_content": False,
            "has_drive_content": False, 
            "has_calendar_content": False,
            "entities": [],
            "recent_topics": []
        }
        
        # Look at last 3 messages
        recent_messages = history[-3:] if len(history) > 3 else history
        
        for msg in recent_messages:
            content = msg.get("content", "").lower()
            
            if any(keyword in content for keyword in ["email", "gmail", "message", "inbox"]):
                context["has_email_content"] = True
                
                # Extract entities like company names, project names
                entities = self._extract_entities_from_text(msg.get("content", ""))
                context["entities"].extend(entities)
        
        return context
    
    def _extract_entities_from_text(self, text: str) -> List[str]:
        """Extract entities from text content."""
        entities = []
        
        # Look for Jubilo, company names, project names
        patterns = [
            r'\b(Jubilo[^,\n]*)',
            r'\b([A-Z][a-z]+\s+[A-Z][a-z]+)\s+(?:proposal|project|contract)',
            r'Re:\s*([^,\n]+?)(?:\s+2025|\s+-)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            entities.extend(matches)
        
        return list(set([e.strip() for e in entities if len(e) > 2]))[:3]
    
    def _create_action_plan(self, intent: Dict[str, Any], history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create an action plan based on user intent."""
        
        plan = {
            "steps": [],
            "expected_outcome": "",
            "requires_tools": []
        }
        
        if intent["primary_intent"] == "action_planning":
            # User wants to know what actions to take
            if intent["context_type"] == "email":
                # If we have existing email context, analyze that directly
                plan.update({
                    "steps": [
                        {
                            "action": "analyze_for_actions",
                            "tool": "internal_analysis",
                            "params": {},
                            "purpose": "Extract action items and next steps from existing email context"
                        }
                    ],
                    "expected_outcome": "List of specific actions user needs to take",
                    "requires_tools": []
                })
            else:
                # No email context, need to fetch emails first
                query_terms = intent["entities_mentioned"] if intent["entities_mentioned"] else ["recent emails"]
                plan.update({
                    "steps": [
                        {
                            "action": "retrieve_context_emails",
                            "tool": "gmail_search", 
                            "params": {"query": " ".join(query_terms)},
                            "purpose": "Get relevant email content for action analysis"
                        },
                        {
                            "action": "analyze_for_actions",
                            "tool": "internal_analysis",
                            "params": {},
                            "purpose": "Extract action items and next steps from emails"
                        }
                    ],
                    "expected_outcome": "List of specific actions user needs to take",
                    "requires_tools": ["gmail_search"]
                })
            
        elif intent["primary_intent"] == "content_analysis":
            # User wants content summarized or analyzed
            if intent["context_type"] == "email":
                plan.update({
                    "steps": [
                        {
                            "action": "analyze_existing_context", 
                            "tool": "internal_analysis",
                            "params": {},
                            "purpose": "Analyze email content from conversation context"
                        }
                    ],
                    "expected_outcome": "Summary of key points and insights",
                    "requires_tools": []
                })
                
        elif intent["primary_intent"] == "content_inquiry":
            # User wants explanation/details about existing content
            if intent["context_type"] == "email":
                plan.update({
                    "steps": [
                        {
                            "action": "analyze_existing_context", 
                            "tool": "internal_analysis",
                            "params": {},
                            "purpose": "Explain specific content from conversation context"
                        }
                    ],
                    "expected_outcome": "Detailed explanation of requested content",
                    "requires_tools": []
                })
            
        elif intent["primary_intent"] == "data_retrieval":
            # User wants to fetch new data
            plan.update({
                "steps": [
                    {
                        "action": "fetch_data",
                        "tool": "gmail_search" if "email" in intent.get("context_type", "") else "gmail_recent",
                        "params": {"max_results": 5},
                        "purpose": "Retrieve requested data"
                    }
                ],
                "expected_outcome": "Requested data formatted for user",
                "requires_tools": ["gmail_search"]
            })
            
        return plan
    
    async def _execute_action_plan(self, plan: Dict[str, Any], user_id: str, mcp_client) -> List[Dict[str, Any]]:
        """Execute the action plan step by step."""
        results = []
        
        for step in plan["steps"]:
            print(f"🧠 Executing step: {step['action']}")
            
            if step["tool"] == "gmail_search":
                # Execute Gmail search
                result = await mcp_client.call_tool("gmail_search", {
                    **step["params"],
                    "user_id": user_id
                })
                results.append({
                    "step": step["action"],
                    "tool_used": "gmail_search",
                    "success": result.get("success", False),
                    "data": result.get("response", ""),
                    "purpose": step["purpose"]
                })
                
            elif step["tool"] == "gmail_recent":
                # Execute Gmail recent
                result = await mcp_client.call_tool("gmail_recent", {
                    **step["params"],
                    "user_id": user_id
                })
                results.append({
                    "step": step["action"],
                    "tool_used": "gmail_recent", 
                    "success": result.get("success", False),
                    "data": result.get("response", ""),
                    "purpose": step["purpose"]
                })
                
            elif step["tool"] == "internal_analysis":
                # Internal analysis step
                results.append({
                    "step": step["action"],
                    "tool_used": "internal_analysis",
                    "success": True,
                    "data": "ready_for_analysis",
                    "purpose": step["purpose"]
                })
        
        return results
    
    async def _synthesize_response(
        self, 
        intent: Dict[str, Any], 
        plan: Dict[str, Any], 
        results: List[Dict[str, Any]], 
        original_message: str,
        conversation_history: List[Dict[str, Any]]
    ) -> str:
        """Synthesize final intelligent response based on all analysis."""
        
        if intent["primary_intent"] == "action_planning":
            return await self._generate_action_response(results, original_message, conversation_history)
        elif intent["primary_intent"] == "content_analysis":
            return await self._generate_analysis_response(results, original_message, conversation_history)
        elif intent["primary_intent"] == "content_inquiry":
            return await self._generate_explanation_response(results, original_message, conversation_history)
        elif intent["primary_intent"] == "data_retrieval":
            return self._generate_data_response(results, original_message)
        else:
            return "I understand you're asking something, but I need more context to provide a helpful response."
    
    async def _generate_action_response(self, results: List[Dict[str, Any]], original_message: str, conversation_history: List[Dict[str, Any]]) -> str:
        """Generate action-focused response with LLM-powered intelligent analysis."""
        
        # Look for email data in results
        email_data = ""
        for result in results:
            if result.get("tool_used") == "gmail_search" and result.get("success"):
                email_data = result.get("data", "")
                break
        
        # CRITICAL: If no email data from tools, use conversation history
        if not email_data:
            # Extract email content from conversation history
            for msg in conversation_history:
                if msg.get("role") == "assistant" and "Email Summary" in msg.get("content", ""):
                    email_data = msg.get("content", "")
                    print(f"🧠 Using conversation history for action analysis")
                    break
            
            if not email_data:
                return "I don't have enough context to determine what actions you need to take. Could you provide more details?"
        
        print(f"🧠 Using LLM to intelligently analyze email content for action items (length: {len(email_data)})")
        
        # Use LLM to intelligently analyze email content for action items
        analysis_result = await self._analyze_content_with_llm(
            content=email_data,
            analysis_type="action_extraction",
            user_query=original_message
        )
        
        if analysis_result and analysis_result.get("actions"):
            actions = analysis_result["actions"]
            response = f"Based on your email correspondence, here's what you need to do:\n\n"
            
            for i, action in enumerate(actions, 1):
                priority_emoji = "🔥" if action.get("priority") == "high" else "⚡" if action.get("priority") == "medium" else "💡"
                response += f"{i}. {priority_emoji} **{action['action']}**\n"
                response += f"   📝 {action['details']}\n"
                if action.get("deadline"):
                    response += f"   ⏰ Deadline: {action['deadline']}\n"
                response += "\n"
            
            return response
        else:
            return "I analyzed your emails but couldn't identify specific action items. The content might need your personal review to determine next steps."
    
    async def _generate_analysis_response(self, results: List[Dict[str, Any]], original_message: str, conversation_history: List[Dict[str, Any]]) -> str:
        """Generate analytical summary response using LLM intelligence."""
        
        # Look for content data in results
        content_data = ""
        for result in results:
            if result.get("success") and result.get("data"):
                content_data = result.get("data", "")
                break
        
        if not content_data:
            return "I don't have enough content to analyze. Please provide more context."
        
        print(f"🧠 Using LLM to generate intelligent analysis")
        
        # Use LLM for intelligent content analysis
        analysis_result = await self._analyze_content_with_llm(
            content=content_data,
            analysis_type="content_summary",
            user_query=original_message
        )
        
        if analysis_result:
            if analysis_result.get("raw_analysis"):
                return f"📊 **Analysis Summary**:\n\n{analysis_result['raw_analysis']}"
            elif analysis_result.get("summary"):
                return f"📊 **Analysis Summary**:\n\n{analysis_result['summary']}"
        
        return "I analyzed the content but couldn't generate a clear summary. Please ask for something more specific."
    
    async def _generate_explanation_response(self, results: List[Dict[str, Any]], original_message: str, conversation_history: List[Dict[str, Any]]) -> str:
        """Generate explanatory response using LLM intelligence."""
        
        # Look for content data in results  
        content_data = ""
        for result in results:
            if result.get("success") and result.get("data") and result.get("data") != "ready_for_analysis":
                content_data = result.get("data", "")
                break
        
        # CRITICAL: If no content from tools but we have conversation history, use that
        if not content_data:
            # Extract email content from conversation history
            for msg in conversation_history:
                if msg.get("role") == "assistant" and "Email Summary" in msg.get("content", ""):
                    content_data = msg.get("content", "")
                    print(f"🧠 Using conversation history content for analysis")
                    break
            
            if not content_data:
                return "I don't have enough content to explain. Please provide more context."
        
        print(f"🧠 Using LLM to generate intelligent explanation")
        
        # Use LLM for intelligent explanation
        analysis_result = await self._analyze_content_with_llm(
            content=content_data,
            analysis_type="content_summary", 
            user_query=original_message
        )
        
        if analysis_result:
            if analysis_result.get("raw_analysis"):
                return f"💡 **Explanation**:\n\n{analysis_result['raw_analysis']}"
            elif analysis_result.get("summary"):
                return f"💡 **Explanation**:\n\n{analysis_result['summary']}"
        
        return "I reviewed the content but couldn't provide a clear explanation. Please ask for something more specific."
    
    def _generate_data_response(self, results: List[Dict[str, Any]], original_message: str) -> str:
        """Generate data-focused response."""
        for result in results:
            if result.get("success") and result.get("data"):
                return result.get("data", "")
        
        return "I couldn't retrieve the requested information. Please try again or be more specific."
    
    async def _analyze_content_with_llm(
        self, 
        content: str, 
        analysis_type: str, 
        user_query: str
    ) -> Dict[str, Any]:
        """Use LLM to intelligently analyze content based on user intent."""
        
        import httpx
        import os
        import json
        
        # Get API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("❌ No OpenAI API key found for LLM analysis")
            return {}
        
        # Create analysis prompt based on type
        if analysis_type == "action_extraction":
            system_prompt = """You are an expert business analyst. Analyze email content and extract specific, actionable items the user needs to take. 

Return your analysis as a JSON object with this structure:
{
  "actions": [
    {
      "action": "Brief action title",
      "details": "Specific details of what needs to be done",
      "priority": "high|medium|low",
      "deadline": "deadline if mentioned, null otherwise",
      "context": "relevant business context"
    }
  ],
  "summary": "Brief overall summary"
}

Focus on:
- Specific actions the user must take
- Business deadlines and urgency
- Required information or responses
- Meeting preparations or follow-ups
- Contract, legal, or financial actions"""

            user_prompt = f"""User asked: "{user_query}"

Analyze this email content and extract actionable items:

{content}

Return JSON with specific actions the user needs to take."""

        elif analysis_type == "content_summary":
            system_prompt = """You are an expert at analyzing and summarizing business communications. Extract key information, main points, and important context."""
            
            user_prompt = f"""User asked: "{user_query}"

Summarize and analyze this content:

{content}"""

        elif analysis_type == "tool_planning":
            # For tool planning, the content is actually the system prompt
            system_prompt = content
            user_prompt = f"Plan the tool usage for: {user_query}"

        elif analysis_type == "question_answering":
            import datetime
            current_date = datetime.datetime.now().strftime("%Y-%m-%d")
            current_year = datetime.datetime.now().year
            
            system_prompt = f"""You are an intelligent assistant that answers questions based on provided content. Be accurate, specific, and helpful.

IMPORTANT: Today's date is {current_date} ({current_year}). Always validate dates and times for relevance.

When analyzing content:
- For EMAIL content: If user asks for "comments", look for feedback, reviews, notes, or discussion content
- For CALENDAR content: When user asks about "next meeting" or upcoming events, only return events that are:
  * In the FUTURE (after today's date {current_date})
  * Within a reasonable timeframe (next few weeks/months)
  * If all events are in the past, clearly state "no upcoming meetings found"
- For any dated content: Check if dates make sense given today's date
- Be thorough in analyzing the full content, not just summaries

Return your response as JSON:
{{
  "answer": "Direct answer to the user's question with specific details",
  "confidence": "high|medium|low",
  "key_points": ["key point 1", "key point 2", ...],
  "additional_context": "any relevant additional information",
  "date_validation": "valid|invalid|outdated - explain any date issues found"
}}"""
            
            user_prompt = f"""User Question: "{user_query}"

Email Content/Data:
{content}

Analyze the email content thoroughly and answer the user's question with specific information from the emails."""
        
        else:
            return {}
        
        try:
            # Make API call to OpenAI
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4o-mini",  # Fast and cost-effective for analysis
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": 0.1,  # Low temperature for consistent analysis
                        "max_tokens": 1000
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    
                    # Try to parse JSON response (handle markdown code blocks)
                    try:
                        # Remove markdown code block formatting if present
                        if content.startswith("```json"):
                            content = content.replace("```json", "").replace("```", "").strip()
                        elif content.startswith("```"):
                            content = content.replace("```", "").strip()
                        
                        # Remove JavaScript-style comments that break JSON parsing
                        import re
                        # Remove single-line comments: // comment
                        content = re.sub(r'//.*', '', content)
                        # Remove multi-line comments: /* comment */
                        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
                        
                        return json.loads(content)
                    except json.JSONDecodeError:
                        print(f"❌ Failed to parse LLM JSON response: {content}")
                        # Fallback: return raw content
                        return {"raw_analysis": content}
                else:
                    print(f"❌ LLM API error: {response.status_code} - {response.text}")
                    return {}
                    
        except Exception as e:
            print(f"❌ Error in LLM analysis: {e}")
            return {}
    
    async def _evaluate_and_learn(
        self,
        user_question: str,
        ai_response: str,
        approach: str,
        tools_used: List[str],
        start_time: float,
        user_id: str,
        classification: Dict[str, Any]
    ) -> None:
        """Evaluate response quality and update analytics asynchronously."""
        
        try:
            from .response_evaluator import response_evaluator
            from .tool_analytics import tool_analytics
            
            # Calculate response time
            response_time = time.time() - start_time
            
            # Evaluate response quality
            evaluation = await response_evaluator.evaluate_response_quality(
                user_question, ai_response, tools_used, approach=approach
            )
            
            print(f"📊 Response evaluation: {evaluation['evaluation']} (score: {evaluation['quality_score']:.2f})")
            
            # Log approach effectiveness
            tool_analytics.log_approach_effectiveness(approach, evaluation["quality_score"])
            
            # Log tool usage if tools were used
            for tool_name in tools_used:
                tool_analytics.log_tool_usage(
                    tool_name=tool_name,
                    user_id=user_id,
                    user_query=user_question,
                    parameters={"approach": approach},
                    result={"success": True, "response": ai_response},
                    response_time=response_time,
                    approach=approach,
                    classification=classification
                )
            
            # Check if we should suggest a better approach for poor results
            if evaluation["quality_score"] < 0.4:
                suggestions = await response_evaluator.suggest_better_approach(
                    user_question, approach, tools_used, evaluation
                )
                
                if suggestions.get("alternative_approach"):
                    print(f"💡 Suggestion: Try {suggestions['alternative_approach']} approach next time")
                    print(f"💡 Reasoning: {suggestions['reasoning']}")
            
            # Log classification accuracy (simplified - assumes good response = correct classification)
            was_classification_correct = evaluation["quality_score"] > 0.6
            tool_analytics.log_classification_result(
                classification, approach, was_classification_correct
            )
            
        except Exception as e:
            print(f"❌ Error in evaluation and learning: {e}")
    
    async def _log_classification_decision(
        self,
        classification: Dict[str, Any],
        chosen_approach: str,
        start_time: float,
        user_id: str
    ) -> None:
        """Log classification decision for analytics."""
        
        try:
            from .tool_analytics import tool_analytics
            
            response_time = time.time() - start_time
            
            # Log classification result (assume it's correct for now)
            tool_analytics.log_classification_result(
                classification, chosen_approach, True  # We'll update this after evaluation
            )
            
            print(f"📊 Logged classification decision: {classification['classification']} -> {chosen_approach}")
            
        except Exception as e:
            print(f"❌ Error logging classification: {e}")
    
    def _get_user_settings(self, user_id: str):
        """Get user agent settings with defaults."""
        try:
            # Import here to avoid circular imports
            from ..api.v1.agent_settings import get_user_agent_settings
            return get_user_agent_settings(user_id)
        except Exception as e:
            print(f"❌ Error getting user settings, using defaults: {e}")
            # Return default settings
            from ..api.v1.agent_settings import AgentSettings, ToolPreferences, ClassificationPreferences
            return AgentSettings(
                tool_preferences=ToolPreferences(),
                classification_preferences=ClassificationPreferences(),
                analytics_enabled=True
            )
    
    def _filter_tools_by_preferences(self, suggested_tools: List[str], user_settings) -> List[str]:
        """Filter tools based on user preferences."""
        allowed_tools = []
        
        for tool in suggested_tools:
            # Check tool-specific preferences
            if "gmail" in tool.lower() and not user_settings.tool_preferences.enable_gmail_tools:
                print(f"🔒 Gmail tool {tool} disabled by user preference")
                continue
            elif "drive" in tool.lower() and not user_settings.tool_preferences.enable_drive_tools:
                print(f"🔒 Drive tool {tool} disabled by user preference")
                continue
            elif "calendar" in tool.lower() and not user_settings.tool_preferences.enable_calendar_tools:
                print(f"🔒 Calendar tool {tool} disabled by user preference")
                continue
            
            allowed_tools.append(tool)
        
        # Apply tool usage approach preference
        approach = user_settings.tool_preferences.preferred_approach
        
        if approach == "conservative":
            # Only use the most relevant tool
            allowed_tools = allowed_tools[:1] if allowed_tools else []
        elif approach == "aggressive":
            # Use all allowed tools
            pass  # Already have all allowed tools
        # "balanced" is the default behavior
        
        return allowed_tools
    
    async def _answer_with_llm_only(self, user_message: str, conversation_history: List[Dict[str, Any]]) -> str:
        """Answer using LLM knowledge only, without any tools."""
        
        # Format the conversation for the LLM
        messages = []
        
        # Add recent conversation history for context
        for msg in conversation_history[-5:]:  # Last 5 messages for context
            if msg.get("role") in ["user", "assistant"]:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        # Add current user message
        messages.append({
            "role": "user", 
            "content": user_message
        })
        
        # Use the existing LLM analysis method but for direct answering
        try:
            system_prompt = """You are a knowledgeable AI assistant. Answer the user's question directly using your training knowledge. Do not use any external tools or data sources. Provide a clear, helpful, and accurate response based on your knowledge.

For questions about current events, sports scores, weather, or other time-sensitive information, acknowledge that your information might not be current and suggest where they could find the latest information if needed."""

            import httpx
            import os
            
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return "I'm sorry, I'm not able to access my knowledge base at the moment. Please try again later."
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": system_prompt}
                        ] + messages,
                        "temperature": 0.7,
                        "max_tokens": 500
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    print(f"❌ LLM API error: {response.status_code}")
                    return "I'm having trouble accessing my knowledge base at the moment. Please try again."
                    
        except Exception as e:
            print(f"❌ Error in direct LLM answer: {e}")
            return "I encountered an error while processing your question. Please try again."
    
    async def _answer_with_current_info_acknowledgment(self, user_message: str, conversation_history: List[Dict[str, Any]]) -> str:
        """Handle current information queries with proper acknowledgment that data might not be current."""
        
        # Extract what kind of current info they're asking about
        message_lower = user_message.lower()
        
        # Sports/competition current info
        if any(word in message_lower for word in ["scorer", "player", "team", "ranking", "leader"]):
            if any(word in message_lower for word in ["2025", "season", "current", "so far", "latest"]):
                return f"I don't have access to real-time sports data, so I can't tell you who the current top scorer is for the 2025 season. For the most up-to-date sports statistics and rankings, I'd recommend checking:\n\n• Official league websites\n• Sports news sites like ESPN or BBC Sport\n• Sports data platforms like ESPN FC or similar\n\nThese sources will have the latest standings, player statistics, and current season information."
        
        # News/current events
        if any(word in message_lower for word in ["news", "latest", "current events", "today", "recent"]):
            return "I don't have access to real-time news or current events. For the latest news, please check:\n\n• Major news websites (BBC, CNN, Reuters, etc.)\n• News aggregators (Google News, Apple News)\n• Local news sources for regional updates\n\nThese will have the most current and up-to-date information."
        
        # Weather
        if any(word in message_lower for word in ["weather", "temperature", "forecast", "climate"]):
            return "I don't have access to current weather data. For accurate weather information, please check:\n\n• Weather.com or your local weather service\n• Weather apps on your device\n• Local meteorological services\n\nThese sources provide real-time weather updates and forecasts."
        
        # Stock/financial current info  
        if any(word in message_lower for word in ["stock", "price", "market", "trading", "financial"]):
            return "I don't have access to real-time financial data. For current stock prices and market information, please check:\n\n• Financial news sites (Bloomberg, Yahoo Finance, MarketWatch)\n• Your broker's platform\n• Financial data providers\n\nThese sources provide real-time market data and analysis."
        
        # Generic current info
        return f"I understand you're asking for current information, but I don't have access to real-time data sources. For the most up-to-date information about your query, I'd recommend:\n\n• Checking official websites or sources related to your topic\n• Using web search engines for the latest information\n• Consulting news sources or specialized platforms\n\nThis will ensure you get the most current and accurate information available."


# Global instance
master_agent = MasterAgent()
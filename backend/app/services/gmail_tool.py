"""
Gmail Tool for Agentic Chatbot Integration

This module provides Gmail API functionality as a tool that can be called by the agentic chatbot.
It allows the chatbot to interact with Gmail on behalf of users for reading, searching, and analyzing emails.
"""

from __future__ import annotations

import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import re

from .google_oauth import google_oauth_service


class GmailTool:
    """Gmail tool for agentic chatbot integration."""
    
    def __init__(self):
        self.name = "gmail"
        self.description = "Access and analyze Gmail messages. Can search, read, and analyze emails."
        
    def get_tool_definition(self) -> Dict[str, Any]:
        """Get the tool definition for OpenAI function calling."""
        return {
            "type": "function",
            "name": "gmail",
            "description": "Access and analyze Gmail messages. Can search, read, and analyze emails.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["search", "read", "analyze", "summarize", "find_recent", "find_important"],
                        "description": "The action to perform on Gmail"
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query for Gmail (e.g., 'from:john@example.com', 'subject:meeting', 'is:unread')"
                    },
                    "message_id": {
                        "type": "string",
                        "description": "Specific message ID to read (required for 'read' action)"
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 10,
                        "description": "Maximum number of messages to return"
                    },
                    "time_range": {
                        "type": "string",
                        "enum": ["today", "yesterday", "week", "month", "year", "all"],
                        "default": "all",
                        "description": "Time range for searching messages"
                    },
                    "analysis_type": {
                        "type": "string",
                        "enum": ["sentiment", "topics", "senders", "frequency", "summary"],
                        "description": "Type of analysis to perform (for 'analyze' action)"
                    }
                },
                "required": ["action"]
            }
        }
    
    async def execute(self, user_id: str, **kwargs) -> Dict[str, Any]:
        """Execute the Gmail tool with the given parameters."""
        try:
            action = kwargs.get("action")
            
            if action == "search":
                return await self._search_emails(user_id, **kwargs)
            elif action == "read":
                return await self._read_message(user_id, **kwargs)
            elif action == "analyze":
                return await self._analyze_emails(user_id, **kwargs)
            elif action == "summarize":
                return await self._summarize_emails(user_id, **kwargs)
            elif action == "find_recent":
                return await self._find_recent_emails(user_id, **kwargs)
            elif action == "find_important":
                return await self._find_important_emails(user_id, **kwargs)
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}",
                    "available_actions": ["search", "read", "analyze", "summarize", "find_recent", "find_important"]
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Gmail tool error: {str(e)}"
            }
    
    async def _search_emails(self, user_id: str, **kwargs) -> Dict[str, Any]:
        """Search for emails based on query."""
        query = kwargs.get("query", "")
        max_results = kwargs.get("max_results", 10)
        time_range = kwargs.get("time_range", "all")
        
        # Build enhanced query with time range
        enhanced_query = self._build_enhanced_query(query, time_range)
        
        # Get user's Google credentials
        credentials = self._get_user_credentials(user_id)
        
        # Search for messages
        result = await google_oauth_service.get_gmail_messages(
            credentials=credentials,
            query=enhanced_query,
            max_results=max_results
        )
        
        if "error" in result:
            return {
                "success": False,
                "error": result["error"],
                "action": "search"
            }
        
        messages = result.get("messages", [])
        
        return {
            "success": True,
            "action": "search",
            "query": enhanced_query,
            "total_found": len(messages),
            "messages": messages,
            "summary": f"Found {len(messages)} messages matching '{query}'"
        }
    
    async def _read_message(self, user_id: str, **kwargs) -> Dict[str, Any]:
        """Read a specific email message."""
        message_id = kwargs.get("message_id")
        
        if not message_id:
            return {
                "success": False,
                "error": "message_id is required for 'read' action"
            }
        
        # Get user's Google credentials
        credentials = self._get_user_credentials(user_id)
        
        # Get message content
        result = await google_oauth_service.get_gmail_message_content(
            credentials=credentials,
            message_id=message_id
        )
        
        if "error" in result:
            return {
                "success": False,
                "error": result["error"],
                "action": "read"
            }
        
        return {
            "success": True,
            "action": "read",
            "message_id": message_id,
            "message": result,
            "summary": f"Retrieved message {message_id}"
        }
    
    async def _analyze_emails(self, user_id: str, **kwargs) -> Dict[str, Any]:
        """Analyze emails for patterns, sentiment, etc."""
        query = kwargs.get("query", "")
        max_results = kwargs.get("max_results", 20)
        analysis_type = kwargs.get("analysis_type", "summary")
        time_range = kwargs.get("time_range", "month")
        
        # Build enhanced query
        enhanced_query = self._build_enhanced_query(query, time_range)
        
        # Get user's Google credentials
        credentials = self._get_user_credentials(user_id)
        
        # Get messages for analysis
        result = await google_oauth_service.get_gmail_messages(
            credentials=credentials,
            query=enhanced_query,
            max_results=max_results
        )
        
        if "error" in result:
            return {
                "success": False,
                "error": result["error"],
                "action": "analyze"
            }
        
        messages = result.get("messages", [])
        
        # Perform analysis based on type
        if analysis_type == "senders":
            analysis = self._analyze_senders(messages)
        elif analysis_type == "topics":
            analysis = self._analyze_topics(messages)
        elif analysis_type == "frequency":
            analysis = self._analyze_frequency(messages)
        elif analysis_type == "sentiment":
            analysis = self._analyze_sentiment(messages)
        else:  # summary
            analysis = self._analyze_summary(messages)
        
        return {
            "success": True,
            "action": "analyze",
            "analysis_type": analysis_type,
            "query": enhanced_query,
            "messages_analyzed": len(messages),
            "analysis": analysis,
            "summary": f"Analyzed {len(messages)} messages for {analysis_type}"
        }
    
    async def _summarize_emails(self, user_id: str, **kwargs) -> Dict[str, Any]:
        """Summarize recent emails."""
        query = kwargs.get("query", "")
        max_results = kwargs.get("max_results", 10)
        time_range = kwargs.get("time_range", "week")
        
        # Build enhanced query
        enhanced_query = self._build_enhanced_query(query, time_range)
        
        # Get user's Google credentials
        credentials = self._get_user_credentials(user_id)
        
        # Get messages
        result = await google_oauth_service.get_gmail_messages(
            credentials=credentials,
            query=enhanced_query,
            max_results=max_results
        )
        
        if "error" in result:
            return {
                "success": False,
                "error": result["error"],
                "action": "summarize"
            }
        
        messages = result.get("messages", [])
        
        # Create summary
        summary = self._create_email_summary(messages)
        
        return {
            "success": True,
            "action": "summarize",
            "query": enhanced_query,
            "messages_summarized": len(messages),
            "summary": summary,
            "key_messages": messages[:5]  # Top 5 most relevant
        }
    
    async def _find_recent_emails(self, user_id: str, **kwargs) -> Dict[str, Any]:
        """Find recent emails."""
        max_results = kwargs.get("max_results", 10)
        
        # Get user's Google credentials
        credentials = self._get_user_credentials(user_id)
        
        # Get recent messages (newer:2024/01/01 ensures recent messages)
        result = await google_oauth_service.get_gmail_messages(
            credentials=credentials,
            query="newer:2024/01/01",
            max_results=max_results
        )
        
        if "error" in result:
            return {
                "success": False,
                "error": result["error"],
                "action": "find_recent"
            }
        
        messages = result.get("messages", [])
        
        return {
            "success": True,
            "action": "find_recent",
            "messages_found": len(messages),
            "messages": messages,
            "summary": f"Found {len(messages)} recent messages"
        }
    
    async def _find_important_emails(self, user_id: str, **kwargs) -> Dict[str, Any]:
        """Find important emails (starred, from important contacts, etc.)."""
        max_results = kwargs.get("max_results", 10)
        
        # Get user's Google credentials
        credentials = self._get_user_credentials(user_id)
        
        # Search for important messages
        result = await google_oauth_service.get_gmail_messages(
            credentials=credentials,
            query="is:important OR is:starred OR label:important",
            max_results=max_results
        )
        
        if "error" in result:
            return {
                "success": False,
                "error": result["error"],
                "action": "find_important"
            }
        
        messages = result.get("messages", [])
        
        return {
            "success": True,
            "action": "find_important",
            "messages_found": len(messages),
            "messages": messages,
            "summary": f"Found {len(messages)} important messages"
        }
    
    def _get_user_credentials(self, user_id: str):
        """Get Google credentials for a user."""
        try:
            # Import here to avoid circular imports
            from ..api.v1.google_api import get_user_google_credentials
            return get_user_google_credentials(user_id)
        except Exception as e:
            print(f"❌ Error getting Google credentials for user {user_id}: {e}")
            raise Exception(f"I need access to your Google account to read Gmail. Please visit http://localhost:3005/test-google.html to authenticate with Google first, then try your request again.")
    
    def _build_enhanced_query(self, query: str, time_range: str) -> str:
        """Build enhanced Gmail search query with time range."""
        enhanced_query = query
        
        # Add time range filters
        if time_range == "today":
            enhanced_query += " newer:2024/01/01"  # This would need to be dynamic
        elif time_range == "week":
            enhanced_query += " newer:2024/01/01"  # This would need to be dynamic
        elif time_range == "month":
            enhanced_query += " newer:2024/01/01"  # This would need to be dynamic
        elif time_range == "year":
            enhanced_query += " newer:2024/01/01"  # This would need to be dynamic
        
        return enhanced_query.strip()
    
    def _analyze_senders(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze email senders."""
        senders = {}
        for msg in messages:
            sender = msg.get("from", "Unknown")
            if sender not in senders:
                senders[sender] = 0
            senders[sender] += 1
        
        # Sort by frequency
        sorted_senders = sorted(senders.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "total_senders": len(senders),
            "top_senders": sorted_senders[:10],
            "most_frequent": sorted_senders[0] if sorted_senders else None
        }
    
    def _analyze_topics(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze email topics/subjects."""
        subjects = [msg.get("subject", "") for msg in messages if msg.get("subject")]
        
        # Simple keyword extraction (in a real implementation, you'd use NLP)
        all_words = []
        for subject in subjects:
            words = re.findall(r'\b\w+\b', subject.lower())
            all_words.extend(words)
        
        # Count word frequency
        word_count = {}
        for word in all_words:
            if len(word) > 3:  # Filter out short words
                word_count[word] = word_count.get(word, 0) + 1
        
        # Sort by frequency
        sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "total_subjects": len(subjects),
            "common_words": sorted_words[:15],
            "sample_subjects": subjects[:5]
        }
    
    def _analyze_frequency(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze email frequency patterns."""
        # This would analyze when emails are received
        # For now, return basic stats
        return {
            "total_messages": len(messages),
            "analysis": "Email frequency analysis would show patterns of when you receive emails"
        }
    
    def _analyze_sentiment(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze email sentiment."""
        # This would use NLP to analyze sentiment
        # For now, return basic info
        return {
            "total_messages": len(messages),
            "analysis": "Sentiment analysis would show the emotional tone of your emails"
        }
    
    def _analyze_summary(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create a general summary of emails."""
        total_messages = len(messages)
        unread_count = sum(1 for msg in messages if "unread" in msg.get("snippet", "").lower())
        
        # Get unique senders
        senders = set(msg.get("from", "Unknown") for msg in messages)
        
        return {
            "total_messages": total_messages,
            "unique_senders": len(senders),
            "unread_estimate": unread_count,
            "date_range": "Recent messages",
            "summary": f"Found {total_messages} messages from {len(senders)} unique senders"
        }
    
    def _create_email_summary(self, messages: List[Dict[str, Any]]) -> str:
        """Create a human-readable summary of emails."""
        if not messages:
            return "No messages found."
        
        total = len(messages)
        senders = set(msg.get("from", "Unknown") for msg in messages)
        
        # Get recent subjects
        recent_subjects = [msg.get("subject", "No subject") for msg in messages[:5]]
        
        summary = f"Found {total} messages from {len(senders)} unique senders. "
        
        if recent_subjects:
            summary += f"Recent topics include: {', '.join(recent_subjects[:3])}"
        
        return summary


# Global instance
gmail_tool = GmailTool()

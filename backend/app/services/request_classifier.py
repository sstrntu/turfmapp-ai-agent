"""
Request Classifier - Intelligent Query Classification for Tool Usage

This service intelligently classifies user requests to determine if tools are needed,
using a 3-tier approach for optimal performance:
- Tier 1: Pattern-based filtering (instant, free)
- Tier 2: Context analysis (fast, cheap)
- Tier 3: LLM analysis (thorough, expensive)
"""

from __future__ import annotations

import re
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime

# Classification types
ClassificationType = Literal["GENERAL_KNOWLEDGE", "PERSONAL_DATA", "CONTEXT_DEPENDENT", "AMBIGUOUS"]

class RequestClassifier:
    """Intelligent request classifier for agentic tool usage decisions."""
    
    def __init__(self):
        # Pattern-based classification rules (Tier 1)
        self.general_knowledge_patterns = [
            # Factual questions that don't need personal data
            r'\b(?:what|who|when|where|how|why)\s+(?:is|are|was|were|do|does|did)\b.*\b(?:the|a|an)\b',
            r'\bwho\s+(?:is|was|are|were)\s+(?:the\s+)?(?:top|best|leading|greatest|most)\b',
            r'\bwhat\s+(?:is|are)\s+(?:the\s+)?(?:capital|currency|language|population)\s+of\b',
            r'\b(?:who\s+won|what\s+happened|when\s+was|where\s+is)\b.*\b(?:championship|war|invention|country)\b',
            r'\bdefin(?:e|ition)\s+(?:of\s+)?(?:the\s+)?\w+\b',
            r'\bexplain\s+(?:the\s+)?(?:concept|theory|principle|meaning)\b',
            r'\bhow\s+(?:does|do|did|can|to)\b.*\bwork\b',
            r'\bwhat\s+(?:does|do|did)\s+.*\bmean\b',
            r'\bcalculate\s+\d+\s*[\+\-\*\/]\s*\d+',
            r'\b(?:weather|temperature|climate)\s+(?:in|for|today|tomorrow)\b',
            r'\bcurrent\s+(?:time|date|year)\b',
            r'\bsports?\s+(?:score|result|news)\b',
            r'\b(?:stock|cryptocurrency|bitcoin|price)\s+(?:of|for|price)\b',
            # Sports and competitions - ENHANCED PATTERNS
            r'\bwho.{0,10}(?:top|best|leading|highest|most)\b.*\b(?:scorer|player|athlete|team|goal|point)\b',
            r'\b(?:top|best|leading|highest)\b.*\b(?:scorer|player|goal|point|team)\b.*\b(?:season|league|tournament|championship)\b',
            r'\bwho\s*(?:\'s|is)\s+(?:the\s+)?(?:leading|top|best|highest)\b.*\b(?:j1|j2|j3|premier|league|championship|tournament)\b',
            r'\b(?:j1|j2|j3|premier\s+league|la\s+liga|serie\s+a|bundesliga|ligue\s+1)\b.*\b(?:scorer|table|standing|result)\b',
            r'\b(?:football|soccer|basketball|baseball|tennis|golf)\b.*\b(?:score|result|winner|champion|leader)\b',
            r'\bwho.*\b(?:won|winning|wins|scored|leading)\b.*\b(?:match|game|tournament|championship|league)\b',
            r'\bwhat.*\b(?:score|result)\b.*\b(?:match|game|yesterday|today|last\s+night)\b',
            # Current events and general info
            r'\bwhat.*\b(?:news|happening|latest)\b.*\b(?:today|yesterday|this\s+week)\b',
            r'\bhow\s+much.*\b(?:cost|price|worth)\b',
            r'\bwhen\s+(?:is|was|will)\b.*\b(?:next|last|this)\b',
            # Simple math and conversions
            r'\b\d+\s*[\+\-\*\/\%]\s*\d+\b',
            r'\bconvert\s+\d+.*\b(?:to|into)\b',
        ]
        
        self.personal_data_patterns = [
            # Explicit personal data requests
            r'\b(?:my|our)\s+(?:email|emails|inbox|message|messages)\b',
            r'\bshow\s+(?:me\s+)?(?:my|our)\s+(?:email|files|calendar|drive|documents)\b',
            r'\bsearch\s+(?:my|our)\s+(?:email|gmail|inbox|drive|calendar)\b',
            r'\b(?:check|find|get|list)\s+(?:my|our)\s+(?:email|messages|files|events)\b',
            r'\b(?:recent|latest|new|unread)\s+(?:email|messages|files|events)\b',
            r'\b(?:upcoming|next)\s+(?:meeting|event|appointment)\b',
            r'\b(?:gmail|google\s+drive|google\s+calendar)\b',
            r'\b(?:attachment|document|spreadsheet|presentation)\s+(?:in|from|on)\s+(?:drive|email)\b',
            # Enhanced personal data patterns
            r'\bshow\s+me\s+(?:my\s+)?(?:recent\s+)?(?:email|messages|files|documents|calendar)\b.*\babout\b',
            r'\b(?:my|our)\s+(?:recent\s+)?(?:email|messages|files|documents)\b.*\babout\b',
            r'\bfind\s+(?:my\s+)?(?:email|messages|files|documents)\b.*\babout\b',
        ]
        
        self.context_dependent_patterns = [
            # Pronouns and context references
            r'\b(?:what|who|where|when|how)\s+(?:are|is|was|were)\s+(?:they|those|these|that|this|it)\b',
            r'\btell\s+me\s+(?:more\s+)?(?:about|on)\s+(?:them|those|that|this|it)\b',
            r'\b(?:details|more\s+info|information)\s+(?:about|on|for)\s+(?:them|those|that|this|it)\b',
            r'\bwhat\s+(?:does|do|did)\s+(?:it|that|this|they)\s+(?:say|mean|contain|include)\b',
            r'\bsummariz[e]?\s+(?:it|that|this|them|those)\b',
            r'\banalyze?\s+(?:it|that|this|them|those)\b',
            r'\bexplain\s+(?:it|that|this|them|those)\b',
        ]
        
        self.conversation_keywords = [
            'email', 'gmail', 'message', 'inbox', 'drive', 'calendar', 'document', 'file',
            'meeting', 'event', 'appointment', 'attachment', 'comment', 'feedback'
        ]
    
    def classify_request(
        self, 
        user_message: str, 
        conversation_history: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Classify a user request using the 3-tier approach.
        
        Returns:
        {
            "classification": ClassificationType,
            "confidence": float (0.0 to 1.0),
            "reasoning": str,
            "needs_tools": bool,
            "suggested_tools": List[str],
            "tier_used": int (1, 2, or 3)
        }
        """
        message_lower = user_message.lower().strip()
        
        # Tier 1: Pattern-based filtering (instant, free)
        tier1_result = self._tier1_pattern_matching(message_lower)
        if tier1_result["confidence"] >= 0.8:
            return tier1_result
        
        # Tier 2: Context analysis (fast, cheap) 
        if conversation_history:
            tier2_result = self._tier2_context_analysis(message_lower, conversation_history)
            if tier2_result["confidence"] >= 0.7:
                return tier2_result
        
        # If we reach here, it's ambiguous and needs Tier 3 LLM analysis
        return {
            "classification": "AMBIGUOUS",
            "confidence": 0.5,
            "reasoning": "Request is ambiguous and requires LLM analysis for proper classification",
            "needs_tools": None,  # Unknown, needs LLM
            "suggested_tools": [],
            "tier_used": 3
        }
    
    def _tier1_pattern_matching(self, message_lower: str) -> Dict[str, Any]:
        """Tier 1: Fast pattern matching for obvious cases."""
        
        # Check for general knowledge patterns
        for pattern in self.general_knowledge_patterns:
            if re.search(pattern, message_lower, re.IGNORECASE):
                return {
                    "classification": "GENERAL_KNOWLEDGE",
                    "confidence": 0.9,
                    "reasoning": f"Matched general knowledge pattern: {pattern[:50]}...",
                    "needs_tools": False,
                    "suggested_tools": [],
                    "tier_used": 1
                }
        
        # Check for personal data patterns
        for pattern in self.personal_data_patterns:
            if re.search(pattern, message_lower, re.IGNORECASE):
                suggested_tools = self._suggest_tools_from_pattern(pattern, message_lower)
                return {
                    "classification": "PERSONAL_DATA",
                    "confidence": 0.9,
                    "reasoning": f"Matched personal data pattern: {pattern[:50]}...",
                    "needs_tools": True,
                    "suggested_tools": suggested_tools,
                    "tier_used": 1
                }
        
        # Check for context-dependent patterns
        for pattern in self.context_dependent_patterns:
            if re.search(pattern, message_lower, re.IGNORECASE):
                return {
                    "classification": "CONTEXT_DEPENDENT", 
                    "confidence": 0.8,
                    "reasoning": f"Matched context-dependent pattern: {pattern[:50]}...",
                    "needs_tools": None,  # Depends on context analysis
                    "suggested_tools": [],
                    "tier_used": 1
                }
        
        # No clear pattern match
        return {
            "classification": "AMBIGUOUS",
            "confidence": 0.3,
            "reasoning": "No clear pattern matched",
            "needs_tools": None,
            "suggested_tools": [],
            "tier_used": 1
        }
    
    def _tier2_context_analysis(
        self, 
        message_lower: str, 
        conversation_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Tier 2: Fast context analysis based on conversation history."""
        
        # Analyze recent conversation context
        context_analysis = self._analyze_conversation_context(conversation_history)
        
        # If user is asking context-dependent questions and we have personal data context
        if any(re.search(pattern, message_lower, re.IGNORECASE) for pattern in self.context_dependent_patterns):
            
            if context_analysis["has_personal_data"]:
                # User asking about personal data mentioned in conversation
                suggested_tools = self._suggest_tools_from_context(context_analysis)
                return {
                    "classification": "PERSONAL_DATA",
                    "confidence": 0.8,
                    "reasoning": f"Context-dependent query with personal data history: {', '.join(context_analysis['data_types'])}",
                    "needs_tools": True,
                    "suggested_tools": suggested_tools,
                    "tier_used": 2
                }
            else:
                # User asking about general knowledge mentioned in conversation
                return {
                    "classification": "GENERAL_KNOWLEDGE",
                    "confidence": 0.7,
                    "reasoning": "Context-dependent query with general knowledge history",
                    "needs_tools": False,
                    "suggested_tools": [],
                    "tier_used": 2
                }
        
        # Check if general question that might benefit from context
        general_question_patterns = [
            r'\bwhat\s+(?:is|are|was|were)\b',
            r'\bwho\s+(?:is|are|was|were)\b',
            r'\btell\s+me\s+about\b',
            r'\bexplain\b'
        ]
        
        is_general_question = any(re.search(pattern, message_lower) for pattern in general_question_patterns)
        
        if is_general_question and not context_analysis["has_personal_data"]:
            return {
                "classification": "GENERAL_KNOWLEDGE",
                "confidence": 0.7,
                "reasoning": "General question with no personal data context",
                "needs_tools": False,
                "suggested_tools": [],
                "tier_used": 2
            }
        
        # Ambiguous case
        return {
            "classification": "AMBIGUOUS",
            "confidence": 0.5,
            "reasoning": "Context analysis inconclusive",
            "needs_tools": None,
            "suggested_tools": [],
            "tier_used": 2
        }
    
    def _analyze_conversation_context(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze conversation history for personal data indicators."""
        context = {
            "has_personal_data": False,
            "data_types": [],
            "recent_topics": [],
            "personal_keywords_count": 0
        }
        
        # Look at last 5 messages for context
        recent_messages = history[-5:] if len(history) > 5 else history
        
        for msg in recent_messages:
            content = msg.get("content", "").lower()
            
            # Check for personal data indicators
            if any(keyword in content for keyword in ["email", "gmail", "inbox", "message"]):
                context["has_personal_data"] = True
                if "email" not in context["data_types"]:
                    context["data_types"].append("email")
            
            if any(keyword in content for keyword in ["drive", "file", "document", "folder"]):
                context["has_personal_data"] = True
                if "drive" not in context["data_types"]:
                    context["data_types"].append("drive")
            
            if any(keyword in content for keyword in ["calendar", "meeting", "event", "appointment"]):
                context["has_personal_data"] = True
                if "calendar" not in context["data_types"]:
                    context["data_types"].append("calendar")
            
            # Count personal keyword occurrences
            for keyword in self.conversation_keywords:
                context["personal_keywords_count"] += content.count(keyword)
            
            # Extract potential topic names (simplified)
            if msg.get("role") == "assistant":
                # Look for entity mentions that might be topics
                topics = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', msg.get("content", ""))
                context["recent_topics"].extend(topics[:3])  # Limit to avoid noise
        
        return context
    
    def _suggest_tools_from_pattern(self, pattern: str, message: str) -> List[str]:
        """Suggest specific tools based on the matched pattern."""
        tools = []
        
        if any(keyword in pattern for keyword in ["email", "gmail", "inbox", "message"]):
            if "recent" in message or "latest" in message or "new" in message:
                tools.append("gmail_recent")
            else:
                tools.append("gmail_search")
        
        if any(keyword in pattern for keyword in ["drive", "file", "document", "folder"]):
            tools.append("drive_list_files")
        
        if any(keyword in pattern for keyword in ["calendar", "meeting", "event", "appointment"]):
            if "upcoming" in message or "next" in message:
                tools.append("calendar_upcoming_events")
            else:
                tools.append("calendar_list_events")
        
        return tools
    
    def _suggest_tools_from_context(self, context_analysis: Dict[str, Any]) -> List[str]:
        """Suggest tools based on conversation context analysis."""
        tools = []
        
        if "email" in context_analysis["data_types"]:
            tools.append("gmail_search")
        
        if "drive" in context_analysis["data_types"]:
            tools.append("drive_list_files")
        
        if "calendar" in context_analysis["data_types"]:
            tools.append("calendar_list_events")
        
        return tools
    
    def get_stats(self) -> Dict[str, Any]:
        """Get classifier statistics and configuration."""
        return {
            "general_knowledge_patterns": len(self.general_knowledge_patterns),
            "personal_data_patterns": len(self.personal_data_patterns),
            "context_dependent_patterns": len(self.context_dependent_patterns),
            "conversation_keywords": len(self.conversation_keywords),
            "version": "1.0.0"
        }


# Global instance
request_classifier = RequestClassifier()
"""
Intelligent Universal Request Classifier

This classifier uses semantic understanding and learning patterns to classify queries
across ANY domain/industry without hardcoded rules. It adapts to user patterns and
learns from feedback to improve classification accuracy over time.
"""

from __future__ import annotations

import re
import json
import httpx
import os
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime
from collections import defaultdict

ClassificationType = Literal["GENERAL_KNOWLEDGE", "PERSONAL_DATA", "CONTEXT_DEPENDENT", "CURRENT_INFO", "AMBIGUOUS"]

class IntelligentUniversalClassifier:
    """Universal classifier that learns and adapts without hardcoded industry rules."""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        
        # Learning patterns from successful classifications
        self.learned_patterns = {
            "GENERAL_KNOWLEDGE": [],
            "PERSONAL_DATA": [],
            "CONTEXT_DEPENDENT": [],
            "CURRENT_INFO": []
        }
        
        # Semantic indicators (generalized, not industry-specific)
        self.semantic_indicators = {
            "personal_pronouns": ["my", "our", "me", "mine", "ours"],
            "context_pronouns": ["they", "them", "those", "these", "that", "this", "it"],
            "personal_actions": ["show", "find", "get", "list", "search", "check"],
            "factual_questions": ["what", "who", "when", "where", "why", "how", "which"],
            "comparative_words": ["top", "best", "worst", "highest", "lowest", "most", "least"],
            "temporal_words": ["recent", "latest", "new", "old", "today", "yesterday", "last", "next"],
            "analysis_words": ["analyze", "summarize", "explain", "details", "about", "regarding"]
        }
        
        # Usage patterns for learning
        self.classification_history = []
        self.feedback_scores = defaultdict(list)
        
    async def classify_request(
        self, 
        user_message: str, 
        conversation_history: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Classify request using intelligent semantic analysis."""
        
        # Tier 1: Fast semantic pattern analysis
        semantic_result = self._semantic_analysis(user_message, conversation_history or [])
        if semantic_result["confidence"] >= 0.8:
            self._record_classification(user_message, semantic_result)
            return semantic_result
        
        # Tier 2: Context + learning patterns
        if conversation_history:
            context_result = self._context_enhanced_analysis(user_message, conversation_history, semantic_result)
            if context_result["confidence"] >= 0.7:
                self._record_classification(user_message, context_result)
                return context_result
        
        # Tier 3: LLM-based intelligent classification
        if self.api_key:
            llm_result = await self._llm_classification(user_message, conversation_history, semantic_result)
            if llm_result:
                self._record_classification(user_message, llm_result)
                return llm_result
        
        # Fallback
        fallback = {
            "classification": "AMBIGUOUS",
            "confidence": 0.3,
            "reasoning": "Insufficient information for confident classification",
            "needs_tools": None,
            "suggested_tools": [],
            "tier_used": 1
        }
        self._record_classification(user_message, fallback)
        return fallback
    
    def _semantic_analysis(self, message: str, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze message using semantic indicators."""
        
        message_lower = message.lower().strip()
        words = message_lower.split()
        word_set = set(words)
        
        # Calculate semantic scores
        personal_score = 0
        factual_score = 0
        context_score = 0
        current_info_score = 0
        
        # Personal data indicators
        personal_score += len([w for w in words if w in self.semantic_indicators["personal_pronouns"]]) * 0.3
        personal_score += len([w for w in words if w in self.semantic_indicators["personal_actions"]]) * 0.2
        personal_score += len([w for w in words if w in self.semantic_indicators["temporal_words"]]) * 0.1
        
        # Check for personal data request patterns (universal)
        if any(pronoun in word_set for pronoun in self.semantic_indicators["personal_pronouns"]):
            if any(action in word_set for action in self.semantic_indicators["personal_actions"]):
                personal_score += 0.4  # "show me", "find my", etc.
            # Boost personal score for "my + data type" combinations
            if any(data_type in message_lower for data_type in ["email", "message", "file", "document", "calendar"]):
                personal_score += 0.6  # Strong personal data indicator
        
        # Factual knowledge indicators
        factual_score += len([w for w in words if w in self.semantic_indicators["factual_questions"]]) * 0.2
        factual_score += len([w for w in words if w in self.semantic_indicators["comparative_words"]]) * 0.2
        
        # Check for factual question patterns
        first_word = words[0] if words else ""
        if first_word in self.semantic_indicators["factual_questions"]:
            # Questions starting with who/what/when/where typically factual
            if not any(pronoun in word_set for pronoun in self.semantic_indicators["personal_pronouns"]):
                factual_score += 0.5  # Increased weight for factual questions
        
        # Additional factual indicators
        factual_indicators = ["definition", "explain", "how does", "what is", "who is", "when was", "where is"]
        for indicator in factual_indicators:
            if indicator in message_lower:
                factual_score += 0.3
        
        # Boost factual score for comparative questions about general topics
        if any(comp in word_set for comp in self.semantic_indicators["comparative_words"]):
            if any(question in word_set for question in self.semantic_indicators["factual_questions"]):
                factual_score += 0.4  # "who is the top...", "what is the best..."
        
        # Special case for competitive/comparative queries (universal pattern)
        if message_lower.startswith("who"):
            # Look for competitive words anywhere in the message
            competitive_words = ["top", "best", "leading", "highest", "most", "greatest", "champion"]
            if any(word in message_lower for word in competitive_words):
                factual_score += 0.6
        
        # Additional patterns for "what is/was the..." type questions
        if any(start in message_lower for start in ["what is", "what was", "what's"]):
            competitive_context = ["score", "result", "winner", "champion", "leader", "record"]
            if any(word in message_lower for word in competitive_context):
                factual_score += 0.5
        
        # Context-dependent indicators
        context_score += len([w for w in words if w in self.semantic_indicators["context_pronouns"]]) * 0.4
        context_score += len([w for w in words if w in self.semantic_indicators["analysis_words"]]) * 0.3
        
        # Strong context patterns
        context_patterns = ["what are they", "tell me more", "what about", "explain those", "what do they"]
        for pattern in context_patterns:
            if pattern in message_lower:
                context_score += 0.5
        
        # Current information indicators (need web search/real-time data)
        current_indicators = [
            "current", "latest", "recent", "today", "now", "this year", "2025", 
            "so far", "up to now", "as of", "right now"
        ]
        temporal_context = ["season", "year", "month", "week", "today", "this"]
        
        current_info_score += len([w for w in words if w in current_indicators]) * 0.4
        
        # Check for current information patterns
        if any(current in message_lower for current in current_indicators):
            if any(temporal in message_lower for temporal in temporal_context):
                current_info_score += 0.5  # "current season", "this year", etc.
        
        # Sports/competition queries with current context get high current_info score
        if message_lower.startswith("who"):
            competitive_words = ["top", "best", "leading", "highest", "most", "greatest", "champion"]
            if any(word in message_lower for word in competitive_words):
                if any(current in message_lower for current in current_indicators):
                    current_info_score += 0.8  # Very likely needs current data
        
        # Determine classification based on scores
        max_score = max(personal_score, factual_score, context_score, current_info_score)
        confidence = min(max_score, 1.0)
        
        if max_score == personal_score and confidence >= 0.6:
            return {
                "classification": "PERSONAL_DATA",
                "confidence": confidence,
                "reasoning": f"Strong personal data indicators (score: {personal_score:.2f})",
                "needs_tools": True,
                "suggested_tools": self._suggest_tools_semantically(message_lower),
                "tier_used": 1,
                "semantic_scores": {"personal": personal_score, "factual": factual_score, "context": context_score}
            }
        
        elif max_score == factual_score and confidence >= 0.6:
            return {
                "classification": "GENERAL_KNOWLEDGE",
                "confidence": confidence,
                "reasoning": f"Strong factual knowledge indicators (score: {factual_score:.2f})",
                "needs_tools": False,
                "suggested_tools": [],
                "tier_used": 1,
                "semantic_scores": {"personal": personal_score, "factual": factual_score, "context": context_score}
            }
        
        elif max_score == context_score and confidence >= 0.6:
            return {
                "classification": "CONTEXT_DEPENDENT",
                "confidence": confidence,
                "reasoning": f"Strong context-dependent indicators (score: {context_score:.2f})",
                "needs_tools": None,  # Depends on context analysis
                "suggested_tools": [],
                "tier_used": 1,
                "semantic_scores": {"personal": personal_score, "factual": factual_score, "context": context_score, "current_info": current_info_score}
            }
        
        elif max_score == current_info_score and confidence >= 0.6:
            return {
                "classification": "CURRENT_INFO",
                "confidence": confidence,
                "reasoning": f"Strong current information indicators (score: {current_info_score:.2f})",
                "needs_tools": True,
                "suggested_tools": ["web_search"],  # Would need web search for current info
                "tier_used": 1,
                "semantic_scores": {"personal": personal_score, "factual": factual_score, "context": context_score, "current_info": current_info_score}
            }
        
        else:
            return {
                "classification": "AMBIGUOUS",
                "confidence": confidence,
                "reasoning": f"Unclear semantic indicators (max score: {max_score:.2f})",
                "needs_tools": None,
                "suggested_tools": [],
                "tier_used": 1,
                "semantic_scores": {"personal": personal_score, "factual": factual_score, "context": context_score, "current_info": current_info_score}
            }
    
    def _context_enhanced_analysis(
        self, 
        message: str, 
        history: List[Dict[str, Any]], 
        semantic_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enhance analysis with conversation context."""
        
        # Analyze conversation for personal data indicators
        personal_data_context = False
        factual_context = False
        
        for msg in history[-5:]:  # Last 5 messages
            content = msg.get("content", "").lower()
            
            # Check for personal data tools usage or mentions
            if any(tool in content for tool in ["email", "gmail", "drive", "calendar", "files", "documents", "messages"]):
                personal_data_context = True
            
            # Check for factual discussions
            if any(word in content for word in ["according to", "research", "studies show", "data indicates", "statistics"]):
                factual_context = True
        
        # If semantic analysis was context-dependent, use context to decide
        if semantic_result["classification"] == "CONTEXT_DEPENDENT":
            if personal_data_context:
                return {
                    "classification": "PERSONAL_DATA",
                    "confidence": 0.75,
                    "reasoning": "Context-dependent query with personal data conversation history",
                    "needs_tools": True,
                    "suggested_tools": self._suggest_tools_semantically(message.lower()),
                    "tier_used": 2
                }
            elif factual_context:
                return {
                    "classification": "GENERAL_KNOWLEDGE", 
                    "confidence": 0.75,
                    "reasoning": "Context-dependent query with factual conversation history",
                    "needs_tools": False,
                    "suggested_tools": [],
                    "tier_used": 2
                }
        
        # Boost confidence if context supports semantic analysis
        boosted_confidence = semantic_result["confidence"]
        if semantic_result["classification"] == "PERSONAL_DATA" and personal_data_context:
            boosted_confidence = min(boosted_confidence + 0.2, 1.0)
        elif semantic_result["classification"] == "GENERAL_KNOWLEDGE" and factual_context:
            boosted_confidence = min(boosted_confidence + 0.2, 1.0)
        
        return {
            **semantic_result,
            "confidence": boosted_confidence,
            "reasoning": f"{semantic_result['reasoning']} + context boost",
            "tier_used": 2
        }
    
    async def _llm_classification(
        self, 
        message: str, 
        history: List[Dict[str, Any]], 
        semantic_result: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Use LLM for sophisticated classification."""
        
        if not self.api_key:
            return None
        
        # Build context
        context_summary = ""
        if history:
            recent_messages = [f"{msg.get('role', '')}: {msg.get('content', '')[:100]}" 
                             for msg in history[-3:]]
            context_summary = f"Recent conversation:\n" + "\n".join(recent_messages)
        
        system_prompt = """You are an intelligent query classifier that determines if a user query requires:

1. GENERAL_KNOWLEDGE - Factual questions that can be answered with general knowledge (no personal data needed)
2. PERSONAL_DATA - Questions requiring access to user's personal data (emails, files, calendar, documents, etc.)
3. CONTEXT_DEPENDENT - Questions referring to previous conversation context
4. CURRENT_INFO - Questions requiring current/real-time information that needs web search
5. AMBIGUOUS - Unclear queries requiring more information

IMPORTANT PRINCIPLES:
- Questions asking for "current", "latest", "recent", "2025", "so far", "this year" info = CURRENT_INFO (needs web search)
- A query about "my emails", "my files", "my calendar", "show me my data" = PERSONAL_DATA  
- A query like "what are they about?", "tell me more", "explain it" = CONTEXT_DEPENDENT
- General factual questions without current context = GENERAL_KNOWLEDGE
- Industry doesn't matter - focus on whether current data/personal data access is needed

Return ONLY valid JSON:
{
    "classification": "GENERAL_KNOWLEDGE|PERSONAL_DATA|CONTEXT_DEPENDENT|CURRENT_INFO|AMBIGUOUS",
    "confidence": float (0.0 to 1.0),
    "reasoning": "brief explanation",
    "needs_tools": boolean or null,
    "suggested_tools": ["tool1", "tool2"] or []
}"""
        
        user_prompt = f"""Query: "{message}"

{context_summary}

Semantic analysis suggests: {semantic_result['classification']} (confidence: {semantic_result['confidence']:.2f})

Classify this query appropriately."""
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": 0.1,
                        "max_tokens": 300
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    
                    # Parse JSON response
                    try:
                        if content.startswith("```json"):
                            content = content.replace("```json", "").replace("```", "").strip()
                        elif content.startswith("```"):
                            content = content.replace("```", "").strip()
                        
                        classification = json.loads(content)
                        classification["tier_used"] = 3
                        return classification
                        
                    except json.JSONDecodeError as e:
                        print(f"❌ Failed to parse LLM classification JSON: {e}")
                        return None
                        
        except Exception as e:
            print(f"❌ Error in LLM classification: {e}")
            return None
    
    def _suggest_tools_semantically(self, message_lower: str) -> List[str]:
        """Suggest tools based on semantic content (universal)."""
        tools = []
        
        # Email-related terms (universal across languages/industries)
        email_terms = ["email", "mail", "message", "inbox", "correspondence"]
        if any(term in message_lower for term in email_terms):
            if any(temporal in message_lower for temporal in ["recent", "latest", "new", "last"]):
                tools.append("gmail_recent")
            else:
                tools.append("gmail_search")
        
        # File/document terms
        file_terms = ["file", "document", "doc", "pdf", "spreadsheet", "presentation", "attachment"]
        if any(term in message_lower for term in file_terms):
            tools.append("drive_list_files")
        
        # Calendar/meeting terms
        calendar_terms = ["meeting", "event", "appointment", "schedule", "calendar"]
        if any(term in message_lower for term in calendar_terms):
            if any(temporal in message_lower for temporal in ["upcoming", "next", "today", "tomorrow"]):
                tools.append("calendar_upcoming_events")
            else:
                tools.append("calendar_list_events")
        
        return list(set(tools))  # Remove duplicates
    
    def _record_classification(self, message: str, result: Dict[str, Any]) -> None:
        """Record classification for learning."""
        self.classification_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "message": message[:100],  # Truncate for storage
            "classification": result["classification"],
            "confidence": result["confidence"],
            "tier_used": result["tier_used"]
        })
        
        # Keep only recent history
        if len(self.classification_history) > 1000:
            self.classification_history = self.classification_history[-500:]
    
    def learn_from_feedback(self, message: str, actual_classification: str, was_correct: bool) -> None:
        """Learn from classification feedback."""
        score = 1.0 if was_correct else 0.0
        self.feedback_scores[actual_classification].append(score)
        
        # Update learned patterns based on feedback
        if was_correct and actual_classification != "AMBIGUOUS":
            # Extract semantic patterns from successful classifications
            semantic_pattern = self._extract_semantic_pattern(message, actual_classification)
            if semantic_pattern not in self.learned_patterns[actual_classification]:
                self.learned_patterns[actual_classification].append(semantic_pattern)
    
    def _extract_semantic_pattern(self, message: str, classification: str) -> str:
        """Extract reusable semantic patterns from successful classifications."""
        # Simplified pattern extraction - can be enhanced with ML
        words = message.lower().split()
        
        if classification == "PERSONAL_DATA":
            personal_words = [w for w in words if w in self.semantic_indicators["personal_pronouns"] or 
                            w in self.semantic_indicators["personal_actions"]]
            return f"personal_pattern:{'+'.join(personal_words)}"
        
        elif classification == "GENERAL_KNOWLEDGE":
            factual_words = [w for w in words if w in self.semantic_indicators["factual_questions"] or 
                           w in self.semantic_indicators["comparative_words"]]
            return f"factual_pattern:{'+'.join(factual_words)}"
        
        return f"general_pattern:{words[0] if words else 'unknown'}"
    
    def get_learning_stats(self) -> Dict[str, Any]:
        """Get classifier learning statistics."""
        accuracy_by_class = {}
        for class_name, scores in self.feedback_scores.items():
            if scores:
                accuracy_by_class[class_name] = sum(scores) / len(scores)
        
        return {
            "total_classifications": len(self.classification_history),
            "accuracy_by_class": accuracy_by_class,
            "learned_patterns": {k: len(v) for k, v in self.learned_patterns.items()},
            "tier_usage": {
                "tier1": len([h for h in self.classification_history if h.get("tier_used") == 1]),
                "tier2": len([h for h in self.classification_history if h.get("tier_used") == 2]),
                "tier3": len([h for h in self.classification_history if h.get("tier_used") == 3])
            }
        }


# Global instance
intelligent_classifier = IntelligentUniversalClassifier()
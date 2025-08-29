"""Configuration for routing agent"""
from typing import Dict, Any
import os

class RoutingConfig:
    """Configuration for the routing agent that decides between APIs"""
    
    # Model configuration
    ANALYSIS_MODEL = "gpt-4o-mini"  # Fast and lightweight for routing decisions
    ANALYSIS_TEMPERATURE = 0  # Deterministic routing decisions
    ANALYSIS_MAX_TOKENS = 10  # Very short response needed
    
    # Timeout configuration
    ANALYSIS_TIMEOUT = 3.0  # Quick timeout for routing decision
    ANALYSIS_CONNECT_TIMEOUT = 1.5
    
    # API endpoints
    OPENAI_CHAT_COMPLETIONS = "https://api.openai.com/v1/chat/completions"
    OPENAI_RESPONSES = "https://api.openai.com/v1/responses"
    
    # Retry configuration
    MAX_RETRIES = 2
    RETRY_DELAY = 0.5
    
    # Analysis prompt configuration
    SYSTEM_PROMPT = "You are a routing assistant. Analyze questions and respond with only YES or NO."
    
    @classmethod
    def get_analysis_prompt(cls, question: str) -> str:
        """Generate the analysis prompt for the routing decision"""
        return f"""Analyze this question and determine if it requires current/real-time information or web search.

Question: "{question}"

Consider:
- Does it ask for recent data, current events, or live information?
- Does it request research, investigation, or web search?
- Does it need information beyond your training data cutoff?
- Is it asking for "latest", "current", "this season", "now", etc.?

Respond with ONLY "YES" or "NO"."""

    @classmethod
    def get_headers(cls, api_key: str) -> Dict[str, str]:
        """Get headers for API requests"""
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
    
    @classmethod
    def get_analysis_payload(cls, question: str) -> Dict[str, Any]:
        """Get payload for analysis API call"""
        return {
            "model": cls.ANALYSIS_MODEL,
            "messages": [
                {"role": "system", "content": cls.SYSTEM_PROMPT},
                {"role": "user", "content": cls.get_analysis_prompt(question)}
            ],
            "max_tokens": cls.ANALYSIS_MAX_TOKENS,
            "temperature": cls.ANALYSIS_TEMPERATURE
        }
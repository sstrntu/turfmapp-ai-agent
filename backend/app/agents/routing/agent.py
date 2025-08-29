"""Routing agent that decides between Chat Completions and Responses API"""
import asyncio
from typing import Optional, Dict, Any
import httpx
from .config import RoutingConfig
from .cache import routing_cache


class RoutingAgent:
    """Agent responsible for routing decisions between different OpenAI APIs"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.config = RoutingConfig()
        
    async def analyze_needs_current_info(self, question: str) -> bool:
        """
        Use LLM to analyze if question needs current/real-time information
        
        Args:
            question: The user's question to analyze
            
        Returns:
            True if needs current info (use Responses API with tools)
            False if can use cached knowledge (use Chat Completions API)
        """
        try:
            # Check cache first
            cached_decision = await routing_cache.get(question)
            if cached_decision is not None:
                return cached_decision
            
            headers = self.config.get_headers(self.api_key)
            payload = self.config.get_analysis_payload(question)
            
            print(f"🤖 Routing Agent: Analyzing question...")
            
            # Make analysis request with retry logic
            for attempt in range(self.config.MAX_RETRIES):
                try:
                    async with httpx.AsyncClient(
                        timeout=httpx.Timeout(
                            self.config.ANALYSIS_TIMEOUT, 
                            connect=self.config.ANALYSIS_CONNECT_TIMEOUT
                        )
                    ) as client:
                        resp = await client.post(
                            self.config.OPENAI_CHAT_COMPLETIONS,
                            json=payload,
                            headers=headers
                        )
                        
                        if resp.status_code == 200:
                            data = resp.json()
                            result = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip().upper()
                            
                            # Validate response
                            if result in ["YES", "NO"]:
                                decision = result == "YES"
                                
                                # Cache the decision
                                await routing_cache.set(question, decision)
                                
                                print(f"🔍 Routing Decision: {result} -> {'Responses API (with tools)' if decision else 'Chat Completions API (fast)'}")
                                return decision
                            else:
                                print(f"⚠️  Invalid LLM response: '{result}', defaulting to Chat Completions")
                                decision = False
                                await routing_cache.set(question, decision)
                                return decision
                                
                        else:
                            print(f"❌ Analysis request failed: {resp.status_code}")
                            if attempt < self.config.MAX_RETRIES - 1:
                                await asyncio.sleep(self.config.RETRY_DELAY)
                                continue
                            
                except (httpx.TimeoutException, httpx.ReadTimeout) as e:
                    print(f"⏱️  Analysis timeout on attempt {attempt + 1}: {e}")
                    if attempt < self.config.MAX_RETRIES - 1:
                        await asyncio.sleep(self.config.RETRY_DELAY)
                        continue
                        
                except Exception as e:
                    print(f"❌ Analysis error on attempt {attempt + 1}: {e}")
                    if attempt < self.config.MAX_RETRIES - 1:
                        await asyncio.sleep(self.config.RETRY_DELAY)
                        continue
                        
            # Fallback to Chat Completions if all attempts failed
            print("🔄 All analysis attempts failed, defaulting to Chat Completions API")
            decision = False
            await routing_cache.set(question, decision)
            return decision
            
        except Exception as e:
            print(f"❌ Critical routing error: {e}")
            return False
    
    def should_use_responses_api(
        self, 
        question: Optional[str] = None,
        has_tools: bool = False,
        has_developer_instructions: bool = False,
        has_assistant_context: bool = False,
        model_name: str = ""
    ) -> Dict[str, Any]:
        """
        Determine if should use Responses API based on various factors
        
        Args:
            question: User question to analyze
            has_tools: Whether tools are provided
            has_developer_instructions: Whether developer instructions are provided  
            has_assistant_context: Whether assistant context is provided
            model_name: The model being used
            
        Returns:
            Dict with 'use_responses_api' bool and 'reason' string
        """
        reasons = []
        
        # Force Responses API for certain conditions
        if model_name.lower().startswith("gpt-5"):
            reasons.append("gpt-5 model (including gpt-5-nano) requires Responses API")
            return {"use_responses_api": True, "reason": "; ".join(reasons)}
            
        if has_tools:
            reasons.append("tools provided")
            
        if has_developer_instructions:
            reasons.append("developer instructions provided")
            
        if has_assistant_context:
            reasons.append("assistant context provided")
            
        if reasons:
            return {"use_responses_api": True, "reason": "; ".join(reasons)}
            
        # If no forced conditions, return for LLM analysis
        return {"use_responses_api": None, "reason": "needs LLM analysis"}
    
    async def route_request(
        self,
        question: str,
        has_tools: bool = False,
        has_developer_instructions: bool = False,
        has_assistant_context: bool = False,
        model_name: str = ""
    ) -> Dict[str, Any]:
        """
        Main routing method that determines which API to use
        
        Returns:
            Dict with 'use_responses_api' bool, 'reason' string, and 'confidence' float
        """
        # Check forced conditions first
        decision = self.should_use_responses_api(
            question, has_tools, has_developer_instructions, has_assistant_context, model_name
        )
        
        if decision["use_responses_api"] is not None:
            return {
                **decision,
                "confidence": 1.0,
                "method": "rule-based"
            }
        
        # Use LLM analysis for content-based routing
        needs_current_info = await self.analyze_needs_current_info(question)
        
        return {
            "use_responses_api": needs_current_info,
            "reason": "question needs current information" if needs_current_info else "question can use cached knowledge",
            "confidence": 0.8,  # LLM confidence
            "method": "llm-analysis"
        }
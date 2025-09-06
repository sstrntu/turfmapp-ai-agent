"""
Response Evaluator - Iterative Quality Assessment and Improvement

This service evaluates the quality of AI responses and determines if tool results
actually answered the user's question effectively. It provides feedback for
continuous improvement of tool usage decisions.
"""

from __future__ import annotations

import json
import httpx
import os
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime

EvaluationResult = Literal["EXCELLENT", "GOOD", "ADEQUATE", "POOR", "FAILED"]

class ResponseEvaluator:
    """Evaluates response quality and provides feedback for tool usage optimization."""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.evaluation_cache: Dict[str, Dict[str, Any]] = {}
        
    async def evaluate_response_quality(
        self,
        user_question: str,
        ai_response: str,
        tools_used: List[str] = None,
        tool_results: List[Dict[str, Any]] = None,
        approach: str = None
    ) -> Dict[str, Any]:
        """
        Evaluate the quality of an AI response.
        
        Returns:
        {
            "quality_score": float (0.0 to 1.0),
            "evaluation": EvaluationResult,
            "reasoning": str,
            "addressed_question": bool,
            "tool_effectiveness": Dict[str, float],
            "improvement_suggestions": List[str],
            "confidence": float
        }
        """
        
        # Create evaluation key for caching
        eval_key = f"{hash(user_question + ai_response)}"
        if eval_key in self.evaluation_cache:
            return self.evaluation_cache[eval_key]
        
        print(f"🔍 Evaluating response quality for: '{user_question[:50]}...'")
        
        # Quick heuristic evaluation first
        heuristic_eval = self._heuristic_evaluation(user_question, ai_response, tools_used)
        
        # If heuristic confidence is high, use it
        if heuristic_eval["confidence"] >= 0.8:
            result = heuristic_eval
        else:
            # Use LLM for thorough evaluation
            llm_eval = await self._llm_evaluation(user_question, ai_response, tools_used, tool_results, approach)
            result = llm_eval if llm_eval else heuristic_eval
        
        # Cache result
        self.evaluation_cache[eval_key] = result
        
        print(f"📊 Evaluation: {result['evaluation']} (score: {result['quality_score']:.2f})")
        
        return result
    
    def _heuristic_evaluation(
        self,
        user_question: str,
        ai_response: str,
        tools_used: List[str] = None
    ) -> Dict[str, Any]:
        """Quick heuristic-based evaluation."""
        
        score = 0.5  # Base score
        reasoning_parts = []
        suggestions = []
        
        # Length and completeness check
        response_length = len(ai_response.strip())
        question_length = len(user_question.strip())
        
        if response_length < 20:
            score -= 0.3
            reasoning_parts.append("Response too short")
            suggestions.append("Provide more detailed explanation")
        elif response_length > question_length * 2:
            score += 0.1
            reasoning_parts.append("Response has adequate length")
        
        # Error indicators
        error_indicators = [
            "error", "failed", "couldn't", "unable", "sorry", 
            "don't have", "can't", "unavailable", "not found"
        ]
        
        response_lower = ai_response.lower()
        error_count = sum(1 for indicator in error_indicators if indicator in response_lower)
        
        if error_count > 2:
            score -= 0.4
            reasoning_parts.append("Multiple error indicators found")
            suggestions.append("Reduce error messages and provide alternatives")
        elif error_count == 0:
            score += 0.1
            reasoning_parts.append("No obvious error indicators")
        
        # Positive indicators
        positive_indicators = [
            "based on", "found", "here's", "according to", 
            "shows", "indicates", "summary", "analysis"
        ]
        
        positive_count = sum(1 for indicator in positive_indicators if indicator in response_lower)
        if positive_count >= 2:
            score += 0.2
            reasoning_parts.append("Contains positive information indicators")
        
        # Tool usage evaluation
        tool_effectiveness = {}
        if tools_used:
            for tool in tools_used:
                # Simple heuristic: if tool is mentioned in response, likely effective
                if tool.replace("_", " ") in response_lower or tool in response_lower:
                    tool_effectiveness[tool] = 0.7
                    score += 0.1
                else:
                    tool_effectiveness[tool] = 0.3
                    score -= 0.05
        
        # Question addressing check (simple keyword overlap)
        question_words = set(user_question.lower().split())
        response_words = set(ai_response.lower().split())
        overlap_ratio = len(question_words.intersection(response_words)) / max(len(question_words), 1)
        
        addressed_question = overlap_ratio > 0.2 or any(
            word in response_lower for word in ["yes", "no", "answer", "result", "information"]
        )
        
        if addressed_question:
            score += 0.1
            reasoning_parts.append("Appears to address the question")
        else:
            score -= 0.2
            reasoning_parts.append("May not fully address the question")
            suggestions.append("Ensure response directly answers the user's question")
        
        # Normalize score
        score = max(0.0, min(1.0, score))
        
        # Convert to evaluation categories
        if score >= 0.8:
            evaluation = "EXCELLENT"
        elif score >= 0.6:
            evaluation = "GOOD"
        elif score >= 0.4:
            evaluation = "ADEQUATE"
        elif score >= 0.2:
            evaluation = "POOR"
        else:
            evaluation = "FAILED"
        
        return {
            "quality_score": score,
            "evaluation": evaluation,
            "reasoning": "; ".join(reasoning_parts) if reasoning_parts else "Basic heuristic evaluation",
            "addressed_question": addressed_question,
            "tool_effectiveness": tool_effectiveness,
            "improvement_suggestions": suggestions,
            "confidence": 0.6 if len(reasoning_parts) >= 3 else 0.4,
            "method": "heuristic"
        }
    
    async def _llm_evaluation(
        self,
        user_question: str,
        ai_response: str,
        tools_used: List[str] = None,
        tool_results: List[Dict[str, Any]] = None,
        approach: str = None
    ) -> Optional[Dict[str, Any]]:
        """Comprehensive LLM-based evaluation."""
        
        if not self.api_key:
            print("❌ No OpenAI API key for LLM evaluation")
            return None
        
        # Prepare tool information
        tool_info = ""
        if tools_used:
            tool_info = f"\nTools used: {', '.join(tools_used)}"
            if tool_results:
                tool_info += f"\nTool results available: {len(tool_results)} results"
        
        approach_info = f"\nApproach used: {approach}" if approach else ""
        
        system_prompt = """You are an expert AI response evaluator. Analyze the quality of AI responses to user questions.

Evaluate based on:
1. RELEVANCE: Does the response directly answer the user's question?
2. ACCURACY: Is the information provided accurate and reliable?
3. COMPLETENESS: Does it provide sufficient detail to be helpful?
4. CLARITY: Is it easy to understand and well-structured?
5. TOOL EFFECTIVENESS: If tools were used, did they provide useful information?

Return your evaluation as JSON:
{
    "quality_score": float (0.0 to 1.0),
    "evaluation": "EXCELLENT|GOOD|ADEQUATE|POOR|FAILED",
    "reasoning": "detailed explanation of evaluation",
    "addressed_question": boolean,
    "tool_effectiveness": {
        "tool_name": effectiveness_score (0.0 to 1.0)
    },
    "improvement_suggestions": ["suggestion1", "suggestion2", ...],
    "confidence": float (0.0 to 1.0)
}

Scoring guide:
- EXCELLENT (0.8-1.0): Perfect answer, very helpful, clear and complete
- GOOD (0.6-0.8): Answers the question well with minor issues
- ADEQUATE (0.4-0.6): Partially answers, some useful information
- POOR (0.2-0.4): Barely addresses question, limited usefulness
- FAILED (0.0-0.2): Doesn't answer question or provides incorrect info"""
        
        user_prompt = f"""USER QUESTION: {user_question}

AI RESPONSE: {ai_response}
{tool_info}
{approach_info}

Evaluate the quality of this AI response."""
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
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
                        "max_tokens": 800
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    
                    # Parse JSON response
                    try:
                        # Clean up markdown formatting
                        if content.startswith("```json"):
                            content = content.replace("```json", "").replace("```", "").strip()
                        elif content.startswith("```"):
                            content = content.replace("```", "").strip()
                        
                        evaluation = json.loads(content)
                        evaluation["method"] = "llm"
                        return evaluation
                        
                    except json.JSONDecodeError as e:
                        print(f"❌ Failed to parse LLM evaluation JSON: {e}")
                        return None
                        
                else:
                    print(f"❌ LLM evaluation API error: {response.status_code}")
                    return None
                    
        except Exception as e:
            print(f"❌ Error in LLM evaluation: {e}")
            return None
    
    async def suggest_better_approach(
        self,
        user_question: str,
        current_approach: str,
        current_tools: List[str],
        evaluation_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Suggest a better approach based on evaluation results."""
        
        suggestions = {
            "alternative_approach": None,
            "different_tools": [],
            "parameter_adjustments": {},
            "reasoning": ""
        }
        
        quality_score = evaluation_result.get("quality_score", 0.0)
        evaluation_grade = evaluation_result.get("evaluation", "FAILED")
        
        if quality_score < 0.4:  # Poor or Failed
            
            if current_approach == "general_knowledge":
                # Maybe it actually needed tools
                suggestions.update({
                    "alternative_approach": "tool_based",
                    "different_tools": ["gmail_search", "drive_list_files"],
                    "reasoning": "General knowledge approach failed, user might need personal data"
                })
                
            elif current_approach == "tool_based":
                # Maybe tools weren't the right ones or parameters were wrong
                if "gmail" in str(current_tools) and "no results" in evaluation_result.get("reasoning", "").lower():
                    suggestions.update({
                        "parameter_adjustments": {"expand_search": True, "max_results": 20},
                        "reasoning": "Gmail search might need broader parameters"
                    })
                else:
                    suggestions.update({
                        "alternative_approach": "context_analysis",
                        "reasoning": "Tools didn't provide useful results, try context analysis"
                    })
                    
            elif current_approach == "context_analysis":
                # Context analysis failed, maybe need tools after all
                suggestions.update({
                    "alternative_approach": "tool_based",
                    "different_tools": ["gmail_recent", "calendar_upcoming_events"],
                    "reasoning": "Context analysis insufficient, try fetching fresh data"
                })
        
        elif quality_score < 0.6:  # Adequate
            # Minor improvements needed
            tool_effectiveness = evaluation_result.get("tool_effectiveness", {})
            ineffective_tools = [tool for tool, score in tool_effectiveness.items() if score < 0.5]
            
            if ineffective_tools:
                suggestions.update({
                    "different_tools": [tool for tool in ["gmail_search", "drive_list_files", "calendar_list_events"] 
                                     if tool not in ineffective_tools],
                    "reasoning": f"Replace ineffective tools: {', '.join(ineffective_tools)}"
                })
        
        return suggestions
    
    def get_evaluation_stats(self) -> Dict[str, Any]:
        """Get statistics about evaluations performed."""
        if not self.evaluation_cache:
            return {"total_evaluations": 0}
        
        evaluations = list(self.evaluation_cache.values())
        total = len(evaluations)
        
        # Count by evaluation grade
        grade_counts = {}
        score_sum = 0
        
        for eval_result in evaluations:
            grade = eval_result.get("evaluation", "UNKNOWN")
            grade_counts[grade] = grade_counts.get(grade, 0) + 1
            score_sum += eval_result.get("quality_score", 0)
        
        avg_score = score_sum / total if total > 0 else 0
        
        # Tool effectiveness analysis
        all_tool_scores = {}
        for eval_result in evaluations:
            for tool, score in eval_result.get("tool_effectiveness", {}).items():
                if tool not in all_tool_scores:
                    all_tool_scores[tool] = []
                all_tool_scores[tool].append(score)
        
        tool_avg_scores = {
            tool: sum(scores) / len(scores) 
            for tool, scores in all_tool_scores.items()
        }
        
        return {
            "total_evaluations": total,
            "average_quality_score": round(avg_score, 3),
            "grade_distribution": grade_counts,
            "tool_effectiveness_averages": tool_avg_scores,
            "cache_size": len(self.evaluation_cache)
        }


# Global instance
response_evaluator = ResponseEvaluator()
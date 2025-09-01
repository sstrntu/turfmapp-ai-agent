"""
Agent management API endpoints.

This module provides API endpoints for managing and interacting with the
agent routing system that was previously unused.
"""

from __future__ import annotations

import os
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ...core.simple_auth import get_current_user_from_token
from ...agents.routing.agent import RoutingAgent
from ...agents.routing.config import RoutingConfig
from ...agents.routing.monitor import PerformanceMonitor

router = APIRouter()

# Initialize agent components
_routing_agent: RoutingAgent | None = None
_performance_monitor = PerformanceMonitor()


def get_routing_agent() -> RoutingAgent:
    """Get or create routing agent instance."""
    global _routing_agent
    
    if _routing_agent is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=500, 
                detail="OPENAI_API_KEY not configured for agent routing"
            )
        _routing_agent = RoutingAgent(api_key)
    
    return _routing_agent


class RoutingAnalysisRequest(BaseModel):
    """Request model for routing analysis."""
    question: str
    

class RoutingAnalysisResponse(BaseModel):
    """Response model for routing analysis."""
    question: str
    needs_current_info: bool
    recommended_api: str
    confidence: float
    analysis_time_ms: float


class AgentStatsResponse(BaseModel):
    """Response model for agent performance statistics."""
    total_requests: int
    cache_hit_rate: float
    average_analysis_time_ms: float
    api_distribution: Dict[str, int]


@router.post("/routing/analyze", response_model=RoutingAnalysisResponse)
async def analyze_routing_needs(
    request: RoutingAnalysisRequest,
    current_user: dict = Depends(get_current_user_from_token)
):
    """Analyze a question to determine optimal API routing."""
    try:
        routing_agent = get_routing_agent()
        
        # Record start time for performance monitoring
        import time
        start_time = time.time()
        
        # Analyze the question
        needs_current_info = await routing_agent.analyze_needs_current_info(request.question)
        
        # Calculate analysis time
        analysis_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Determine recommended API
        recommended_api = "responses_api" if needs_current_info else "chat_completions"
        
        # Calculate confidence (simplified - could be enhanced with more sophisticated logic)
        confidence = 0.85  # Default confidence level
        
        # Record performance metrics
        _performance_monitor.record_request(
            question=request.question,
            decision=needs_current_info,
            response_time=analysis_time
        )
        
        return RoutingAnalysisResponse(
            question=request.question,
            needs_current_info=needs_current_info,
            recommended_api=recommended_api,
            confidence=confidence,
            analysis_time_ms=round(analysis_time, 2)
        )
        
    except Exception as e:
        print(f"❌ Routing analysis error: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to analyze routing needs: {str(e)}"
        )


@router.get("/stats", response_model=AgentStatsResponse)
async def get_agent_statistics(
    current_user: dict = Depends(get_current_user_from_token)
):
    """Get performance statistics for the agent routing system."""
    try:
        stats = _performance_monitor.get_stats()
        
        return AgentStatsResponse(
            total_requests=stats.get("total_requests", 0),
            cache_hit_rate=stats.get("cache_hit_rate", 0.0),
            average_analysis_time_ms=stats.get("average_analysis_time_ms", 0.0),
            api_distribution=stats.get("api_distribution", {"responses_api": 0, "chat_completions": 0})
        )
        
    except Exception as e:
        print(f"❌ Agent stats error: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to retrieve agent statistics: {str(e)}"
        )


@router.get("/config")
async def get_routing_config(
    current_user: dict = Depends(get_current_user_from_token)
):
    """Get current routing configuration."""
    try:
        config = RoutingConfig()
        
        return {
            "analysis_model": config.ANALYSIS_MODEL,
            "analysis_timeout": config.ANALYSIS_TIMEOUT,
            "max_retries": config.MAX_RETRIES,
            "endpoints": {
                "chat_completions": config.OPENAI_CHAT_COMPLETIONS,
                "responses": config.OPENAI_RESPONSES
            }
        }
        
    except Exception as e:
        print(f"❌ Get config error: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to retrieve routing configuration: {str(e)}"
        )


@router.get("/health")
async def agent_health_check():
    """Health check endpoint for agent routing system."""
    try:
        # Basic health check - verify agent can be initialized
        api_key = os.getenv("OPENAI_API_KEY")
        is_configured = bool(api_key)
        
        return {
            "status": "healthy" if is_configured else "configuration_missing",
            "service": "agent_routing",
            "api_key_configured": is_configured,
            "timestamp": "2025-08-30T12:00:00Z"
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "service": "agent_routing",
            "timestamp": "2025-08-30T12:00:00Z"
        }
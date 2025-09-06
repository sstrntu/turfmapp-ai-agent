"""
Agent Settings API - Control Tool Usage and Behavior

This module provides endpoints for users to control agent behavior,
tool usage preferences, and view analytics about their agent's performance.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional, Literal
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ...core.simple_auth import get_current_user_from_token
from ...services.tool_analytics import tool_analytics
from ...services.response_evaluator import response_evaluator
from ...services.intelligent_classifier import intelligent_classifier

router = APIRouter()

# User preference models
class ToolPreferences(BaseModel):
    """User preferences for tool usage."""
    auto_tool_usage: bool = Field(True, description="Allow agent to automatically decide tool usage")
    preferred_approach: Literal["conservative", "balanced", "aggressive"] = Field("balanced", description="Tool usage preference")
    max_tools_per_query: int = Field(3, ge=1, le=10, description="Maximum tools to use per query")
    enable_gmail_tools: bool = Field(True, description="Enable Gmail integration")
    enable_drive_tools: bool = Field(True, description="Enable Google Drive integration")
    enable_calendar_tools: bool = Field(True, description="Enable Google Calendar integration")
    
class ClassificationPreferences(BaseModel):
    """User preferences for query classification."""
    classification_sensitivity: Literal["strict", "normal", "lenient"] = Field("normal", description="How strictly to classify queries")
    prefer_tier1_classification: bool = Field(True, description="Prefer fast pattern-based classification")
    allow_llm_classification: bool = Field(True, description="Allow expensive LLM-based classification for complex queries")

class AgentSettings(BaseModel):
    """Complete agent settings."""
    tool_preferences: ToolPreferences
    classification_preferences: ClassificationPreferences
    analytics_enabled: bool = Field(True, description="Enable analytics tracking")
    
class AgentSettingsUpdate(BaseModel):
    """Update agent settings."""
    tool_preferences: Optional[ToolPreferences] = None
    classification_preferences: Optional[ClassificationPreferences] = None
    analytics_enabled: Optional[bool] = None

# In-memory storage for user settings (in production, use database)
user_settings: Dict[str, AgentSettings] = {}

def get_user_agent_settings(user_id: str) -> AgentSettings:
    """Get user's agent settings with defaults."""
    if user_id not in user_settings:
        # Create default settings
        user_settings[user_id] = AgentSettings(
            tool_preferences=ToolPreferences(),
            classification_preferences=ClassificationPreferences(),
            analytics_enabled=True
        )
    return user_settings[user_id]

@router.get("/settings", response_model=AgentSettings)
async def get_agent_settings(
    current_user: dict = Depends(get_current_user_from_token)
):
    """Get current agent settings for the user."""
    user_id = current_user["id"]
    settings = get_user_agent_settings(user_id)
    
    return settings

@router.put("/settings", response_model=AgentSettings)
async def update_agent_settings(
    settings_update: AgentSettingsUpdate,
    current_user: dict = Depends(get_current_user_from_token)
):
    """Update agent settings for the user."""
    user_id = current_user["id"]
    current_settings = get_user_agent_settings(user_id)
    
    # Update settings
    if settings_update.tool_preferences:
        current_settings.tool_preferences = settings_update.tool_preferences
    
    if settings_update.classification_preferences:
        current_settings.classification_preferences = settings_update.classification_preferences
    
    if settings_update.analytics_enabled is not None:
        current_settings.analytics_enabled = settings_update.analytics_enabled
    
    user_settings[user_id] = current_settings
    
    print(f"🔧 Updated agent settings for user {user_id}")
    
    return current_settings

@router.get("/analytics/overview")
async def get_analytics_overview(
    current_user: dict = Depends(get_current_user_from_token)
):
    """Get analytics overview for the user."""
    try:
        user_id = current_user["id"]
        
        # Get overall analytics
        overall_analytics = tool_analytics.get_overall_analytics()
        
        # Get user-specific analytics (filter by user_id)
        user_logs = [log for log in tool_analytics.usage_logs if log.get("user_id") == user_id]
        
        # Calculate user-specific metrics
        user_total_interactions = len(user_logs)
        user_tools_used = set(log["tool_name"] for log in user_logs)
        user_success_rate = (
            sum(1 for log in user_logs if log.get("success", False)) / max(user_total_interactions, 1)
        ) * 100 if user_total_interactions > 0 else 0
        
        # Get recent activity (last 7 days)
        from datetime import timedelta
        week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
        recent_logs = [log for log in user_logs if log["timestamp"] > week_ago]
        
        return {
            "user_analytics": {
                "total_interactions": user_total_interactions,
                "tools_used": list(user_tools_used),
                "success_rate": round(user_success_rate, 1),
                "recent_activity": len(recent_logs)
            },
            "system_analytics": {
                "total_system_interactions": overall_analytics["total_interactions"],
                "most_used_tools": overall_analytics["most_used_tools"],
                "system_performance": overall_analytics["tool_performance"]
            },
            "recommendations": tool_analytics.get_optimization_recommendations()
        }
        
    except Exception as e:
        print(f"❌ Error getting analytics overview: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to retrieve analytics: {str(e)}"
        )

@router.get("/analytics/classification")
async def get_classification_analytics(
    current_user: dict = Depends(get_current_user_from_token)
):
    """Get classification performance analytics."""
    try:
        # Get classification metrics
        classification_stats = {}
        for class_type, metrics in tool_analytics.classification_metrics.items():
            if metrics["total"] > 0:
                accuracy = (metrics["correct_predictions"] / metrics["total"]) * 100
                classification_stats[class_type] = {
                    "total_classifications": metrics["total"],
                    "accuracy_percentage": round(accuracy, 1),
                    "tier_usage": {
                        "tier1": metrics["tier1_used"],
                        "tier2": metrics["tier2_used"],
                        "tier3": metrics["tier3_used"]
                    }
                }
        
        # Get classifier information
        classifier_stats = intelligent_classifier.get_learning_stats()
        
        return {
            "classification_performance": classification_stats,
            "classifier_configuration": classifier_stats,
            "tier_efficiency": {
                "tier1_patterns": classifier_stats["general_knowledge_patterns"] + 
                                classifier_stats["personal_data_patterns"],
                "tier2_analysis": "Context-based analysis",
                "tier3_llm": "GPT-4O-mini analysis"
            }
        }
        
    except Exception as e:
        print(f"❌ Error getting classification analytics: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to retrieve classification analytics: {str(e)}"
        )

@router.get("/analytics/tools")
async def get_tool_analytics(
    tool_name: Optional[str] = Query(None, description="Specific tool to analyze"),
    current_user: dict = Depends(get_current_user_from_token)
):
    """Get detailed tool usage analytics."""
    try:
        if tool_name:
            # Get specific tool report
            tool_report = tool_analytics.get_tool_performance_report(tool_name)
            return {"tool_report": tool_report}
        else:
            # Get all tool analytics
            overall = tool_analytics.get_overall_analytics()
            return {
                "tool_performance": overall["tool_performance"],
                "approach_effectiveness": overall["approach_effectiveness"],
                "optimization_recommendations": overall["optimization_recommendations"]
            }
    
    except Exception as e:
        print(f"❌ Error getting tool analytics: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to retrieve tool analytics: {str(e)}"
        )

@router.post("/test-classification")
async def test_classification(
    query: str = Query(..., description="Query to test classification"),
    current_user: dict = Depends(get_current_user_from_token)
):
    """Test query classification for debugging and tuning."""
    try:
        # Classify the query
        classification = await intelligent_classifier.classify_request(query, [])
        
        return {
            "query": query,
            "classification": classification,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        print(f"❌ Error testing classification: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to test classification: {str(e)}"
        )

@router.get("/health")
async def agent_health_check():
    """Health check for agent services."""
    try:
        # Test core components
        health_status = {
            "status": "healthy",
            "components": {
                "request_classifier": "operational",
                "tool_analytics": "operational", 
                "response_evaluator": "operational"
            },
            "statistics": {
                "total_classifications": sum(
                    metrics["total"] for metrics in tool_analytics.classification_metrics.values()
                ),
                "total_tool_usages": sum(
                    metrics["total_uses"] for metrics in tool_analytics.performance_metrics.values()
                ),
                "cache_sizes": {
                    "analytics_logs": len(tool_analytics.usage_logs),
                    "evaluation_cache": len(response_evaluator.evaluation_cache)
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return health_status
    
    except Exception as e:
        print(f"❌ Agent health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@router.post("/analytics/export")
async def export_analytics_data(
    current_user: dict = Depends(get_current_user_from_token)
):
    """Export analytics data for the user."""
    try:
        user_id = current_user["id"]
        
        # Export all analytics data
        full_export = tool_analytics.export_analytics_data()
        
        # Filter for user-specific data only for privacy
        user_logs = [log for log in full_export["usage_logs"] if log.get("user_id") == user_id]
        
        user_export = {
            "user_id": user_id,
            "export_timestamp": full_export["export_timestamp"],
            "user_usage_logs": user_logs,
            "user_statistics": {
                "total_interactions": len(user_logs),
                "tools_used": list(set(log["tool_name"] for log in user_logs)),
                "date_range": {
                    "first_interaction": min((log["timestamp"] for log in user_logs), default=None),
                    "last_interaction": max((log["timestamp"] for log in user_logs), default=None)
                }
            },
            "system_summary": full_export["summary"]  # Non-personal aggregate data
        }
        
        return user_export
    
    except Exception as e:
        print(f"❌ Error exporting analytics: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to export analytics: {str(e)}"
        )

@router.delete("/analytics/data")
async def clear_user_analytics(
    confirm: bool = Query(False, description="Confirmation to delete data"),
    current_user: dict = Depends(get_current_user_from_token)
):
    """Clear user's analytics data."""
    if not confirm:
        raise HTTPException(
            status_code=400, 
            detail="Must set confirm=true to delete analytics data"
        )
    
    try:
        user_id = current_user["id"]
        
        # Remove user's data from analytics
        original_count = len(tool_analytics.usage_logs)
        tool_analytics.usage_logs = [
            log for log in tool_analytics.usage_logs 
            if log.get("user_id") != user_id
        ]
        removed_count = original_count - len(tool_analytics.usage_logs)
        
        # Clear user settings
        if user_id in user_settings:
            del user_settings[user_id]
        
        return {
            "message": f"Cleared {removed_count} analytics records for user",
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        print(f"❌ Error clearing user analytics: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to clear analytics: {str(e)}"
        )
"""
Tool Usage Analytics - Track and Analyze Tool Performance

This service tracks tool usage patterns, success rates, and effectiveness to 
continuously improve the agent's decision-making about when and how to use tools.
"""

from __future__ import annotations

import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

class ToolAnalytics:
    """Analytics service for tracking tool usage and effectiveness."""
    
    def __init__(self):
        # In-memory storage (in production, this should use a database)
        self.usage_logs: List[Dict[str, Any]] = []
        self.performance_metrics: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "total_uses": 0,
            "successful_uses": 0,
            "response_times": [],
            "effectiveness_scores": [],
            "user_satisfaction_scores": [],
            "last_used": None,
            "common_parameters": defaultdict(int),
            "failure_reasons": defaultdict(int)
        })
        
        self.classification_metrics: Dict[str, Dict[str, int]] = defaultdict(lambda: {
            "total": 0,
            "correct_predictions": 0,
            "tier1_used": 0,
            "tier2_used": 0,
            "tier3_used": 0
        })
        
        self.approach_effectiveness: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "uses": 0,
            "avg_quality_score": 0.0,
            "quality_scores": []
        })
    
    def log_tool_usage(
        self,
        tool_name: str,
        user_id: str,
        user_query: str,
        parameters: Dict[str, Any],
        result: Dict[str, Any],
        response_time: float,
        approach: str = None,
        classification: Dict[str, Any] = None
    ) -> None:
        """Log a tool usage event."""
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "tool_name": tool_name,
            "user_id": user_id,
            "user_query": user_query[:100],  # Truncate for privacy
            "parameters": parameters,
            "success": result.get("success", False),
            "response_time": response_time,
            "approach": approach,
            "classification": classification,
            "result_data_length": len(str(result.get("response", ""))),
            "error": result.get("error") if not result.get("success") else None
        }
        
        self.usage_logs.append(log_entry)
        
        # Update performance metrics
        metrics = self.performance_metrics[tool_name]
        metrics["total_uses"] += 1
        metrics["last_used"] = datetime.utcnow().isoformat()
        metrics["response_times"].append(response_time)
        
        if result.get("success"):
            metrics["successful_uses"] += 1
        else:
            error_msg = result.get("error", "unknown_error")
            metrics["failure_reasons"][error_msg] += 1
        
        # Track parameter usage
        for param, value in parameters.items():
            if param != "user_id":  # Don't track user_id for privacy
                metrics["common_parameters"][f"{param}:{str(value)[:20]}"] += 1
        
        print(f"📊 Logged tool usage: {tool_name} (success: {result.get('success')}, {response_time:.2f}s)")
    
    def log_classification_result(
        self,
        classification: Dict[str, Any],
        actual_outcome: str,
        was_correct: bool
    ) -> None:
        """Log classification accuracy."""
        
        classification_type = classification.get("classification", "UNKNOWN")
        tier_used = classification.get("tier_used", 0)
        
        metrics = self.classification_metrics[classification_type]
        metrics["total"] += 1
        
        if was_correct:
            metrics["correct_predictions"] += 1
        
        if tier_used == 1:
            metrics["tier1_used"] += 1
        elif tier_used == 2:
            metrics["tier2_used"] += 1
        elif tier_used == 3:
            metrics["tier3_used"] += 1
        
        print(f"📊 Logged classification: {classification_type} (tier {tier_used}, correct: {was_correct})")
    
    def log_approach_effectiveness(
        self,
        approach: str,
        quality_score: float
    ) -> None:
        """Log the effectiveness of different approaches."""
        
        metrics = self.approach_effectiveness[approach]
        metrics["uses"] += 1
        metrics["quality_scores"].append(quality_score)
        
        # Recalculate average
        metrics["avg_quality_score"] = statistics.mean(metrics["quality_scores"])
        
        print(f"📊 Logged approach effectiveness: {approach} (score: {quality_score:.2f})")
    
    def log_user_feedback(
        self,
        tool_name: str,
        satisfaction_score: float,
        feedback: str = None
    ) -> None:
        """Log user feedback for tool effectiveness."""
        
        metrics = self.performance_metrics[tool_name]
        metrics["user_satisfaction_scores"].append(satisfaction_score)
        
        if feedback:
            # Could store feedback for qualitative analysis
            pass
    
    def get_tool_performance_report(self, tool_name: str) -> Dict[str, Any]:
        """Get detailed performance report for a specific tool."""
        
        if tool_name not in self.performance_metrics:
            return {"error": f"No data found for tool: {tool_name}"}
        
        metrics = self.performance_metrics[tool_name]
        
        success_rate = (metrics["successful_uses"] / max(metrics["total_uses"], 1)) * 100
        avg_response_time = statistics.mean(metrics["response_times"]) if metrics["response_times"] else 0
        avg_effectiveness = statistics.mean(metrics["effectiveness_scores"]) if metrics["effectiveness_scores"] else None
        avg_satisfaction = statistics.mean(metrics["user_satisfaction_scores"]) if metrics["user_satisfaction_scores"] else None
        
        return {
            "tool_name": tool_name,
            "total_uses": metrics["total_uses"],
            "success_rate": round(success_rate, 2),
            "avg_response_time": round(avg_response_time, 3),
            "avg_effectiveness_score": round(avg_effectiveness, 3) if avg_effectiveness else None,
            "avg_user_satisfaction": round(avg_satisfaction, 3) if avg_satisfaction else None,
            "last_used": metrics["last_used"],
            "common_parameters": dict(metrics["common_parameters"]),
            "failure_reasons": dict(metrics["failure_reasons"]),
            "usage_trend": self._get_usage_trend(tool_name)
        }
    
    def get_overall_analytics(self) -> Dict[str, Any]:
        """Get comprehensive analytics across all tools and classifications."""
        
        # Tool performance summary
        tool_summary = {}
        for tool_name, metrics in self.performance_metrics.items():
            if metrics["total_uses"] > 0:
                success_rate = (metrics["successful_uses"] / metrics["total_uses"]) * 100
                tool_summary[tool_name] = {
                    "uses": metrics["total_uses"],
                    "success_rate": round(success_rate, 1)
                }
        
        # Classification accuracy
        classification_accuracy = {}
        for class_type, metrics in self.classification_metrics.items():
            if metrics["total"] > 0:
                accuracy = (metrics["correct_predictions"] / metrics["total"]) * 100
                classification_accuracy[class_type] = {
                    "total": metrics["total"],
                    "accuracy": round(accuracy, 1),
                    "tier_distribution": {
                        "tier1": metrics["tier1_used"],
                        "tier2": metrics["tier2_used"], 
                        "tier3": metrics["tier3_used"]
                    }
                }
        
        # Approach effectiveness
        approach_summary = {}
        for approach, metrics in self.approach_effectiveness.items():
            if metrics["uses"] > 0:
                approach_summary[approach] = {
                    "uses": metrics["uses"],
                    "avg_quality": round(metrics["avg_quality_score"], 3)
                }
        
        # Recent trends
        recent_logs = [log for log in self.usage_logs 
                      if self._is_recent(log["timestamp"], hours=24)]
        
        return {
            "total_interactions": len(self.usage_logs),
            "recent_24h_interactions": len(recent_logs),
            "tool_performance": tool_summary,
            "classification_accuracy": classification_accuracy,
            "approach_effectiveness": approach_summary,
            "most_used_tools": self._get_most_used_tools(),
            "optimization_recommendations": self._generate_recommendations()
        }
    
    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Generate recommendations for improving tool usage."""
        
        recommendations = []
        
        # Analyze tool performance for recommendations
        for tool_name, metrics in self.performance_metrics.items():
            if metrics["total_uses"] < 3:  # Not enough data
                continue
                
            success_rate = (metrics["successful_uses"] / metrics["total_uses"]) * 100
            avg_response_time = statistics.mean(metrics["response_times"])
            
            # Low success rate recommendation
            if success_rate < 50:
                recommendations.append({
                    "type": "tool_reliability",
                    "priority": "high",
                    "tool": tool_name,
                    "issue": f"Low success rate ({success_rate:.1f}%)",
                    "suggestion": "Review tool parameters or consider alternative tools",
                    "data": {"success_rate": success_rate, "total_uses": metrics["total_uses"]}
                })
            
            # Slow response time recommendation
            if avg_response_time > 5.0:
                recommendations.append({
                    "type": "performance",
                    "priority": "medium",
                    "tool": tool_name,
                    "issue": f"Slow response time ({avg_response_time:.1f}s)",
                    "suggestion": "Consider caching or parameter optimization",
                    "data": {"avg_response_time": avg_response_time}
                })
        
        # Classification accuracy recommendations
        for class_type, metrics in self.classification_metrics.items():
            if metrics["total"] < 5:  # Not enough data
                continue
                
            accuracy = (metrics["correct_predictions"] / metrics["total"]) * 100
            if accuracy < 70:
                recommendations.append({
                    "type": "classification_accuracy",
                    "priority": "high",
                    "classification": class_type,
                    "issue": f"Low classification accuracy ({accuracy:.1f}%)",
                    "suggestion": "Improve classification patterns or training",
                    "data": {"accuracy": accuracy, "total": metrics["total"]}
                })
        
        # Tier usage recommendations
        total_classifications = sum(metrics["total"] for metrics in self.classification_metrics.values())
        if total_classifications > 10:
            tier3_usage = sum(metrics["tier3_used"] for metrics in self.classification_metrics.values())
            tier3_ratio = (tier3_usage / total_classifications) * 100
            
            if tier3_ratio > 30:  # Too much expensive LLM usage
                recommendations.append({
                    "type": "cost_optimization",
                    "priority": "medium",
                    "issue": f"High Tier 3 LLM usage ({tier3_ratio:.1f}%)",
                    "suggestion": "Improve Tier 1 and Tier 2 classification patterns",
                    "data": {"tier3_ratio": tier3_ratio, "total_classifications": total_classifications}
                })
        
        return sorted(recommendations, key=lambda x: {"high": 3, "medium": 2, "low": 1}[x["priority"]], reverse=True)
    
    def _get_usage_trend(self, tool_name: str, hours: int = 24) -> Dict[str, Any]:
        """Get usage trend for a specific tool."""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        recent_logs = [
            log for log in self.usage_logs 
            if log["tool_name"] == tool_name and 
            datetime.fromisoformat(log["timestamp"]) > cutoff_time
        ]
        
        if not recent_logs:
            return {"trend": "no_recent_data", "recent_uses": 0}
        
        # Group by hour to show trend
        hourly_usage = defaultdict(int)
        for log in recent_logs:
            hour = datetime.fromisoformat(log["timestamp"]).replace(minute=0, second=0, microsecond=0)
            hourly_usage[hour] += 1
        
        usage_values = list(hourly_usage.values())
        
        if len(usage_values) >= 2:
            # Simple trend calculation
            recent_avg = statistics.mean(usage_values[-3:])  # Last 3 hours
            earlier_avg = statistics.mean(usage_values[:-3]) if len(usage_values) > 3 else usage_values[0]
            
            if recent_avg > earlier_avg * 1.2:
                trend = "increasing"
            elif recent_avg < earlier_avg * 0.8:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
        
        return {
            "trend": trend,
            "recent_uses": len(recent_logs),
            "hourly_distribution": dict(hourly_usage)
        }
    
    def _get_most_used_tools(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get most frequently used tools."""
        
        tool_usage = [(tool, metrics["total_uses"]) 
                     for tool, metrics in self.performance_metrics.items()]
        
        tool_usage.sort(key=lambda x: x[1], reverse=True)
        
        return [
            {"tool": tool, "uses": uses} 
            for tool, uses in tool_usage[:limit]
        ]
    
    def _is_recent(self, timestamp_str: str, hours: int = 24) -> bool:
        """Check if timestamp is within recent hours."""
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            return timestamp > cutoff
        except:
            return False
    
    def _generate_recommendations(self) -> List[str]:
        """Generate high-level optimization recommendations."""
        
        recommendations = []
        
        # Check if any tools have very low success rates
        problematic_tools = [
            tool for tool, metrics in self.performance_metrics.items()
            if metrics["total_uses"] > 5 and (metrics["successful_uses"] / metrics["total_uses"]) < 0.5
        ]
        
        if problematic_tools:
            recommendations.append(f"Review configuration for tools with low success rates: {', '.join(problematic_tools)}")
        
        # Check classification accuracy
        total_classifications = sum(metrics["total"] for metrics in self.classification_metrics.values())
        if total_classifications > 10:
            total_correct = sum(metrics["correct_predictions"] for metrics in self.classification_metrics.values())
            overall_accuracy = (total_correct / total_classifications) * 100
            
            if overall_accuracy < 75:
                recommendations.append("Consider improving classification patterns - overall accuracy is below 75%")
        
        # Check for tier 3 overuse
        if total_classifications > 20:
            tier3_usage = sum(metrics["tier3_used"] for metrics in self.classification_metrics.values())
            if (tier3_usage / total_classifications) > 0.25:
                recommendations.append("High LLM usage detected - consider strengthening Tier 1 and Tier 2 classification rules")
        
        # Tool diversity check
        active_tools = len([t for t, m in self.performance_metrics.items() if m["total_uses"] > 0])
        if active_tools < 3 and len(self.usage_logs) > 20:
            recommendations.append("Limited tool diversity - consider expanding tool usage for better coverage")
        
        return recommendations or ["System is performing well - no immediate optimizations needed"]
    
    def export_analytics_data(self) -> Dict[str, Any]:
        """Export all analytics data for backup or analysis."""
        
        return {
            "export_timestamp": datetime.utcnow().isoformat(),
            "usage_logs": self.usage_logs,
            "performance_metrics": dict(self.performance_metrics),
            "classification_metrics": dict(self.classification_metrics),
            "approach_effectiveness": dict(self.approach_effectiveness),
            "summary": self.get_overall_analytics()
        }
    
    def clear_old_data(self, days: int = 30) -> int:
        """Clear analytics data older than specified days."""
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Clear old usage logs
        original_count = len(self.usage_logs)
        self.usage_logs = [
            log for log in self.usage_logs
            if datetime.fromisoformat(log["timestamp"]) > cutoff
        ]
        
        removed_count = original_count - len(self.usage_logs)
        
        print(f"📊 Cleared {removed_count} analytics records older than {days} days")
        
        return removed_count


# Global instance
tool_analytics = ToolAnalytics()
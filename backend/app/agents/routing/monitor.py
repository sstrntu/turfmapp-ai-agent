"""Performance monitoring for routing and API calls"""
import time
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict, deque


@dataclass
class RequestMetrics:
    """Metrics for a single request"""
    api_type: str  # "responses" or "chat_completions"
    start_time: float
    end_time: Optional[float] = None
    success: bool = False
    error: Optional[str] = None
    response_tokens: int = 0
    routing_decision_time: float = 0
    
    @property
    def duration(self) -> float:
        """Get request duration in seconds"""
        if self.end_time is None:
            return time.time() - self.start_time
        return self.end_time - self.start_time


class PerformanceMonitor:
    """Monitor and track API performance metrics"""
    
    def __init__(self, max_history: int = 100):
        self._requests: deque = deque(maxlen=max_history)
        self._api_stats: Dict[str, Dict] = defaultdict(lambda: {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_duration": 0.0,
            "avg_duration": 0.0,
            "min_duration": float("inf"),
            "max_duration": 0.0
        })
        self._lock = asyncio.Lock()
    
    def start_request(self, api_type: str) -> RequestMetrics:
        """Start tracking a new request"""
        return RequestMetrics(
            api_type=api_type,
            start_time=time.time()
        )
    
    async def end_request(
        self, 
        metrics: RequestMetrics, 
        success: bool = True, 
        error: Optional[str] = None,
        response_tokens: int = 0
    ) -> None:
        """End request tracking and update stats"""
        async with self._lock:
            metrics.end_time = time.time()
            metrics.success = success
            metrics.error = error
            metrics.response_tokens = response_tokens
            
            self._requests.append(metrics)
            
            # Update API stats
            stats = self._api_stats[metrics.api_type]
            stats["total_requests"] += 1
            
            if success:
                stats["successful_requests"] += 1
            else:
                stats["failed_requests"] += 1
            
            duration = metrics.duration
            stats["total_duration"] += duration
            stats["avg_duration"] = stats["total_duration"] / stats["total_requests"]
            stats["min_duration"] = min(stats["min_duration"], duration)
            stats["max_duration"] = max(stats["max_duration"], duration)
    
    async def get_stats(self) -> Dict:
        """Get current performance statistics"""
        async with self._lock:
            recent_requests = list(self._requests)[-10:]  # Last 10 requests
            
            # Calculate recent success rate
            if recent_requests:
                recent_success_rate = sum(1 for r in recent_requests if r.success) / len(recent_requests)
            else:
                recent_success_rate = 0.0
            
            return {
                "total_requests": len(self._requests),
                "recent_success_rate": recent_success_rate,
                "api_stats": dict(self._api_stats),
                "recent_requests": [
                    {
                        "api_type": r.api_type,
                        "duration": r.duration,
                        "success": r.success,
                        "error": r.error,
                        "response_tokens": r.response_tokens
                    }
                    for r in recent_requests
                ]
            }
    
    async def log_performance_summary(self) -> None:
        """Log current performance summary"""
        stats = await self.get_stats()
        
        print("\n📊 API Performance Summary:")
        print(f"   Total requests: {stats['total_requests']}")
        print(f"   Recent success rate: {stats['recent_success_rate']:.1%}")
        
        for api_type, api_stats in stats['api_stats'].items():
            print(f"\n   {api_type.upper()} API:")
            print(f"     Total: {api_stats['total_requests']}")
            print(f"     Success: {api_stats['successful_requests']}")
            print(f"     Failed: {api_stats['failed_requests']}")
            print(f"     Avg Duration: {api_stats['avg_duration']:.2f}s")
            print(f"     Min/Max: {api_stats['min_duration']:.2f}s / {api_stats['max_duration']:.2f}s")
    
    async def get_optimization_recommendations(self) -> List[str]:
        """Get performance optimization recommendations"""
        recommendations = []
        stats = await self.get_stats()
        
        for api_type, api_stats in stats['api_stats'].items():
            if api_stats['total_requests'] == 0:
                continue
                
            success_rate = api_stats['successful_requests'] / api_stats['total_requests']
            avg_duration = api_stats['avg_duration']
            
            if success_rate < 0.95:  # Less than 95% success rate
                recommendations.append(
                    f"{api_type} API has low success rate ({success_rate:.1%}). Consider implementing better retry logic."
                )
            
            if avg_duration > 30:  # Longer than 30 seconds average
                recommendations.append(
                    f"{api_type} API is slow (avg {avg_duration:.1f}s). Consider reducing max_tokens or using faster models."
                )
            
            if api_type == "responses" and avg_duration > 20:  # Responses API taking too long
                recommendations.append(
                    "Responses API is slow. Consider more aggressive fallback to Chat Completions API."
                )
        
        return recommendations


# Global performance monitor instance
performance_monitor = PerformanceMonitor()
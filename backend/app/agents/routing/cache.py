"""Simple in-memory cache for routing decisions"""
import asyncio
import hashlib
import time
from typing import Dict, Any, Optional


class RoutingCache:
    """Simple in-memory cache for routing decisions to speed up repeated questions"""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):  # 5 minute TTL
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._lock = asyncio.Lock()
    
    def _get_cache_key(self, question: str) -> str:
        """Generate cache key from question"""
        # Normalize question for better cache hits
        normalized = question.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        """Check if cache entry is expired"""
        return time.time() - entry["timestamp"] > self.ttl_seconds
    
    async def get(self, question: str) -> Optional[bool]:
        """Get cached routing decision"""
        async with self._lock:
            key = self._get_cache_key(question)
            entry = self._cache.get(key)
            
            if entry is None:
                return None
                
            if self._is_expired(entry):
                del self._cache[key]
                return None
                
            print(f"🚀 Cache hit for question: {question[:50]}...")
            return entry["decision"]
    
    async def set(self, question: str, decision: bool) -> None:
        """Cache routing decision"""
        async with self._lock:
            # Evict oldest entries if cache is full
            if len(self._cache) >= self.max_size:
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k]["timestamp"])
                del self._cache[oldest_key]
            
            key = self._get_cache_key(question)
            self._cache[key] = {
                "decision": decision,
                "timestamp": time.time()
            }
    
    async def clear(self) -> None:
        """Clear all cached entries"""
        async with self._lock:
            self._cache.clear()
    
    async def cleanup_expired(self) -> None:
        """Remove expired entries"""
        async with self._lock:
            current_time = time.time()
            expired_keys = [
                key for key, entry in self._cache.items()
                if current_time - entry["timestamp"] > self.ttl_seconds
            ]
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                print(f"🧹 Cleaned up {len(expired_keys)} expired cache entries")


# Global cache instance
routing_cache = RoutingCache()
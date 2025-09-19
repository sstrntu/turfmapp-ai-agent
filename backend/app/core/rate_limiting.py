"""
Rate Limiting Configuration for TURFMAPP API

Provides rate limiting for OAuth and sensitive endpoints.
"""

from fastapi import Request, Response
import os
from typing import Optional

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
    import redis
    RATE_LIMITING_AVAILABLE = True
except ImportError:
    # Fallback for when slowapi/redis is not available
    RATE_LIMITING_AVAILABLE = False

    # Create dummy classes for development
    class RateLimitExceeded(Exception):
        def __init__(self, detail: str, retry_after: int = 60):
            self.detail = detail
            self.retry_after = retry_after

    class Limiter:
        def __init__(self, key_func=None, storage_uri=None, default_limits=None):
            pass

        def limit(self, rate: str):
            def decorator(func):
                return func
            return decorator

    def get_remote_address(request: Request) -> str:
        return request.client.host if request.client else "unknown"


def get_user_id_or_ip(request: Request) -> str:
    """
    Get rate limiting key - use user ID if authenticated, otherwise IP address.
    """
    # Try to get user ID from the request if authenticated
    user = getattr(request.state, 'user', None)
    if user and hasattr(user, 'get') and user.get('id'):
        return f"user:{user['id']}"

    # Fallback to IP address
    return f"ip:{get_remote_address(request)}"


def get_redis_connection():
    """Get Redis connection for rate limiting storage."""
    if not RATE_LIMITING_AVAILABLE:
        return None

    redis_url = os.getenv('REDIS_URL')
    if redis_url:
        try:
            import redis
            return redis.from_url(redis_url)
        except Exception:
            # Redis connection failed, fallback to in-memory
            return None
    return None


# Initialize rate limiter with Redis if available, otherwise in-memory
redis_client = get_redis_connection()

if RATE_LIMITING_AVAILABLE:
    if redis_client:
        # Use Redis for distributed rate limiting
        limiter = Limiter(
            key_func=get_user_id_or_ip,
            storage_uri=os.getenv('REDIS_URL', 'redis://localhost:6379')
        )
    else:
        # Use in-memory storage for development
        limiter = Limiter(
            key_func=get_user_id_or_ip,
            default_limits=["1000/hour"]  # Global default limit
        )
else:
    # Dummy limiter when slowapi is not available
    limiter = Limiter()


# Custom rate limit exceeded handler
def custom_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Custom handler for rate limit exceeded errors."""
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=429,
        content={
            "error_code": "RATE_LIMIT_EXCEEDED",
            "message": f"Rate limit exceeded: {exc.detail}",
            "retry_after": exc.retry_after,
            "limit": exc.detail
        },
        headers={"Retry-After": str(exc.retry_after)}
    )


# Rate limiting decorators for different endpoint types
class RateLimits:
    """Rate limiting configurations for different endpoint types."""

    # OAuth endpoints - more restrictive
    OAUTH_AUTH_URL = "5/minute"          # Getting auth URL
    OAUTH_CALLBACK = "10/minute"         # OAuth callbacks
    OAUTH_REFRESH = "20/minute"          # Token refresh

    # Google API endpoints - moderate limits
    GMAIL_READ = "100/minute"            # Reading Gmail
    DRIVE_READ = "100/minute"            # Reading Drive files
    CALENDAR_READ = "100/minute"         # Reading Calendar

    # Google API write operations - more restrictive
    DRIVE_WRITE = "20/minute"            # Drive file operations
    GMAIL_SEND = "10/minute"             # Sending emails

    # Admin endpoints - restrictive
    ADMIN_OPERATIONS = "30/minute"       # Admin user management

    # Account management - moderate
    ACCOUNT_MANAGEMENT = "50/minute"     # Google account management


def apply_oauth_rate_limit(limit: str = RateLimits.OAUTH_CALLBACK):
    """Apply rate limiting to OAuth endpoints."""
    return limiter.limit(limit)


def apply_google_api_rate_limit(limit: str = RateLimits.GMAIL_READ):
    """Apply rate limiting to Google API endpoints."""
    return limiter.limit(limit)


def apply_admin_rate_limit(limit: str = RateLimits.ADMIN_OPERATIONS):
    """Apply rate limiting to admin endpoints."""
    return limiter.limit(limit)


def apply_account_rate_limit(limit: str = RateLimits.ACCOUNT_MANAGEMENT):
    """Apply rate limiting to account management endpoints."""
    return limiter.limit(limit)


# Middleware setup function
def setup_rate_limiting(app):
    """Setup rate limiting middleware for the FastAPI app."""
    if RATE_LIMITING_AVAILABLE:
        # Add rate limiting middleware
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, custom_rate_limit_exceeded_handler)

        # Add SlowAPI middleware
        app.add_middleware(SlowAPIMiddleware)

    return app


# Health check for rate limiting system
def check_rate_limiting_health() -> dict:
    """Check if rate limiting system is working properly."""
    if not RATE_LIMITING_AVAILABLE:
        return {
            "status": "disabled",
            "storage": "none",
            "redis_connected": False,
            "message": "Rate limiting dependencies not installed"
        }

    try:
        if redis_client:
            # Test Redis connection
            redis_client.ping()
            return {
                "status": "healthy",
                "storage": "redis",
                "redis_connected": True
            }
        else:
            return {
                "status": "healthy",
                "storage": "memory",
                "redis_connected": False
            }
    except Exception as e:
        return {
            "status": "degraded",
            "storage": "memory",
            "redis_connected": False,
            "error": str(e)
        }
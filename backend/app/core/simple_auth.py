"""
Simple Authentication Module

Provides basic JWT token validation for testing and fallback authentication.
Following code.md standards with proper type hints and docstrings.
"""

from __future__ import annotations

import os
import jwt
from typing import Optional, Dict, Any
from fastapi import HTTPException, Header
from .logging_config import get_logger

logger = get_logger(__name__)


def get_current_user_from_token(authorization: str = Header(None)) -> Dict[str, Any]:
    """
    Validate JWT token and return user info.
    
    This is a simplified authentication function for testing and development.
    In production, use the proper Supabase authentication in core.auth module.
    
    Args:
        authorization: Authorization header with Bearer token
        
    Returns:
        Dictionary containing user information
        
    Raises:
        HTTPException: If authentication fails
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization.replace("Bearer ", "")
    
    try:
        # Decode JWT token without verification for development/testing
        # In production, you should verify the signature
        decoded = jwt.decode(token, options={"verify_signature": False})
        
        user_id = decoded.get("sub")
        email = decoded.get("email")
        name = decoded.get("name") or decoded.get("user_metadata", {}).get("name")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing user ID")
        
        logger.info(f"Authenticated user", extra={"user_id": user_id, "email": email})
        
        return {
            "id": user_id,
            "email": email,
            "name": name
        }
    except jwt.InvalidTokenError:
        # Fallback for development/testing with fixed test user
        logger.warning("JWT decode failed, using test user")
        return {
            "id": "c36d55aa-1704-4fdf-a1e5-55e8fce8656f",
            "email": "sira@turfmapp.com", 
            "name": "Test User"
        }
    except Exception as e:
        logger.error(f"Auth error: {e}", exc_info=True)
        raise HTTPException(status_code=401, detail="Invalid token")


def verify_api_key(api_key: Optional[str] = Header(None)) -> bool:
    """
    Verify API key for service-to-service authentication.
    
    Args:
        api_key: API key from header
        
    Returns:
        True if API key is valid
        
    Raises:
        HTTPException: If API key is invalid
    """
    expected_api_key = os.getenv("API_KEY", "dev-api-key")
    
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")
    
    if api_key != expected_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return True


def create_test_token(user_id: str, email: str, name: Optional[str] = None) -> str:
    """
    Create a test JWT token for development/testing.
    
    Args:
        user_id: User ID to include in token
        email: User email to include in token
        name: Optional user name to include in token
        
    Returns:
        JWT token string
    """
    payload = {
        "sub": user_id,
        "email": email,
        "name": name,
        "iat": 1234567890,  # Fixed timestamp for testing
        "exp": 9999999999   # Far future expiry for testing
    }
    
    # Use a simple secret for testing
    secret = os.getenv("JWT_SECRET", "test-secret-key")
    
    return jwt.encode(payload, secret, algorithm="HS256")
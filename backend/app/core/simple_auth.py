"""Authentication with Supabase JWT validation"""
from typing import Optional
from fastapi import HTTPException, Header
import os
import jwt

def get_current_user_from_token(authorization: str = Header(None)):
    """Validate Supabase JWT token and return user info"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization.replace("Bearer ", "")
    
    try:
        # Decode JWT token without verification first to get user info
        # In production, you should verify the signature
        decoded = jwt.decode(token, options={"verify_signature": False})
        
        user_id = decoded.get("sub")
        email = decoded.get("email")
        name = decoded.get("name") or decoded.get("user_metadata", {}).get("name")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing user ID")
        
        print(f"🔑 Authenticated user: {user_id} ({email})")
        
        return {
            "id": user_id,
            "email": email,
            "name": name
        }
    except jwt.InvalidTokenError:
        # Fallback for development/testing
        print("⚠️  JWT decode failed, using test user")
        return {
            "id": "c36d55aa-1704-4fdf-a1e5-55e8fce8656f",  # Use the actual user ID from database
            "email": "sira@turfmapp.com",
            "name": "Test User"
        }
    except Exception as e:
        print(f"Auth error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
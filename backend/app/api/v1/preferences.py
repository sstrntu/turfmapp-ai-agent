"""User preferences API endpoints"""
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ...core.simple_auth import get_current_user_from_token

router = APIRouter()

# In-memory preferences storage (replace with Supabase later)
user_preferences: Dict[str, Dict[str, Any]] = {}


class PreferencesUpdate(BaseModel):
    """User preferences update model"""
    system_prompt: Optional[str] = None
    default_model: Optional[str] = None


class PreferencesResponse(BaseModel):
    """User preferences response model"""
    system_prompt: Optional[str] = None
    default_model: str = "gpt-4o"


@router.get("/me", response_model=PreferencesResponse)
async def get_user_preferences(
    current_user: dict = Depends(get_current_user_from_token)
):
    """Get current user's preferences"""
    try:
        user_id = current_user["id"]
        prefs = user_preferences.get(user_id, {})
        
        return PreferencesResponse(
            system_prompt=prefs.get("system_prompt"),
            default_model=prefs.get("default_model", "gpt-4o")
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching preferences: {str(e)}"
        )


@router.put("/me", response_model=PreferencesResponse)
async def update_user_preferences(
    preferences: PreferencesUpdate,
    current_user: dict = Depends(get_current_user_from_token)
):
    """Update current user's preferences"""
    try:
        user_id = current_user["id"]
        
        # Get existing preferences or create new
        if user_id not in user_preferences:
            user_preferences[user_id] = {}
        
        # Update preferences
        if preferences.system_prompt is not None:
            user_preferences[user_id]["system_prompt"] = preferences.system_prompt.strip()
        
        if preferences.default_model is not None:
            user_preferences[user_id]["default_model"] = preferences.default_model
        
        # Return updated preferences
        prefs = user_preferences[user_id]
        return PreferencesResponse(
            system_prompt=prefs.get("system_prompt"),
            default_model=prefs.get("default_model", "gpt-4o")
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating preferences: {str(e)}"
        )
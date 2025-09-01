from __future__ import annotations

from typing import Annotated, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status

from ...database import execute_query, execute_query_one
from ...core.auth import get_current_user_supabase

router = APIRouter()


@router.get("/profile")
async def get_profile(
    current_user: Annotated[Dict[str, Any], Depends(get_current_user_supabase)]
):
    """Get current user profile"""
    return current_user


@router.put("/profile")
async def update_profile(
    profile_data: Dict[str, Any],
    current_user: Annotated[Dict[str, Any], Depends(get_current_user_supabase)]
):
    """Update current user profile"""
    try:
        # Only allow updating name and avatar_url for regular users
        allowed_fields = {'name', 'avatar_url'}
        update_fields = []
        params = []
        param_count = 1
        
        for field, value in profile_data.items():
            if field in allowed_fields:
                update_fields.append(f"{field} = ${param_count}")
                params.append(value)
                param_count += 1
        
        if not update_fields:
            return current_user
        
        # Add updated_at and user_id
        update_fields.append("updated_at = NOW()")
        params.append(current_user["id"])
        
        query = f"""
            UPDATE turfmapp_agent.users 
            SET {', '.join(update_fields)}
            WHERE id = ${param_count}
            RETURNING id, email, name, avatar_url, role, status, created_at, updated_at, last_login_at
        """
        
        result = await execute_query_one(query, *params)
        return dict(result) if result else current_user
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating profile: {str(e)}"
        )


@router.get("/preferences")
async def get_preferences(
    current_user: Annotated[Dict[str, Any], Depends(get_current_user_supabase)]
):
    """Get current user preferences"""
    try:
        query = """
            SELECT id, user_id, system_prompt, default_model, settings, created_at, updated_at
            FROM turfmapp_agent.user_preferences 
            WHERE user_id = $1
        """
        preferences = await execute_query_one(query, current_user["id"])
        
        if not preferences:
            # Create default preferences if they don't exist
            import uuid
            pref_id = str(uuid.uuid4())
            create_query = """
                INSERT INTO turfmapp_agent.user_preferences (id, user_id, default_model, settings, created_at, updated_at)
                VALUES ($1, $2, $3, $4, NOW(), NOW())
                RETURNING id, user_id, system_prompt, default_model, settings, created_at, updated_at
            """
            preferences = await execute_query_one(create_query, pref_id, current_user["id"], "gpt-4o", "{}")
            
        return dict(preferences) if preferences else {}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching preferences: {str(e)}"
        )


@router.put("/preferences")
async def update_preferences(
    preferences_data: Dict[str, Any],
    current_user: Annotated[Dict[str, Any], Depends(get_current_user_supabase)]
):
    """Update current user preferences"""
    try:
        # Check if preferences exist
        check_query = "SELECT id FROM turfmapp_agent.user_preferences WHERE user_id = $1"
        existing = await execute_query_one(check_query, current_user["id"])
        
        if not existing:
            # Create new preferences
            import uuid
            pref_id = str(uuid.uuid4())
            create_query = """
                INSERT INTO turfmapp_agent.user_preferences (id, user_id, system_prompt, default_model, settings, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
                RETURNING id, user_id, system_prompt, default_model, settings, created_at, updated_at
            """
            import json
            result = await execute_query_one(
                create_query,
                pref_id,
                current_user["id"],
                preferences_data.get("system_prompt"),
                preferences_data.get("default_model", "gpt-4o"),
                json.dumps(preferences_data.get("settings", {}))
            )
        else:
            # Update existing preferences
            update_fields = []
            params = []
            param_count = 1
            
            for field, value in preferences_data.items():
                if field in ["system_prompt", "default_model"]:
                    update_fields.append(f"{field} = ${param_count}")
                    params.append(value)
                    param_count += 1
                elif field == "settings":
                    import json
                    update_fields.append(f"{field} = ${param_count}")
                    params.append(json.dumps(value))
                    param_count += 1
            
            if update_fields:
                update_fields.append("updated_at = NOW()")
                params.append(current_user["id"])
                
                query = f"""
                    UPDATE turfmapp_agent.user_preferences 
                    SET {', '.join(update_fields)}
                    WHERE user_id = ${param_count}
                    RETURNING id, user_id, system_prompt, default_model, settings, created_at, updated_at
                """
                
                result = await execute_query_one(query, *params)
            else:
                # No valid fields to update, get existing
                get_query = """
                    SELECT id, user_id, system_prompt, default_model, settings, created_at, updated_at
                    FROM turfmapp_agent.user_preferences 
                    WHERE user_id = $1
                """
                result = await execute_query_one(get_query, current_user["id"])
        
        return dict(result) if result else {}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating preferences: {str(e)}"
        )


@router.delete("/account")
async def delete_account(
    current_user: Annotated[Dict[str, Any], Depends(get_current_user_supabase)]
):
    """Delete current user account"""
    try:
        query = "DELETE FROM turfmapp_agent.users WHERE id = $1"
        await execute_query(query, current_user["id"])
        return {"message": "Account deleted successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting account: {str(e)}"
        )
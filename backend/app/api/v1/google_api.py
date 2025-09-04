from __future__ import annotations

import json
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from ...core.auth import get_current_user_supabase
from typing import Dict, Any
from ...services.google_oauth import google_oauth_service


router = APIRouter()


class GoogleTokens(BaseModel):
    """Model for storing Google OAuth tokens."""
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[float] = None


class GoogleAuthResponse(BaseModel):
    """Response model for Google auth operations."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class GoogleCallbackRequest(BaseModel):
    """Request model for Google OAuth callback."""
    code: str
    state: Optional[str] = None


# In-memory token storage (in production, use database)
user_google_tokens: Dict[str, GoogleTokens] = {}


@router.get("/auth/url", response_model=GoogleAuthResponse)
async def get_google_auth_url(
    current_user: Dict[str, Any] = Depends(get_current_user_supabase)
):
    """Get Google OAuth authorization URL."""
    try:
        auth_url = google_oauth_service.get_authorization_url(state=current_user["id"])
        
        return GoogleAuthResponse(
            success=True,
            message="Authorization URL generated",
            data={"auth_url": auth_url}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate auth URL: {str(e)}")


@router.get("/auth/callback")
async def handle_google_callback_get(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(None, description="State parameter"),
    error: str = Query(None, description="Error parameter if authentication failed")
):
    """Handle Google OAuth callback GET request (redirect from Google)."""
    if error:
        # Redirect to frontend with error
        return RedirectResponse(
            url=f"http://localhost:3005/google-callback.html?error={error}",
            status_code=302
        )
    
    if not code:
        # Redirect to frontend with error
        return RedirectResponse(
            url="http://localhost:3005/google-callback.html?error=no_code",
            status_code=302
        )
    
    # Redirect to frontend callback handler with the code and state
    return RedirectResponse(
        url=f"http://localhost:3005/google-callback.html?code={code}&state={state or ''}",
        status_code=302
    )


@router.post("/auth/callback", response_model=GoogleAuthResponse)
async def handle_google_callback(
    request: GoogleCallbackRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_supabase)
):
    """Handle Google OAuth callback."""
    try:
        # Debug logging
        print(f"🔍 DEBUG - Callback received:")
        print(f"  - request.code: {request.code[:20]}..." if request.code else "  - request.code: None")
        print(f"  - request.state: {request.state}")
        print(f"  - current_user id: {current_user.get('id')}")
        print(f"  - current_user: {current_user}")
        
        # Verify state matches current user (convert UUID to string for comparison)
        current_user_id = str(current_user["id"])
        if request.state != current_user_id:
            print(f"❌ State mismatch: '{request.state}' != '{current_user_id}'")
            raise HTTPException(status_code=400, detail=f"Invalid state parameter. Expected: {current_user_id}, Got: {request.state}")
        
        print(f"✅ State validation passed: {request.state}")
        
        # Exchange code for tokens
        token_data = await google_oauth_service.exchange_code_for_tokens(request.code, request.state)
        
        if not token_data:
            raise HTTPException(status_code=400, detail="Failed to exchange code for tokens")
        
        # Store tokens for the user (ensure string key for consistency)
        user_id_str = str(current_user["id"])
        user_google_tokens[user_id_str] = GoogleTokens(
            access_token=token_data['access_token'],
            refresh_token=token_data['refresh_token'],
            expires_at=token_data['expires_in']
        )
        
        print(f"✅ Stored Google tokens for user {user_id_str}")
        print(f"🔧 Token storage keys: {list(user_google_tokens.keys())}")
        
        return GoogleAuthResponse(
            success=True,
            message="Google authentication successful",
            data={
                "user_info": token_data['user_info'],
                "has_tokens": True
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")


@router.get("/auth/status", response_model=GoogleAuthResponse)
async def get_google_auth_status(
    current_user: Dict[str, Any] = Depends(get_current_user_supabase)
):
    """Check if user has valid Google tokens."""
    user_id_str = str(current_user["id"])
    has_tokens = user_id_str in user_google_tokens
    tokens = user_google_tokens.get(user_id_str) if has_tokens else None
    
    return GoogleAuthResponse(
        success=True,
        message="Auth status retrieved",
        data={
            "has_tokens": has_tokens,
            "expires_at": tokens.expires_at if tokens else None
        }
    )


def get_user_google_credentials(user_id: str):
    """Get Google credentials for a user."""
    print(f"🔍 Looking for tokens for user_id: '{user_id}' (type: {type(user_id)})")
    print(f"🔍 Available token keys: {list(user_google_tokens.keys())}")
    
    tokens = user_google_tokens.get(user_id)
    if not tokens:
        print(f"❌ No tokens found for user {user_id}")
        raise HTTPException(status_code=401, detail="Google authentication required")
    
    print(f"✅ Found tokens for user {user_id}")
    
    return google_oauth_service.get_credentials_from_token(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token
    )


# Gmail API endpoints
@router.get("/gmail/messages", response_model=Dict[str, Any])
async def get_gmail_messages(
    query: str = Query("", description="Gmail search query"),
    max_results: int = Query(10, ge=1, le=50, description="Maximum number of messages to return"),
    current_user: Dict[str, Any] = Depends(get_current_user_supabase)
):
    """Get Gmail messages for the authenticated user."""
    try:
        credentials = get_user_google_credentials(current_user["id"])
        messages = await google_oauth_service.get_gmail_messages(
            credentials=credentials,
            query=query,
            max_results=max_results
        )
        
        return messages
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Gmail messages: {str(e)}")


@router.get("/gmail/messages/{message_id}", response_model=Dict[str, Any])
async def get_gmail_message(
    message_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user_supabase)
):
    """Get full content of a specific Gmail message."""
    try:
        credentials = get_user_google_credentials(current_user["id"])
        message = await google_oauth_service.get_gmail_message_content(
            credentials=credentials,
            message_id=message_id
        )
        
        return message
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Gmail message: {str(e)}")


# Google Drive API endpoints
@router.get("/drive/files", response_model=Dict[str, Any])
async def get_drive_files(
    query: str = Query("", description="Drive search query"),
    max_results: int = Query(10, ge=1, le=50, description="Maximum number of files to return"),
    current_user: Dict[str, Any] = Depends(get_current_user_supabase)
):
    """Get Google Drive files for the authenticated user."""
    try:
        credentials = get_user_google_credentials(current_user["id"])
        files = await google_oauth_service.get_drive_files(
            credentials=credentials,
            query=query,
            max_results=max_results
        )
        
        return files
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Drive files: {str(e)}")


# Google Calendar API endpoints
@router.get("/calendar/events", response_model=Dict[str, Any])
async def get_calendar_events(
    calendar_id: str = Query("primary", description="Calendar ID"),
    max_results: int = Query(10, ge=1, le=50, description="Maximum number of events to return"),
    current_user: Dict[str, Any] = Depends(get_current_user_supabase)
):
    """Get Google Calendar events for the authenticated user."""
    try:
        credentials = get_user_google_credentials(current_user["id"])
        events = await google_oauth_service.get_calendar_events(
            credentials=credentials,
            calendar_id=calendar_id,
            max_results=max_results
        )
        
        return events
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Calendar events: {str(e)}")


@router.post("/auth/refresh", response_model=GoogleAuthResponse)
async def refresh_google_tokens(
    current_user: Dict[str, Any] = Depends(get_current_user_supabase)
):
    """Refresh Google access token."""
    try:
        user_id_str = str(current_user["id"])
        tokens = user_google_tokens.get(user_id_str)
        if not tokens or not tokens.refresh_token:
            raise HTTPException(status_code=401, detail="No refresh token available")
        
        new_tokens = google_oauth_service.refresh_access_token(tokens.refresh_token)
        if not new_tokens:
            raise HTTPException(status_code=401, detail="Failed to refresh tokens")
        
        # Update stored tokens
        user_google_tokens[user_id_str] = GoogleTokens(
            access_token=new_tokens['access_token'],
            refresh_token=new_tokens['refresh_token'] or tokens.refresh_token,
            expires_at=new_tokens['expires_in']
        )
        
        return GoogleAuthResponse(
            success=True,
            message="Tokens refreshed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token refresh failed: {str(e)}")


# Advanced Drive Operations
@router.post("/drive/create-folder")
async def create_folder_structure(
    folder_path: str = Form(...),
    root_folder: str = Form("TURFMAPP"),
    current_user: Dict[str, Any] = Depends(get_current_user_supabase)
):
    """Create nested folder structure in user's Drive."""
    try:
        credentials = get_user_google_credentials(current_user["id"])
        folder_id = await google_oauth_service.create_folder_structure(
            credentials, folder_path, root_folder
        )
        
        return {
            'success': True,
            'folder_id': folder_id,
            'folder_path': f"{root_folder}/{folder_path}",
            'message': 'Folder structure created successfully'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create folder structure: {str(e)}")


@router.post("/drive/upload")
async def upload_file_to_drive(
    file: UploadFile = File(...),
    folder_path: Optional[str] = Form(None),
    current_user: Dict[str, Any] = Depends(get_current_user_supabase)
):
    """Upload file to specific folder in user's Drive."""
    try:
        credentials = get_user_google_credentials(current_user["id"])
        
        # Read file content
        file_content = await file.read()
        
        # Upload to Drive
        result = await google_oauth_service.upload_file_to_drive(
            credentials, file_content, file.filename, folder_path
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@router.delete("/drive/files/{file_id}")
async def delete_file_from_drive(
    file_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user_supabase)
):
    """Delete file from user's Drive."""
    try:
        credentials = get_user_google_credentials(current_user["id"])
        result = await google_oauth_service.delete_file_from_drive(credentials, file_id)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


@router.get("/drive/folder/{folder_path:path}/files")
async def list_files_in_folder(
    folder_path: str,
    current_user: Dict[str, Any] = Depends(get_current_user_supabase)
):
    """List files in specific folder path."""
    try:
        credentials = get_user_google_credentials(current_user["id"])
        result = await google_oauth_service.list_files_in_folder(credentials, folder_path)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.get("/drive/folder-exists/{folder_path:path}")
async def check_folder_exists(
    folder_path: str,
    current_user: Dict[str, Any] = Depends(get_current_user_supabase)
):
    """Check if folder path exists in user's Drive."""
    try:
        credentials = get_user_google_credentials(current_user["id"])
        # Create a basic exists check by trying to find the folder
        try:
            folder_id = await google_oauth_service.create_folder_structure(credentials, folder_path)
            return {'exists': bool(folder_id), 'folder_id': folder_id}
        except:
            return {'exists': False, 'folder_id': None}
            
    except HTTPException:
        raise  
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check folder: {str(e)}")
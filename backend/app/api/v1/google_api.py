from __future__ import annotations

import os
import json
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from ...core.auth import get_current_user_supabase
from typing import Dict, Any
from ...services.google_oauth import google_oauth_service, GoogleTokens, GoogleAccount
from ...services.google_db import google_accounts_db


router = APIRouter()

FRONTEND_URL = os.getenv("FRONTEND_URL")


class GoogleAuthResponse(BaseModel):
    """Response model for Google auth operations."""

    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class GoogleCallbackRequest(BaseModel):
    """Request model for Google OAuth callback."""

    code: str
    state: Optional[str] = None


# Database storage now used instead of in-memory storage


@router.get("/auth/url", response_model=GoogleAuthResponse)
async def get_google_auth_url(
    add_account: bool = Query(
        False, description="Whether to add another account or replace primary"
    ),
    current_user: Dict[str, Any] = Depends(get_current_user_supabase),
):
    """Get Google OAuth authorization URL for new account or additional account."""
    try:
        user_id_str = str(current_user["id"])

        # Create state with user_id and action indicator
        state_data = f"{user_id_str}|{'add' if add_account else 'primary'}"

        auth_url = google_oauth_service.get_authorization_url(state=state_data)

        return GoogleAuthResponse(
            success=True,
            message="Authorization URL generated for "
            + ("additional account" if add_account else "primary account"),
            data={
                "auth_url": auth_url,
                "action": "add_account" if add_account else "set_primary",
            },
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate auth URL: {str(e)}"
        )


@router.get("/auth/callback")
async def handle_google_callback_get(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(None, description="State parameter"),
    error: str = Query(None, description="Error parameter if authentication failed"),
):
    """Handle Google OAuth callback GET request (redirect from Google)."""
    if error:
        # Redirect to frontend with error
        return RedirectResponse(
            url=f"{FRONTEND_URL}/google-callback.html?error={error}", status_code=302
        )

    if not code:
        # Redirect to frontend with error
        return RedirectResponse(
            url="{FRONTEND_URL}/google-callback.html?error=no_code", status_code=302
        )

    # Redirect to frontend callback handler with the code and state
    return RedirectResponse(
        url=f"{FRONTEND_URL}/google-callback.html?code={code}&state={state or ''}",
        status_code=302,
    )


@router.post("/auth/callback", response_model=GoogleAuthResponse)
async def handle_google_callback(
    request: GoogleCallbackRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_supabase),
):
    """Handle Google OAuth callback."""
    try:
        # Debug logging
        print(f"🔍 DEBUG - Callback received:")
        print(
            f"  - request.code: {request.code[:20]}..."
            if request.code
            else "  - request.code: None"
        )
        print(f"  - request.state: {request.state}")
        print(f"  - current_user id: {current_user.get('id')}")
        print(f"  - current_user: {current_user}")

        # Parse state to get user_id and action
        try:
            state_parts = request.state.split("|")
            state_user_id = state_parts[0]
            action = state_parts[1] if len(state_parts) > 1 else "primary"
        except:
            state_user_id = request.state  # Backward compatibility
            action = "primary"

        # Verify state matches current user
        current_user_id = str(current_user["id"])
        if state_user_id != current_user_id:
            print(f"❌ State mismatch: '{state_user_id}' != '{current_user_id}'")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid state parameter. Expected: {current_user_id}, Got: {state_user_id}",
            )

        print(f"✅ State validation passed: {state_user_id}, action: {action}")

        # Exchange code for tokens
        token_data = await google_oauth_service.exchange_code_for_tokens(
            request.code, request.state
        )

        if not token_data:
            raise HTTPException(
                status_code=400, detail="Failed to exchange code for tokens"
            )

        # Get user info
        user_info = token_data["user_info"]
        user_email = user_info.get("email", "")
        user_name = user_info.get("name", "")
        user_picture = user_info.get("picture", "")

        user_id_str = str(current_user["id"])

        # Get existing accounts to determine if this should be primary
        existing_accounts = await google_accounts_db.get_user_google_accounts(
            user_id_str
        )

        # Create Google account object
        import time

        google_account = GoogleAccount(
            email=user_email,
            name=user_name,
            picture=user_picture,
            tokens=GoogleTokens(
                access_token=token_data["access_token"],
                refresh_token=token_data["refresh_token"],
                expires_at=token_data["expires_in"],
            ),
            is_primary=(action == "primary" or len(existing_accounts) == 0),
            connected_at=time.time(),
        )

        # Save to database
        await google_accounts_db.save_google_account(user_id_str, google_account)

        # Get updated accounts list
        updated_accounts = await google_accounts_db.get_user_google_accounts(
            user_id_str
        )

        print(f"✅ Stored Google account {user_email} for user {user_id_str}")
        print(f"🔧 User now has {len(updated_accounts)} Google accounts")

        return GoogleAuthResponse(
            success=True,
            message=f"Google account {user_email} connected successfully",
            data={
                "user_info": user_info,
                "account_email": user_email,
                "is_primary": google_account.is_primary,
                "total_accounts": len(updated_accounts),
                "action": action,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")


@router.get("/auth/status", response_model=GoogleAuthResponse)
async def get_google_auth_status(
    current_user: Dict[str, Any] = Depends(get_current_user_supabase),
):
    """Check if user has valid Google tokens."""
    user_id_str = str(current_user["id"])

    # Get accounts from database
    accounts = await google_accounts_db.get_user_google_accounts(user_id_str)
    primary_account = await google_accounts_db.get_primary_account(user_id_str)

    return GoogleAuthResponse(
        success=True,
        message="Auth status retrieved",
        data={
            "has_tokens": len(accounts) > 0,
            "expires_at": (
                primary_account.tokens.expires_at if primary_account else None
            ),
            "accounts": [
                {
                    "email": acc.email,
                    "name": acc.name,
                    "nickname": acc.nickname,
                    "is_primary": acc.is_primary,
                    "connected_at": acc.connected_at,
                }
                for acc in accounts.values()
            ],
            "primary_account": primary_account.email if primary_account else None,
            "total_accounts": len(accounts),
        },
    )


async def get_user_google_credentials(user_id: str, account_email: str = None):
    """Get Google credentials for a user, optionally for a specific account."""
    print(f"🔍 Looking for tokens for user_id: '{user_id}', account: '{account_email}'")

    if account_email:
        # Specific account requested
        account = await google_accounts_db.get_account_by_email(user_id, account_email)
        if not account:
            raise HTTPException(
                status_code=404, detail=f"Google account {account_email} not found"
            )
        tokens = account.tokens
        print(f"✅ Found specific account {account_email}")
    else:
        # Use primary account
        primary_account = await google_accounts_db.get_primary_account(user_id)
        if not primary_account:
            print(f"❌ No Google accounts found for user {user_id}")
            raise HTTPException(
                status_code=401,
                detail="Google authentication required. Please connect your Google account in Settings.",
            )
        tokens = primary_account.tokens
        print(f"✅ Using primary account {primary_account.email}")

    return google_oauth_service.get_credentials_from_token(
        access_token=tokens.access_token, refresh_token=tokens.refresh_token
    )


# Gmail API endpoints
@router.get("/gmail/messages", response_model=Dict[str, Any])
async def get_gmail_messages(
    query: str = Query("", description="Gmail search query"),
    max_results: int = Query(
        10, ge=1, le=50, description="Maximum number of messages to return"
    ),
    current_user: Dict[str, Any] = Depends(get_current_user_supabase),
):
    """Get Gmail messages for the authenticated user."""
    try:
        credentials = await get_user_google_credentials(current_user["id"])
        messages = await google_oauth_service.get_gmail_messages(
            credentials=credentials, query=query, max_results=max_results
        )

        return messages

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get Gmail messages: {str(e)}"
        )


@router.get("/gmail/messages/{message_id}", response_model=Dict[str, Any])
async def get_gmail_message(
    message_id: str, current_user: Dict[str, Any] = Depends(get_current_user_supabase)
):
    """Get full content of a specific Gmail message."""
    try:
        credentials = await get_user_google_credentials(current_user["id"])
        message = await google_oauth_service.get_gmail_message_content(
            credentials=credentials, message_id=message_id
        )

        return message

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get Gmail message: {str(e)}"
        )


# Google Drive API endpoints
@router.get("/drive/files", response_model=Dict[str, Any])
async def get_drive_files(
    query: str = Query("", description="Drive search query"),
    max_results: int = Query(
        10, ge=1, le=50, description="Maximum number of files to return"
    ),
    current_user: Dict[str, Any] = Depends(get_current_user_supabase),
):
    """Get Google Drive files for the authenticated user."""
    try:
        credentials = await get_user_google_credentials(current_user["id"])
        files = await google_oauth_service.get_drive_files(
            credentials=credentials, query=query, max_results=max_results
        )

        return files

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get Drive files: {str(e)}"
        )


# Google Calendar API endpoints
@router.get("/calendar/events", response_model=Dict[str, Any])
async def get_calendar_events(
    calendar_id: str = Query("primary", description="Calendar ID"),
    max_results: int = Query(
        10, ge=1, le=50, description="Maximum number of events to return"
    ),
    current_user: Dict[str, Any] = Depends(get_current_user_supabase),
):
    """Get Google Calendar events for the authenticated user."""
    try:
        credentials = await get_user_google_credentials(current_user["id"])
        events = await google_oauth_service.get_calendar_events(
            credentials=credentials, calendar_id=calendar_id, max_results=max_results
        )

        return events

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get Calendar events: {str(e)}"
        )


@router.post("/auth/refresh", response_model=GoogleAuthResponse)
async def refresh_google_tokens(
    current_user: Dict[str, Any] = Depends(get_current_user_supabase),
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
            access_token=new_tokens["access_token"],
            refresh_token=new_tokens["refresh_token"] or tokens.refresh_token,
            expires_at=new_tokens["expires_in"],
        )

        return GoogleAuthResponse(success=True, message="Tokens refreshed successfully")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token refresh failed: {str(e)}")


# Advanced Drive Operations
@router.post("/drive/create-folder")
async def create_folder_structure(
    folder_path: str = Form(...),
    root_folder: str = Form("TURFMAPP"),
    current_user: Dict[str, Any] = Depends(get_current_user_supabase),
):
    """Create nested folder structure in user's Drive."""
    try:
        credentials = await get_user_google_credentials(current_user["id"])
        folder_id = await google_oauth_service.create_folder_structure(
            credentials, folder_path, root_folder
        )

        return {
            "success": True,
            "folder_id": folder_id,
            "folder_path": f"{root_folder}/{folder_path}",
            "message": "Folder structure created successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create folder structure: {str(e)}"
        )


@router.post("/drive/upload")
async def upload_file_to_drive(
    file: UploadFile = File(...),
    folder_path: Optional[str] = Form(None),
    current_user: Dict[str, Any] = Depends(get_current_user_supabase),
):
    """Upload file to specific folder in user's Drive."""
    try:
        credentials = await get_user_google_credentials(current_user["id"])

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
    file_id: str, current_user: Dict[str, Any] = Depends(get_current_user_supabase)
):
    """Delete file from user's Drive."""
    try:
        credentials = await get_user_google_credentials(current_user["id"])
        result = await google_oauth_service.delete_file_from_drive(credentials, file_id)

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


@router.get("/drive/folder/{folder_path:path}/files")
async def list_files_in_folder(
    folder_path: str, current_user: Dict[str, Any] = Depends(get_current_user_supabase)
):
    """List files in specific folder path."""
    try:
        credentials = await get_user_google_credentials(current_user["id"])
        result = await google_oauth_service.list_files_in_folder(
            credentials, folder_path
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.get("/drive/folder-exists/{folder_path:path}")
async def check_folder_exists(
    folder_path: str, current_user: Dict[str, Any] = Depends(get_current_user_supabase)
):
    """Check if folder path exists in user's Drive."""
    try:
        credentials = await get_user_google_credentials(current_user["id"])
        # Create a basic exists check by trying to find the folder
        try:
            folder_id = await google_oauth_service.create_folder_structure(
                credentials, folder_path
            )
            return {"exists": bool(folder_id), "folder_id": folder_id}
        except:
            return {"exists": False, "folder_id": None}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check folder: {str(e)}")


# Multi-Account Management Endpoints


@router.get("/accounts", response_model=GoogleAuthResponse)
async def list_google_accounts(
    current_user: Dict[str, Any] = Depends(get_current_user_supabase),
):
    """List all connected Google accounts for the user."""
    user_id_str = str(current_user["id"])
    accounts = await google_accounts_db.get_user_google_accounts(user_id_str)

    return GoogleAuthResponse(
        success=True,
        message=f"Found {len(accounts)} connected accounts",
        data={
            "accounts": [
                {
                    "email": acc.email,
                    "name": acc.name,
                    "picture": acc.picture,
                    "nickname": acc.nickname,
                    "is_primary": acc.is_primary,
                    "connected_at": acc.connected_at,
                }
                for acc in accounts.values()
            ],
            "total_accounts": len(accounts),
        },
    )


@router.post("/accounts/{account_email}/set-primary", response_model=GoogleAuthResponse)
async def set_primary_account(
    account_email: str,
    current_user: Dict[str, Any] = Depends(get_current_user_supabase),
):
    """Set a specific account as the primary account."""
    user_id_str = str(current_user["id"])

    # Set primary account in database
    success = await google_accounts_db.set_primary_account(user_id_str, account_email)

    if not success:
        raise HTTPException(
            status_code=404, detail=f"Account {account_email} not found"
        )

    return GoogleAuthResponse(
        success=True,
        message=f"Account {account_email} set as primary",
        data={"primary_account": account_email},
    )


@router.put("/accounts/{account_email}/nickname", response_model=GoogleAuthResponse)
async def set_account_nickname(
    account_email: str,
    nickname: str = Form(...),
    current_user: Dict[str, Any] = Depends(get_current_user_supabase),
):
    """Set a nickname/label for a Google account."""
    user_id_str = str(current_user["id"])

    # Update nickname in database
    success = await google_accounts_db.update_account_nickname(
        user_id_str, account_email, nickname
    )

    if not success:
        raise HTTPException(
            status_code=404, detail=f"Account {account_email} not found"
        )

    return GoogleAuthResponse(
        success=True,
        message=f"Nickname '{nickname}' set for {account_email}",
        data={"account": account_email, "nickname": nickname},
    )


@router.delete("/accounts/{account_email}", response_model=GoogleAuthResponse)
async def disconnect_google_account(
    account_email: str,
    current_user: Dict[str, Any] = Depends(get_current_user_supabase),
):
    """Disconnect a specific Google account."""
    user_id_str = str(current_user["id"])

    # Delete account from database
    success = await google_accounts_db.delete_google_account(user_id_str, account_email)

    if not success:
        raise HTTPException(
            status_code=404, detail=f"Account {account_email} not found"
        )

    # Get remaining accounts to see if we need to set a new primary
    remaining_accounts = await google_accounts_db.get_user_google_accounts(user_id_str)

    return GoogleAuthResponse(
        success=True,
        message=f"Account {account_email} disconnected",
        data={
            "disconnected_account": account_email,
            "remaining_accounts": len(remaining_accounts),
        },
    )

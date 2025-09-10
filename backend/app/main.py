from __future__ import annotations

import os
from typing import List

from dotenv import load_dotenv

# Load environment variables FIRST, before any other imports
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# New modular API structure
from .api.v1.chat import router as chat_router_v1
from .api.v1.preferences import router as preferences_router_v1
from .api.v1.auth import router as auth_router_v1
from .api.v1.upload import router as upload_router
from .api.v1.fal_tools import router as fal_tools_router
from .api.v1.admin import router as admin_router_v1
from .api.v1.settings import router as settings_router_v1
from .api.v1.google_api import router as google_api_router_v1

from .database import get_supabase_config


def _get_cors_origins() -> List[str]:
    origins_env = os.getenv("BACKEND_CORS_ORIGINS", "")
    if origins_env:
        return [origin.strip() for origin in origins_env.split(",") if origin.strip()]
    
    # Default CORS origins
    return ["http://localhost:3005", "http://localhost:3000"]

app = FastAPI(
    title="TURFMAPP AI Agent Backend",
    description="Modular AI chatbot backend with Supabase integration",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "TURFMAPP AI Agent Backend",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/healthz")
def health_check() -> dict:
    """Health check endpoint"""
    return {"status": "ok"}


# API v1 routes
app.include_router(chat_router_v1, prefix="/api/v1/chat", tags=["chat"])
app.include_router(preferences_router_v1, prefix="/api/v1/preferences", tags=["preferences"])
app.include_router(auth_router_v1, prefix="/api/v1/auth", tags=["auth"])

# Additional v1 routes
app.include_router(upload_router, prefix="/api/v1/uploads", tags=["uploads"])
app.include_router(fal_tools_router, prefix="/api/v1/fal-tools", tags=["fal-tools"])
app.include_router(admin_router_v1, prefix="/api/v1/admin", tags=["admin"])
app.include_router(settings_router_v1, prefix="/api/v1/settings", tags=["settings"])
app.include_router(google_api_router_v1, prefix="/api/v1/google", tags=["google-api"])

# Direct Google OAuth callback route for frontend redirect
app.include_router(google_api_router_v1, prefix="/auth/google", tags=["google-oauth"])


@app.on_event("startup")
def on_startup() -> None:
    """Initialize application on startup"""
    # Supabase integration - configuration loaded
    config = get_supabase_config()
    print(f"Supabase configured: {bool(config['url'])}")



from __future__ import annotations

import os
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .routes.auth import router as auth_router
from .routes.admin import router as admin_router
from .routes.chat import router as chat_router
from .routes.upload import router as upload_router
from .routes.fal_tools import router as fal_tools_router
from .database import Base, engine


def _get_cors_origins() -> List[str]:
    origins_env = os.getenv("BACKEND_CORS_ORIGINS", "")
    if not origins_env:
        return []
    return [origin.strip() for origin in origins_env.split(",") if origin.strip()]


load_dotenv()

app = FastAPI(title="TurfMapp AI Agent Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def health_check() -> dict:
    """Simple health endpoint for readiness probes."""
    return {"status": "ok"}


app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(admin_router, prefix="/admin", tags=["admin"])
app.include_router(chat_router, prefix="/chat", tags=["chat"])
app.include_router(upload_router, prefix="/uploads", tags=["uploads"])
app.include_router(fal_tools_router, prefix="/fal-tools", tags=["fal-tools"])


@app.on_event("startup")
def on_startup() -> None:
    # Create tables if they do not exist
    Base.metadata.create_all(bind=engine)



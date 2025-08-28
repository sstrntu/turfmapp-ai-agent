from __future__ import annotations

import os
from typing import Optional

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings


class Settings(BaseSettings):
    # Database - Supabase Required
    supabase_url: str = os.getenv("SUPABASE_URL")
    supabase_anon_key: str = os.getenv("SUPABASE_ANON_KEY") 
    supabase_service_role_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    supabase_db_url: str = os.getenv("SUPABASE_DB_URL")
    
    # OpenAI
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    # App settings
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS
    allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3005",
        "http://localhost:5173",
        "http://localhost:8080",
    ]
    
    class Config:
        case_sensitive = False


# Global settings instance
settings = Settings()
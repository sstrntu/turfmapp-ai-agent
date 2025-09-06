from __future__ import annotations

import os
from typing import Optional

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings


class Settings(BaseSettings):
    # Database - Supabase Required
    supabase_url: str = os.getenv("SUPABASE_URL", "https://example.supabase.co")
    supabase_anon_key: str = os.getenv("SUPABASE_ANON_KEY", "test-anon-key") 
    supabase_service_role_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
    supabase_db_url: str = os.getenv("SUPABASE_DB_URL", "postgresql://test:test@localhost:5432/test")
    
    # Database URL property for compatibility
    @property
    def database_url(self) -> str:
        """Return the database URL for asyncpg connections."""
        return self.supabase_db_url
    
    # OpenAI
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    
    # App settings
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Encryption
    encryption_key: Optional[str] = os.getenv("ENCRYPTION_KEY")
    
    # Google OAuth
    google_client_id: Optional[str] = os.getenv("GOOGLE_CLIENT_ID")
    google_client_secret: Optional[str] = os.getenv("GOOGLE_CLIENT_SECRET")
    google_redirect_uri: Optional[str] = os.getenv("GOOGLE_REDIRECT_URI")
    
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


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings
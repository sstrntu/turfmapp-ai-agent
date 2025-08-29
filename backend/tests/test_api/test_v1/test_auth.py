"""
Test Auth API Endpoints

Tests for app.api.v1.auth module following code.md standards.
Comprehensive coverage for authentication endpoints.
"""

from __future__ import annotations

import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any
from fastapi.testclient import TestClient
from fastapi import status


class TestAuthEndpoints:
    """Test authentication API endpoints."""

    def test_exchange_tokens_success(
        self, 
        client: TestClient, 
        mock_env_vars: Dict[str, str]
    ) -> None:
        """Test successful token exchange.
        
        Args:
            client: FastAPI test client
            mock_env_vars: Mock environment variables
        """
        payload = {
            "access_token": "valid-access-token",
            "refresh_token": "valid-refresh-token",
            "state": "test-state"
        }
        
        mock_user_response = {
            "id": "test-user-id",
            "email": "test@example.com",
            "user_metadata": {
                "full_name": "Test User",
                "avatar_url": "https://example.com/avatar.jpg"
            }
        }
        
        from app.models.auth import PublicUser
        mock_user = PublicUser(
            id="test-user-id",
            email="test@example.com",
            name="Test User",
            avatar_url="https://example.com/avatar.jpg"
        )
        
        with patch("app.api.v1.auth.fetch_user_with_access_token", return_value=mock_user):
            response = client.post("/api/v1/auth/exchange", json=payload)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "test-user-id"
        assert data["email"] == "test@example.com"
        assert data["name"] == "Test User"
        assert data["avatar_url"] == "https://example.com/avatar.jpg"

    def test_exchange_tokens_invalid_token(
        self,
        client: TestClient,
        mock_env_vars: Dict[str, str]
    ) -> None:
        """Test token exchange with invalid token.
        
        Args:
            client: FastAPI test client
            mock_env_vars: Mock environment variables
        """
        payload = {
            "access_token": "invalid-token",
            "refresh_token": "invalid-refresh-token",
            "state": "test-state"
        }
        
        with patch("app.api.v1.auth.fetch_user_with_access_token", return_value=None):
            response = client.post("/api/v1/auth/exchange", json=payload)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid access token" in response.json()["detail"]

    def test_exchange_tokens_missing_token(
        self,
        client: TestClient
    ) -> None:
        """Test token exchange with missing access token.
        
        Args:
            client: FastAPI test client
        """
        payload = {
            "refresh_token": "some-refresh-token"
        }
        
        response = client.post("/api/v1/auth/exchange", json=payload)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_exchange_tokens_malformed_payload(
        self,
        client: TestClient
    ) -> None:
        """Test token exchange with malformed payload.
        
        Args:
            client: FastAPI test client
        """
        payload = {
            "not_access_token": "some-token"
        }
        
        response = client.post("/api/v1/auth/exchange", json=payload)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_exchange_tokens_empty_payload(
        self,
        client: TestClient
    ) -> None:
        """Test token exchange with empty payload.
        
        Args:
            client: FastAPI test client
        """
        response = client.post("/api/v1/auth/exchange", json={})
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_exchange_tokens_supabase_error(
        self,
        client: TestClient,
        mock_env_vars: Dict[str, str]
    ) -> None:
        """Test token exchange with Supabase service error.
        
        Args:
            client: FastAPI test client
            mock_env_vars: Mock environment variables
        """
        payload = {
            "access_token": "valid-token",
            "refresh_token": "valid-refresh-token"
        }
        
        with patch("app.api.v1.auth.fetch_user_with_access_token", side_effect=Exception("Supabase error")):
            response = client.post("/api/v1/auth/exchange", json=payload)
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_exchange_tokens_minimal_user_data(
        self,
        client: TestClient,
        mock_env_vars: Dict[str, str]
    ) -> None:
        """Test token exchange with minimal user data from Supabase.
        
        Args:
            client: FastAPI test client
            mock_env_vars: Mock environment variables
        """
        payload = {
            "access_token": "valid-access-token",
            "refresh_token": "valid-refresh-token"
        }
        
        mock_user_response = {
            "id": "test-user-id",
            "email": "test@example.com"
            # No user_metadata
        }
        
        with patch("app.api.v1.auth.fetch_user_with_access_token", return_value=mock_user_response):
            response = client.post("/api/v1/auth/exchange", json=payload)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "test-user-id"
        assert data["email"] == "test@example.com"
        assert data["name"] is None
        assert data["avatar_url"] is None

    def test_get_authenticated_user_success(
        self,
        client: TestClient,
        mock_auth_header: Dict[str, str],
        mock_env_vars: Dict[str, str]
    ) -> None:
        """Test getting authenticated user successfully.
        
        Args:
            client: FastAPI test client
            mock_auth_header: Mock authorization header
            mock_env_vars: Mock environment variables
        """
        mock_user_response = {
            "id": "test-user-id",
            "email": "test@example.com",
            "user_metadata": {
                "full_name": "Test User"
            }
        }
        
        with patch("app.api.v1.auth.fetch_user_with_access_token", return_value=mock_user_response):
            response = client.get("/api/v1/auth/user", headers=mock_auth_header)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "test-user-id"
        assert data["email"] == "test@example.com"

    def test_get_authenticated_user_no_token(
        self,
        client: TestClient
    ) -> None:
        """Test getting authenticated user without token.
        
        Args:
            client: FastAPI test client
        """
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_authenticated_user_invalid_header(
        self,
        client: TestClient
    ) -> None:
        """Test getting authenticated user with invalid authorization header.
        
        Args:
            client: FastAPI test client
        """
        headers = {"Authorization": "InvalidHeader token"}
        response = client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_authenticated_user_invalid_token(
        self,
        client: TestClient,
        mock_env_vars: Dict[str, str]
    ) -> None:
        """Test getting authenticated user with invalid token.
        
        Args:
            client: FastAPI test client
            mock_env_vars: Mock environment variables
        """
        headers = {"Authorization": "Bearer invalid-token"}
        
        with patch("app.api.v1.auth.fetch_user_with_access_token", return_value=None):
            response = client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid access token" in response.json()["detail"]


class TestAuthUtilityFunctions:
    """Test auth utility functions and edge cases."""

    def test_auth_endpoint_routes_exist(self, client: TestClient) -> None:
        """Test that auth endpoints are properly registered.
        
        Args:
            client: FastAPI test client
        """
        # Test that endpoints exist (will return appropriate errors without auth)
        response = client.post("/api/v1/auth/exchange", json={})
        assert response.status_code != status.HTTP_404_NOT_FOUND
        
        response = client.get("/api/v1/auth/me")
        assert response.status_code != status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_fetch_user_network_timeout(self) -> None:
        """Test fetch user with network timeout."""
        from app.api.v1.auth import fetch_user_with_access_token
        
        with patch("httpx.AsyncClient") as mock_httpx:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Timeout")
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_httpx.return_value = mock_client
            
            result = await fetch_user_with_access_token("test-token")
            assert result is None

    @pytest.mark.asyncio
    async def test_fetch_user_http_error(self) -> None:
        """Test fetch user with HTTP error."""
        from app.api.v1.auth import fetch_user_with_access_token
        
        with patch("httpx.AsyncClient") as mock_httpx:
            mock_response = Mock()
            mock_response.status_code = 500
            
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_httpx.return_value = mock_client
            
            result = await fetch_user_with_access_token("test-token")
            assert result is None
"""
Test Session Utilities

Tests for app.utils.sessions module following code.md standards.
Comprehensive coverage for session management utilities.
"""

from __future__ import annotations

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any
from itsdangerous import URLSafeSerializer, BadSignature
from fastapi import Request, Response


class TestSessionUtilities:
    """Test session management utility functions."""

    def test_get_serializer_default_secret(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test getting serializer with default secret key.
        
        Args:
            monkeypatch: pytest fixture for environment variables
        """
        from app.utils.sessions import _get_serializer
        
        monkeypatch.setenv("SESSION_SECRET", "test-secret-key")
        
        serializer = _get_serializer()
        
        assert isinstance(serializer, URLSafeSerializer)
        assert serializer.secret_key == b"test-secret-key"

    def test_get_serializer_custom_secret(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test getting serializer with custom secret key.
        
        Args:
            monkeypatch: pytest fixture for environment variables
        """
        from app.utils.sessions import _get_serializer
        
        monkeypatch.setenv("SESSION_SECRET", "custom-secret-key")
        
        serializer = _get_serializer()
        
        assert serializer.secret_key == b"custom-secret-key"

    def test_get_serializer_no_secret_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test getting serializer when no secret key is set.
        
        Args:
            monkeypatch: pytest fixture for environment variables
        """
        from app.utils.sessions import _get_serializer
        
        monkeypatch.delenv("SESSION_SECRET", raising=False)
        
        serializer = _get_serializer()
        
        # Should use default fallback (secret_key is bytes in production)
        assert serializer.secret_key in [b"dev-secret-please-change", "dev-secret-please-change"]

    def test_set_state_cookie(self) -> None:
        """Test setting state cookie on response."""
        from app.utils.sessions import set_state_cookie
        
        mock_response = Mock(spec=Response)
        state = "test-state-value"
        
        set_state_cookie(mock_response, state)
        
        mock_response.set_cookie.assert_called_once_with(
            key="tm_oauth_state",
            value=state,
            httponly=True,
            secure=False,
            samesite="lax",
            path="/",
            max_age=600
        )

    def test_get_state_from_cookie_exists(self) -> None:
        """Test getting state from cookie when it exists."""
        from app.utils.sessions import get_state_from_cookie
        
        mock_request = Mock(spec=Request)
        mock_request.cookies = {"tm_oauth_state": "test-state-value"}
        
        state = get_state_from_cookie(mock_request)
        
        assert state == "test-state-value"

    def test_get_state_from_cookie_missing(self) -> None:
        """Test getting state from cookie when it doesn't exist."""
        from app.utils.sessions import get_state_from_cookie
        
        mock_request = Mock(spec=Request)
        mock_request.cookies = {}
        
        state = get_state_from_cookie(mock_request)
        
        assert state is None

    def test_set_session_cookie(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test setting session cookie with serialized data.
        
        Args:
            monkeypatch: pytest fixture for environment variables
        """
        from app.utils.sessions import set_session_cookie
        
        monkeypatch.setenv("SESSION_SECRET", "test-secret")
        
        mock_response = Mock(spec=Response)
        session_data = {"user_id": "123", "email": "test@example.com"}
        
        set_session_cookie(mock_response, session_data)
        
        # Verify set_cookie was called
        assert mock_response.set_cookie.called
        call_args = mock_response.set_cookie.call_args
        
        assert call_args[1]["key"] == "tm_session"
        assert call_args[1]["httponly"] is True
        assert call_args[1]["secure"] is False
        assert call_args[1]["samesite"] == "lax"
        assert call_args[1]["path"] == "/"
        assert "expires" in call_args[1]  # Has expiration date

    def test_clear_session_cookie(self) -> None:
        """Test clearing session cookie."""
        from app.utils.sessions import clear_session_cookie
        
        mock_response = Mock(spec=Response)
        
        clear_session_cookie(mock_response)
        
        # Should delete both session and state cookies
        assert mock_response.delete_cookie.call_count == 2
        calls = mock_response.delete_cookie.call_args_list
        
        # Check that tm_session and tm_oauth_state are deleted
        deleted_keys = [call[0][0] for call in calls]  # First positional arg of each call
        assert "tm_session" in deleted_keys
        assert "tm_oauth_state" in deleted_keys

    def test_get_session_from_request_valid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test getting valid session from request.
        
        Args:
            monkeypatch: pytest fixture for environment variables
        """
        from app.utils.sessions import get_session_from_request, _get_serializer
        
        monkeypatch.setenv("SESSION_SECRET", "test-secret")
        
        # Create valid session token
        session_data = {"user_id": "123", "email": "test@example.com"}
        serializer = _get_serializer()
        session_token = serializer.dumps(session_data)
        
        mock_request = Mock(spec=Request)
        mock_request.cookies = {"tm_session": session_token}
        
        result = get_session_from_request(mock_request)
        
        assert result == session_data

    def test_get_session_from_request_missing_token(self) -> None:
        """Test getting session from request with missing token."""
        from app.utils.sessions import get_session_from_request
        
        mock_request = Mock(spec=Request)
        mock_request.cookies = {}
        
        result = get_session_from_request(mock_request)
        
        assert result is None

    def test_get_session_from_request_invalid_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test getting session from request with invalid token.
        
        Args:
            monkeypatch: pytest fixture for environment variables
        """
        from app.utils.sessions import get_session_from_request
        
        monkeypatch.setenv("SESSION_SECRET", "test-secret")
        
        mock_request = Mock(spec=Request)
        mock_request.cookies = {"tm_session": "invalid-token"}
        
        result = get_session_from_request(mock_request)
        
        assert result is None

    def test_get_session_from_request_non_dict_session(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test getting session from request when session is not a dictionary.
        
        Args:
            monkeypatch: pytest fixture for environment variables
        """
        from app.utils.sessions import get_session_from_request, _get_serializer
        
        monkeypatch.setenv("SESSION_SECRET", "test-secret")
        
        # Create token with non-dict data
        serializer = _get_serializer()
        session_token = serializer.dumps("not-a-dict")
        
        mock_request = Mock(spec=Request)
        mock_request.cookies = {"tm_session": session_token}
        
        result = get_session_from_request(mock_request)
        
        assert result is None

    def test_get_session_from_request_serializer_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test getting session from request with serializer error.
        
        Args:
            monkeypatch: pytest fixture for environment variables
        """
        from app.utils.sessions import get_session_from_request
        
        monkeypatch.setenv("SESSION_SECRET", "test-secret")
        
        mock_request = Mock(spec=Request)
        mock_request.cookies = {"tm_session": "corrupted-token"}
        
        with patch("app.utils.sessions._get_serializer") as mock__get_serializer:
            mock_serializer = Mock()
            mock_serializer.loads.side_effect = BadSignature("Bad signature")
            mock__get_serializer.return_value = mock_serializer
            
            result = get_session_from_request(mock_request)
        
        assert result is None


class TestSessionSecurityFeatures:
    """Test session security features and edge cases."""

    def test_session_cookie_security_attributes(self) -> None:
        """Test that session cookies have proper security attributes."""
        from app.utils.sessions import set_session_cookie
        
        mock_response = Mock(spec=Response)
        session_data = {"user_id": "123"}
        
        set_session_cookie(mock_response, session_data)
        
        call_args = mock_response.set_cookie.call_args
        
        # Verify security attributes
        assert call_args[1]["httponly"] is True  # Prevents XSS
        assert call_args[1]["secure"] is False   # Not HTTPS in test environment
        assert call_args[1]["samesite"] == "lax" # CSRF protection

    def test_state_cookie_security_attributes(self) -> None:
        """Test that state cookies have proper security attributes."""
        from app.utils.sessions import set_state_cookie
        
        mock_response = Mock(spec=Response)
        state = "test-state"
        
        set_state_cookie(mock_response, state)
        
        call_args = mock_response.set_cookie.call_args
        
        # Verify security attributes
        assert call_args[1]["httponly"] is True  # Prevents XSS
        assert call_args[1]["secure"] is False   # Not HTTPS in test environment
        assert call_args[1]["samesite"] == "lax" # CSRF protection
        assert call_args[1]["max_age"] == 600    # 10 minute expiry

    def test_serializer_consistency(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that serializer is consistent across calls.
        
        Args:
            monkeypatch: pytest fixture for environment variables
        """
        from app.utils.sessions import _get_serializer
        
        monkeypatch.setenv("SESSION_SECRET", "consistent-secret")
        
        serializer1 = _get_serializer()
        serializer2 = _get_serializer()
        
        # Should use same secret key
        assert serializer1.secret_key == serializer2.secret_key
        
        # Should be able to serialize/deserialize consistently
        test_data = {"test": "data"}
        token = serializer1.dumps(test_data)
        decoded = serializer2.loads(token)
        
        assert decoded == test_data

    def test_session_data_serialization_types(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test session data serialization with various data types.
        
        Args:
            monkeypatch: pytest fixture for environment variables
        """
        from app.utils.sessions import set_session_cookie, get_session_from_request, _get_serializer
        
        monkeypatch.setenv("SESSION_SECRET", "test-secret")
        
        complex_data = {
            "user_id": "123",
            "email": "test@example.com",
            "roles": ["user", "admin"],
            "preferences": {
                "theme": "dark",
                "notifications": True
            },
            "login_count": 5,
            "last_login": None
        }
        
        # Serialize
        mock_response = Mock(spec=Response)
        set_session_cookie(mock_response, complex_data)
        
        # Get the token that was set
        call_args = mock_response.set_cookie.call_args
        session_token = call_args[1]["value"]
        
        # Deserialize
        mock_request = Mock(spec=Request)
        mock_request.cookies = {"tm_session": session_token}
        
        result = get_session_from_request(mock_request)
        
        assert result == complex_data

    def test_empty_session_data(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test handling of empty session data.
        
        Args:
            monkeypatch: pytest fixture for environment variables
        """
        from app.utils.sessions import set_session_cookie, get_session_from_request
        
        monkeypatch.setenv("SESSION_SECRET", "test-secret")
        
        empty_data = {}
        
        # Serialize empty data
        mock_response = Mock(spec=Response)
        set_session_cookie(mock_response, empty_data)
        
        # Get the token that was set
        call_args = mock_response.set_cookie.call_args
        session_token = call_args[1]["value"]
        
        # Deserialize
        mock_request = Mock(spec=Request)
        mock_request.cookies = {"tm_session": session_token}
        
        result = get_session_from_request(mock_request)
        
        assert result == empty_data
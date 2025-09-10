"""
Comprehensive tests for google_oauth.py - Google OAuth and API service
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import base64
import json
from datetime import datetime, timezone
from typing import Dict, Any

# Import the service to test
from app.services.google_oauth import (
    GoogleOAuthService,
    GoogleTokens,
    GoogleAccount,
    google_oauth_service
)


class TestGoogleTokensModel:
    """Test suite for GoogleTokens model"""

    def test_google_tokens_creation(self):
        """Test GoogleTokens model creation"""
        tokens = GoogleTokens(
            access_token="access123",
            refresh_token="refresh123",
            expires_at=1640995200.0
        )
        
        assert tokens.access_token == "access123"
        assert tokens.refresh_token == "refresh123"
        assert tokens.expires_at == 1640995200.0

    def test_google_tokens_optional_fields(self):
        """Test GoogleTokens with optional fields"""
        tokens = GoogleTokens(access_token="access123")
        
        assert tokens.access_token == "access123"
        assert tokens.refresh_token is None
        assert tokens.expires_at is None


class TestGoogleAccountModel:
    """Test suite for GoogleAccount model"""

    def test_google_account_creation(self):
        """Test GoogleAccount model creation"""
        tokens = GoogleTokens(access_token="access123")
        account = GoogleAccount(
            email="test@example.com",
            name="Test User",
            picture="https://example.com/pic.jpg",
            tokens=tokens,
            nickname="Work",
            is_primary=True,
            connected_at=1640995200.0
        )
        
        assert account.email == "test@example.com"
        assert account.name == "Test User"
        assert account.picture == "https://example.com/pic.jpg"
        assert account.tokens == tokens
        assert account.nickname == "Work"
        assert account.is_primary is True
        assert account.connected_at == 1640995200.0

    def test_google_account_optional_fields(self):
        """Test GoogleAccount with optional fields"""
        tokens = GoogleTokens(access_token="access123")
        account = GoogleAccount(
            email="test@example.com",
            name="Test User",
            tokens=tokens,
            connected_at=1640995200.0
        )
        
        assert account.picture is None
        assert account.nickname is None
        assert account.is_primary is False


class TestGoogleOAuthServiceInitialization:
    """Test suite for GoogleOAuthService initialization"""

    def test_service_initialization(self):
        """Test GoogleOAuthService initialization"""
        with patch.dict('os.environ', {
            'GOOGLE_CLIENT_ID': 'test_client_id',
            'GOOGLE_CLIENT_SECRET': 'test_client_secret',
            'GOOGLE_REDIRECT_URI': 'http://localhost:8000/callback'
        }):
            service = GoogleOAuthService()
            
            assert service.client_id == 'test_client_id'
            assert service.client_secret == 'test_client_secret'
            assert service.redirect_uri == 'http://localhost:8000/callback'

    def test_service_initialization_with_defaults(self):
        """Test GoogleOAuthService initialization with default redirect URI"""
        with patch.dict('os.environ', {
            'GOOGLE_CLIENT_ID': 'test_client_id',
            'GOOGLE_CLIENT_SECRET': 'test_client_secret'
        }, clear=True):
            service = GoogleOAuthService()
            
            assert service.redirect_uri == "http://localhost:8000/auth/google/auth/callback"

    def test_scopes_configuration(self):
        """Test that required scopes are properly configured"""
        service = GoogleOAuthService()
        
        expected_scopes = [
            'openid',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile', 
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/drive.readonly', 
            'https://www.googleapis.com/auth/calendar.readonly'
        ]
        
        assert service.scopes == expected_scopes

    def test_global_instance_exists(self):
        """Test that global google_oauth_service instance exists"""
        assert google_oauth_service is not None
        assert isinstance(google_oauth_service, GoogleOAuthService)


class TestConfiguration:
    """Test suite for configuration validation"""

    @pytest.fixture
    def mock_service(self):
        with patch.dict('os.environ', {
            'GOOGLE_CLIENT_ID': 'test_client_id',
            'GOOGLE_CLIENT_SECRET': 'test_client_secret'
        }):
            return GoogleOAuthService()

    def test_ensure_configured_success(self, mock_service):
        """Test _ensure_configured when properly configured"""
        # Should not raise any exception
        mock_service._ensure_configured()

    def test_ensure_configured_missing_client_id(self):
        """Test _ensure_configured when client_id is missing"""
        with patch.dict('os.environ', {'GOOGLE_CLIENT_SECRET': 'test_secret'}, clear=True):
            service = GoogleOAuthService()
            
            with pytest.raises(ValueError, match="Google OAuth credentials not configured"):
                service._ensure_configured()

    def test_ensure_configured_missing_client_secret(self):
        """Test _ensure_configured when client_secret is missing"""
        with patch.dict('os.environ', {'GOOGLE_CLIENT_ID': 'test_client_id'}, clear=True):
            service = GoogleOAuthService()
            
            with pytest.raises(ValueError, match="Google OAuth credentials not configured"):
                service._ensure_configured()

    def test_ensure_configured_empty_credentials(self):
        """Test _ensure_configured when credentials are empty strings"""
        with patch.dict('os.environ', {
            'GOOGLE_CLIENT_ID': '',
            'GOOGLE_CLIENT_SECRET': ''
        }):
            service = GoogleOAuthService()
            
            with pytest.raises(ValueError, match="Google OAuth credentials not configured"):
                service._ensure_configured()


class TestAuthorizationURL:
    """Test suite for get_authorization_url method"""

    @pytest.fixture
    def mock_service(self):
        with patch.dict('os.environ', {
            'GOOGLE_CLIENT_ID': 'test_client_id',
            'GOOGLE_CLIENT_SECRET': 'test_client_secret'
        }):
            return GoogleOAuthService()

    def test_get_authorization_url_success(self, mock_service):
        """Test get_authorization_url generates proper URL"""
        mock_flow = Mock()
        mock_flow.authorization_url.return_value = ("https://accounts.google.com/oauth/authorize?client_id=test", "state")
        
        with patch('app.services.google_oauth.Flow') as mock_flow_class:
            mock_flow_class.from_client_config.return_value = mock_flow
            
            url = mock_service.get_authorization_url("test_state")
            
            assert url == "https://accounts.google.com/oauth/authorize?client_id=test"
            mock_flow.authorization_url.assert_called_once_with(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent',
                state='test_state'
            )

    def test_get_authorization_url_without_state(self, mock_service):
        """Test get_authorization_url without state parameter"""
        mock_flow = Mock()
        mock_flow.authorization_url.return_value = ("https://accounts.google.com/oauth/authorize", "state")
        
        with patch('app.services.google_oauth.Flow') as mock_flow_class:
            mock_flow_class.from_client_config.return_value = mock_flow
            
            url = mock_service.get_authorization_url()
            
            assert url == "https://accounts.google.com/oauth/authorize"
            mock_flow.authorization_url.assert_called_once_with(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent',
                state=None
            )

    def test_get_authorization_url_not_configured(self):
        """Test get_authorization_url when not configured"""
        service = GoogleOAuthService()  # No environment variables set
        
        with pytest.raises(ValueError, match="Google OAuth credentials not configured"):
            service.get_authorization_url()

    def test_get_authorization_url_flow_configuration(self, mock_service):
        """Test that Flow is configured with correct parameters"""
        mock_flow = Mock()
        mock_flow.authorization_url.return_value = ("https://test.url", "state")
        
        with patch('app.services.google_oauth.Flow') as mock_flow_class:
            mock_flow_class.from_client_config.return_value = mock_flow
            
            mock_service.get_authorization_url()
            
            # Check Flow configuration
            expected_config = {
                "web": {
                    "client_id": "test_client_id",
                    "client_secret": "test_client_secret",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [mock_service.redirect_uri]
                }
            }
            
            mock_flow_class.from_client_config.assert_called_once_with(
                expected_config,
                scopes=mock_service.scopes
            )


class TestTokenExchange:
    """Test suite for exchange_code_for_tokens method"""

    @pytest.fixture
    def mock_service(self):
        with patch.dict('os.environ', {
            'GOOGLE_CLIENT_ID': 'test_client_id',
            'GOOGLE_CLIENT_SECRET': 'test_client_secret'
        }):
            return GoogleOAuthService()

    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens_success(self, mock_service):
        """Test successful token exchange"""
        # Mock credentials
        mock_credentials = Mock()
        mock_credentials.token = "access_token_123"
        mock_credentials.refresh_token = "refresh_token_123"
        mock_credentials.expiry = Mock()
        mock_credentials.expiry.timestamp.return_value = 1640995200.0
        mock_credentials.to_json.return_value = '{"token": "access_token_123"}'
        
        # Mock flow
        mock_flow = Mock()
        mock_flow.credentials = mock_credentials
        
        # Mock user info
        mock_user_info = {
            'id': 'user123',
            'email': 'test@example.com',
            'name': 'Test User',
            'picture': 'https://example.com/pic.jpg'
        }
        
        with patch('app.services.google_oauth.Flow') as mock_flow_class, \
             patch.object(mock_service, '_get_user_info', new_callable=AsyncMock, return_value=mock_user_info):
            
            mock_flow_class.from_client_config.return_value = mock_flow
            
            result = await mock_service.exchange_code_for_tokens("auth_code_123", "test_state")
            
            assert result is not None
            assert result['access_token'] == "access_token_123"
            assert result['refresh_token'] == "refresh_token_123"
            assert result['expires_in'] == 1640995200.0
            assert result['user_info'] == mock_user_info
            assert result['credentials'] == '{"token": "access_token_123"}'
            
            mock_flow.fetch_token.assert_called_once_with(code="auth_code_123")

    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens_without_expiry(self, mock_service):
        """Test token exchange when credentials have no expiry"""
        mock_credentials = Mock()
        mock_credentials.token = "access_token_123"
        mock_credentials.refresh_token = "refresh_token_123"
        mock_credentials.expiry = None
        mock_credentials.to_json.return_value = '{"token": "access_token_123"}'
        
        mock_flow = Mock()
        mock_flow.credentials = mock_credentials
        
        with patch('app.services.google_oauth.Flow') as mock_flow_class, \
             patch.object(mock_service, '_get_user_info', new_callable=AsyncMock, return_value={}):
            
            mock_flow_class.from_client_config.return_value = mock_flow
            
            result = await mock_service.exchange_code_for_tokens("auth_code_123")
            
            assert result is not None
            assert result['expires_in'] is None

    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens_error(self, mock_service):
        """Test token exchange with error"""
        mock_flow = Mock()
        mock_flow.fetch_token.side_effect = Exception("Token exchange failed")
        
        with patch('app.services.google_oauth.Flow') as mock_flow_class:
            mock_flow_class.from_client_config.return_value = mock_flow
            
            result = await mock_service.exchange_code_for_tokens("auth_code_123")
            
            assert result is None

    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens_not_configured(self, mock_service):
        """Test token exchange when not configured"""
        mock_service.client_id = None
        
        with pytest.raises(ValueError, match="Google OAuth credentials not configured"):
            await mock_service.exchange_code_for_tokens("auth_code_123")


class TestGetUserInfo:
    """Test suite for _get_user_info method"""

    @pytest.fixture
    def mock_service(self):
        return GoogleOAuthService()

    @pytest.mark.asyncio
    async def test_get_user_info_success(self, mock_service):
        """Test successful user info retrieval"""
        mock_credentials = Mock()
        mock_user_info = {
            'id': 'user123',
            'email': 'test@example.com',
            'name': 'Test User',
            'picture': 'https://example.com/pic.jpg',
            'verified_email': True
        }
        
        mock_userinfo = Mock()
        mock_userinfo.get.return_value.execute.return_value = mock_user_info
        
        mock_service_obj = Mock()
        mock_service_obj.userinfo.return_value = mock_userinfo
        
        with patch('app.services.google_oauth.build', return_value=mock_service_obj):
            result = await mock_service._get_user_info(mock_credentials)
            
            assert result == {
                'id': 'user123',
                'email': 'test@example.com',
                'name': 'Test User',
                'picture': 'https://example.com/pic.jpg',
                'verified_email': True
            }

    @pytest.mark.asyncio
    async def test_get_user_info_missing_fields(self, mock_service):
        """Test user info retrieval with missing fields"""
        mock_credentials = Mock()
        mock_user_info = {
            'id': 'user123',
            'email': 'test@example.com'
            # Missing name, picture, verified_email
        }
        
        mock_userinfo = Mock()
        mock_userinfo.get.return_value.execute.return_value = mock_user_info
        
        mock_service_obj = Mock()
        mock_service_obj.userinfo.return_value = mock_userinfo
        
        with patch('app.services.google_oauth.build', return_value=mock_service_obj):
            result = await mock_service._get_user_info(mock_credentials)
            
            assert result == {
                'id': 'user123',
                'email': 'test@example.com',
                'name': None,
                'picture': None,
                'verified_email': False
            }

    @pytest.mark.asyncio
    async def test_get_user_info_http_error(self, mock_service):
        """Test user info retrieval with HttpError"""
        from googleapiclient.errors import HttpError
        
        mock_credentials = Mock()
        mock_userinfo = Mock()
        mock_userinfo.get.return_value.execute.side_effect = HttpError(Mock(status=403), b"Forbidden")
        
        mock_service_obj = Mock()
        mock_service_obj.userinfo.return_value = mock_userinfo
        
        with patch('app.services.google_oauth.build', return_value=mock_service_obj):
            result = await mock_service._get_user_info(mock_credentials)
            
            assert result == {}


class TestRefreshToken:
    """Test suite for refresh_access_token method"""

    @pytest.fixture
    def mock_service(self):
        with patch.dict('os.environ', {
            'GOOGLE_CLIENT_ID': 'test_client_id',
            'GOOGLE_CLIENT_SECRET': 'test_client_secret'
        }):
            return GoogleOAuthService()

    def test_refresh_access_token_success(self, mock_service):
        """Test successful token refresh"""
        mock_credentials = Mock()
        mock_credentials.token = "new_access_token"
        mock_credentials.refresh_token = "new_refresh_token"
        mock_credentials.expiry = Mock()
        mock_credentials.expiry.timestamp.return_value = 1640995200.0
        mock_credentials.to_json.return_value = '{"token": "new_access_token"}'
        
        with patch('app.services.google_oauth.Credentials', return_value=mock_credentials):
            result = mock_service.refresh_access_token("refresh_token_123")
            
            assert result is not None
            assert result['access_token'] == "new_access_token"
            assert result['refresh_token'] == "new_refresh_token"
            assert result['expires_in'] == 1640995200.0
            assert result['credentials'] == '{"token": "new_access_token"}'

    def test_refresh_access_token_without_expiry(self, mock_service):
        """Test token refresh without expiry"""
        mock_credentials = Mock()
        mock_credentials.token = "new_access_token"
        mock_credentials.refresh_token = "new_refresh_token"
        mock_credentials.expiry = None
        mock_credentials.to_json.return_value = '{"token": "new_access_token"}'
        
        with patch('app.services.google_oauth.Credentials', return_value=mock_credentials):
            result = mock_service.refresh_access_token("refresh_token_123")
            
            assert result is not None
            assert result['expires_in'] is None

    def test_refresh_access_token_error(self, mock_service):
        """Test token refresh with error"""
        mock_credentials = Mock()
        mock_credentials.refresh.side_effect = Exception("Refresh failed")
        
        with patch('app.services.google_oauth.Credentials', return_value=mock_credentials):
            result = mock_service.refresh_access_token("refresh_token_123")
            
            assert result is None

    def test_refresh_access_token_not_configured(self, mock_service):
        """Test token refresh when not configured"""
        mock_service.client_id = None
        
        with pytest.raises(ValueError, match="Google OAuth credentials not configured"):
            mock_service.refresh_access_token("refresh_token_123")


class TestCredentialsManagement:
    """Test suite for credentials management methods"""

    @pytest.fixture
    def mock_service(self):
        with patch.dict('os.environ', {
            'GOOGLE_CLIENT_ID': 'test_client_id',
            'GOOGLE_CLIENT_SECRET': 'test_client_secret'
        }):
            return GoogleOAuthService()

    def test_get_credentials_from_token(self, mock_service):
        """Test creating credentials from tokens"""
        mock_credentials = Mock()
        
        with patch('app.services.google_oauth.Credentials', return_value=mock_credentials) as mock_creds_class:
            result = mock_service.get_credentials_from_token("access_token", "refresh_token")
            
            assert result == mock_credentials
            mock_creds_class.assert_called_once_with(
                token="access_token",
                refresh_token="refresh_token",
                token_uri="https://oauth2.googleapis.com/token",
                client_id="test_client_id",
                client_secret="test_client_secret"
            )

    def test_get_credentials_from_token_without_refresh(self, mock_service):
        """Test creating credentials without refresh token"""
        mock_credentials = Mock()
        
        with patch('app.services.google_oauth.Credentials', return_value=mock_credentials) as mock_creds_class:
            result = mock_service.get_credentials_from_token("access_token")
            
            assert result == mock_credentials
            mock_creds_class.assert_called_once_with(
                token="access_token",
                refresh_token=None,
                token_uri="https://oauth2.googleapis.com/token",
                client_id="test_client_id",
                client_secret="test_client_secret"
            )

    def test_refresh_credentials_if_needed_not_expired(self, mock_service):
        """Test refresh_credentials_if_needed when not expired"""
        mock_credentials = Mock()
        mock_credentials.expired = False
        
        result = mock_service.refresh_credentials_if_needed(mock_credentials)
        
        assert result == mock_credentials
        # Should not call refresh

    def test_refresh_credentials_if_needed_expired_success(self, mock_service):
        """Test refresh_credentials_if_needed when expired - success"""
        mock_credentials = Mock()
        mock_credentials.expired = True
        mock_credentials.refresh_token = "refresh_token"
        
        result = mock_service.refresh_credentials_if_needed(mock_credentials)
        
        assert result == mock_credentials
        mock_credentials.refresh.assert_called_once()

    def test_refresh_credentials_if_needed_expired_no_refresh_token(self, mock_service):
        """Test refresh_credentials_if_needed when expired but no refresh token"""
        mock_credentials = Mock()
        mock_credentials.expired = True
        mock_credentials.refresh_token = None
        
        result = mock_service.refresh_credentials_if_needed(mock_credentials)
        
        assert result == mock_credentials
        # Should not call refresh when no refresh token

    def test_refresh_credentials_if_needed_refresh_error(self, mock_service):
        """Test refresh_credentials_if_needed when refresh fails"""
        mock_credentials = Mock()
        mock_credentials.expired = True
        mock_credentials.refresh_token = "refresh_token"
        mock_credentials.refresh.side_effect = Exception("Refresh failed")
        
        with pytest.raises(Exception, match="Refresh failed"):
            mock_service.refresh_credentials_if_needed(mock_credentials)


class TestGmailAPI:
    """Test suite for Gmail API methods"""

    @pytest.fixture
    def mock_service(self):
        return GoogleOAuthService()

    @pytest.mark.asyncio
    async def test_get_gmail_messages_success(self, mock_service):
        """Test successful Gmail messages retrieval"""
        mock_credentials = Mock()
        
        # Mock Gmail API responses
        mock_messages_list = {
            'messages': [{'id': 'msg1'}, {'id': 'msg2'}],
            'resultSizeEstimate': 2
        }
        
        mock_message_detail = {
            'id': 'msg1',
            'threadId': 'thread1',
            'snippet': 'Test message snippet',
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'sender@example.com'},
                    {'name': 'Subject', 'value': 'Test Subject'},
                    {'name': 'Date', 'value': 'Wed, 1 Jan 2024 12:00:00 GMT'}
                ]
            }
        }
        
        mock_messages = Mock()
        mock_messages.list.return_value.execute.return_value = mock_messages_list
        mock_messages.get.return_value.execute.return_value = mock_message_detail
        
        mock_users = Mock()
        mock_users.messages.return_value = mock_messages
        
        mock_gmail_service = Mock()
        mock_gmail_service.users.return_value = mock_users
        
        with patch('app.services.google_oauth.build', return_value=mock_gmail_service), \
             patch.object(mock_service, '_extract_email_body', return_value="Email body content"):
            
            result = await mock_service.get_gmail_messages(mock_credentials, "test query", 5)
            
            assert result['resultSizeEstimate'] == 2
            assert len(result['messages']) == 2
            assert result['messages'][0]['id'] == 'msg1'
            assert result['messages'][0]['from'] == 'sender@example.com'
            assert result['messages'][0]['subject'] == 'Test Subject'
            assert result['messages'][0]['body'] == "Email body content"

    @pytest.mark.asyncio
    async def test_get_gmail_messages_http_error(self, mock_service):
        """Test Gmail messages retrieval with HttpError"""
        from googleapiclient.errors import HttpError
        
        mock_credentials = Mock()
        
        mock_messages = Mock()
        mock_messages.list.return_value.execute.side_effect = HttpError(Mock(status=403), b"Forbidden")
        
        mock_users = Mock()
        mock_users.messages.return_value = mock_messages
        
        mock_gmail_service = Mock()
        mock_gmail_service.users.return_value = mock_users
        
        with patch('app.services.google_oauth.build', return_value=mock_gmail_service):
            result = await mock_service.get_gmail_messages(mock_credentials)
            
            assert 'error' in result
            assert result['messages'] == []

    def test_extract_email_body_plain_text(self, mock_service):
        """Test extracting plain text email body"""
        # Create base64url encoded data
        plain_text = "This is a plain text email body"
        encoded_data = base64.urlsafe_b64encode(plain_text.encode()).decode().rstrip('=')
        
        payload = {
            'mimeType': 'text/plain',
            'body': {'data': encoded_data}
        }
        
        result = mock_service._extract_email_body(payload)
        assert result == plain_text

    def test_extract_email_body_html(self, mock_service):
        """Test extracting HTML email body"""
        html_content = "<html><body><p>This is <b>HTML</b> content</p></body></html>"
        encoded_data = base64.urlsafe_b64encode(html_content.encode()).decode().rstrip('=')
        
        payload = {
            'mimeType': 'text/html',
            'body': {'data': encoded_data}
        }
        
        result = mock_service._extract_email_body(payload)
        assert "This is HTML content" in result
        assert "<html>" not in result  # HTML tags should be removed

    def test_extract_email_body_multipart(self, mock_service):
        """Test extracting multipart email body"""
        plain_text = "Plain text part"
        html_content = "<p>HTML part</p>"
        
        plain_encoded = base64.urlsafe_b64encode(plain_text.encode()).decode().rstrip('=')
        html_encoded = base64.urlsafe_b64encode(html_content.encode()).decode().rstrip('=')
        
        payload = {
            'mimeType': 'multipart/alternative',
            'parts': [
                {
                    'mimeType': 'text/plain',
                    'body': {'data': plain_encoded}
                },
                {
                    'mimeType': 'text/html',
                    'body': {'data': html_encoded}
                }
            ]
        }
        
        result = mock_service._extract_email_body(payload)
        assert "Plain text part" in result
        assert "HTML part" in result

    def test_extract_email_body_empty(self, mock_service):
        """Test extracting empty email body"""
        payload = {
            'mimeType': 'text/plain',
            'body': {'data': ''}
        }
        
        result = mock_service._extract_email_body(payload)
        assert result == ""

    def test_extract_email_body_fallback_to_snippet(self, mock_service):
        """Test fallback to snippet when no body content"""
        payload = {
            'mimeType': 'application/octet-stream',
            'snippet': 'Fallback snippet content'
        }
        
        result = mock_service._extract_email_body(payload)
        assert result == "Fallback snippet content"

    @pytest.mark.asyncio
    async def test_get_gmail_message_content(self, mock_service):
        """Test getting specific Gmail message content"""
        mock_credentials = Mock()
        message_id = "msg123"
        
        mock_message = {
            'id': message_id,
            'threadId': 'thread123',
            'payload': {'mimeType': 'text/plain'},
            'snippet': 'Message snippet'
        }
        
        mock_messages = Mock()
        mock_messages.get.return_value.execute.return_value = mock_message
        
        mock_users = Mock()
        mock_users.messages.return_value = mock_messages
        
        mock_gmail_service = Mock()
        mock_gmail_service.users.return_value = mock_users
        
        with patch('app.services.google_oauth.build', return_value=mock_gmail_service):
            result = await mock_service.get_gmail_message_content(mock_credentials, message_id)
            
            assert result['id'] == message_id
            assert result['threadId'] == 'thread123'
            assert result['snippet'] == 'Message snippet'

    @pytest.mark.asyncio
    async def test_get_gmail_message_content_error(self, mock_service):
        """Test getting Gmail message content with error"""
        from googleapiclient.errors import HttpError
        
        mock_credentials = Mock()
        
        mock_messages = Mock()
        mock_messages.get.return_value.execute.side_effect = HttpError(Mock(status=404), b"Not Found")
        
        mock_users = Mock()
        mock_users.messages.return_value = mock_messages
        
        mock_gmail_service = Mock()
        mock_gmail_service.users.return_value = mock_users
        
        with patch('app.services.google_oauth.build', return_value=mock_gmail_service):
            result = await mock_service.get_gmail_message_content(mock_credentials, "msg123")
            
            assert 'error' in result


class TestDriveAPI:
    """Test suite for Drive API methods"""

    @pytest.fixture
    def mock_service(self):
        return GoogleOAuthService()

    @pytest.mark.asyncio
    async def test_get_drive_files_success(self, mock_service):
        """Test successful Drive files retrieval"""
        mock_credentials = Mock()
        
        mock_files = {
            'files': [
                {'id': 'file1', 'name': 'Document.pdf', 'mimeType': 'application/pdf'},
                {'id': 'file2', 'name': 'Spreadsheet.xlsx', 'mimeType': 'application/vnd.ms-excel'}
            ],
            'nextPageToken': 'next_token'
        }
        
        mock_files_obj = Mock()
        mock_files_obj.list.return_value.execute.return_value = mock_files
        
        mock_drive_service = Mock()
        mock_drive_service.files.return_value = mock_files_obj
        
        with patch('app.services.google_oauth.build', return_value=mock_drive_service), \
             patch.object(mock_service, 'refresh_credentials_if_needed', return_value=mock_credentials):
            
            result = await mock_service.get_drive_files(mock_credentials, "type:pdf", 5)
            
            assert len(result['files']) == 2
            assert result['nextPageToken'] == 'next_token'
            assert result['files'][0]['name'] == 'Document.pdf'

    @pytest.mark.asyncio
    async def test_get_drive_files_error(self, mock_service):
        """Test Drive files retrieval with error"""
        from googleapiclient.errors import HttpError
        
        mock_credentials = Mock()
        
        mock_files_obj = Mock()
        mock_files_obj.list.return_value.execute.side_effect = HttpError(Mock(status=403), b"Forbidden")
        
        mock_drive_service = Mock()
        mock_drive_service.files.return_value = mock_files_obj
        
        with patch('app.services.google_oauth.build', return_value=mock_drive_service), \
             patch.object(mock_service, 'refresh_credentials_if_needed', return_value=mock_credentials):
            
            result = await mock_service.get_drive_files(mock_credentials)
            
            assert 'error' in result
            assert result['files'] == []

    @pytest.mark.asyncio
    async def test_create_folder_structure(self, mock_service):
        """Test creating nested folder structure"""
        mock_credentials = Mock()
        
        with patch.object(mock_service, 'refresh_credentials_if_needed', return_value=mock_credentials), \
             patch.object(mock_service, '_get_or_create_folder', new_callable=AsyncMock, side_effect=['folder1', 'folder2', 'folder3']):
            
            result = await mock_service.create_folder_structure(mock_credentials, "Projects/Client")
            
            assert result == 'folder3'
            # Should create: TURFMAPP -> Projects -> Client
            assert mock_service._get_or_create_folder.call_count == 3

    @pytest.mark.asyncio
    async def test_get_or_create_folder_existing(self, mock_service):
        """Test getting existing folder"""
        mock_service_obj = Mock()
        
        # Mock existing folder found
        mock_files_result = {
            'files': [{'id': 'existing_folder_id', 'name': 'ExistingFolder'}]
        }
        mock_service_obj.files.return_value.list.return_value.execute.return_value = mock_files_result
        
        folder_id = await mock_service._get_or_create_folder(mock_service_obj, "ExistingFolder")
        
        assert folder_id == 'existing_folder_id'

    @pytest.mark.asyncio
    async def test_get_or_create_folder_create_new(self, mock_service):
        """Test creating new folder"""
        mock_service_obj = Mock()
        
        # Mock no existing folder found
        mock_files_result = {'files': []}
        mock_service_obj.files.return_value.list.return_value.execute.return_value = mock_files_result
        
        # Mock folder creation
        mock_create_result = {'id': 'new_folder_id'}
        mock_service_obj.files.return_value.create.return_value.execute.return_value = mock_create_result
        
        folder_id = await mock_service._get_or_create_folder(mock_service_obj, "NewFolder", "parent_id")
        
        assert folder_id == 'new_folder_id'

    @pytest.mark.asyncio
    async def test_upload_file_to_drive_new_file(self, mock_service):
        """Test uploading new file to Drive"""
        mock_credentials = Mock()
        file_content = b"Test file content"
        filename = "test.txt"
        
        mock_files_result = {'files': []}  # No existing file
        mock_create_result = {
            'id': 'new_file_id',
            'name': filename,
            'webViewLink': 'https://drive.google.com/file/d/new_file_id'
        }
        
        mock_files_obj = Mock()
        mock_files_obj.list.return_value.execute.return_value = mock_files_result
        mock_files_obj.create.return_value.execute.return_value = mock_create_result
        
        mock_drive_service = Mock()
        mock_drive_service.files.return_value = mock_files_obj
        
        with patch('app.services.google_oauth.build', return_value=mock_drive_service), \
             patch.object(mock_service, 'refresh_credentials_if_needed', return_value=mock_credentials), \
             patch.object(mock_service, 'create_folder_structure', new_callable=AsyncMock, return_value='folder_id'), \
             patch('app.services.google_oauth.MediaIoBaseUpload'):
            
            result = await mock_service.upload_file_to_drive(mock_credentials, file_content, filename, "Projects")
            
            assert result['success'] is True
            assert result['action'] == 'created'
            assert result['file']['id'] == 'new_file_id'

    @pytest.mark.asyncio
    async def test_upload_file_to_drive_update_existing(self, mock_service):
        """Test updating existing file in Drive"""
        mock_credentials = Mock()
        file_content = b"Updated file content"
        filename = "test.txt"
        
        mock_files_result = {'files': [{'id': 'existing_file_id', 'name': filename}]}
        mock_update_result = {
            'id': 'existing_file_id',
            'name': filename,
            'webViewLink': 'https://drive.google.com/file/d/existing_file_id'
        }
        
        mock_files_obj = Mock()
        mock_files_obj.list.return_value.execute.return_value = mock_files_result
        mock_files_obj.update.return_value.execute.return_value = mock_update_result
        
        mock_drive_service = Mock()
        mock_drive_service.files.return_value = mock_files_obj
        
        with patch('app.services.google_oauth.build', return_value=mock_drive_service), \
             patch.object(mock_service, 'refresh_credentials_if_needed', return_value=mock_credentials), \
             patch('app.services.google_oauth.MediaIoBaseUpload'):
            
            result = await mock_service.upload_file_to_drive(mock_credentials, file_content, filename)
            
            assert result['success'] is True
            assert result['action'] == 'updated'
            assert result['file']['id'] == 'existing_file_id'

    @pytest.mark.asyncio
    async def test_delete_file_from_drive(self, mock_service):
        """Test deleting file from Drive"""
        mock_credentials = Mock()
        file_id = "file_to_delete"
        
        mock_file_info = {'id': file_id, 'name': 'file_to_delete.txt'}
        
        mock_files_obj = Mock()
        mock_files_obj.get.return_value.execute.return_value = mock_file_info
        mock_files_obj.delete.return_value.execute.return_value = None  # Delete returns nothing
        
        mock_drive_service = Mock()
        mock_drive_service.files.return_value = mock_files_obj
        
        with patch('app.services.google_oauth.build', return_value=mock_drive_service), \
             patch.object(mock_service, 'refresh_credentials_if_needed', return_value=mock_credentials):
            
            result = await mock_service.delete_file_from_drive(mock_credentials, file_id)
            
            assert result['success'] is True
            assert file_id in result['message']
            assert result['file_id'] == file_id

    @pytest.mark.asyncio
    async def test_list_files_in_folder(self, mock_service):
        """Test listing files in a specific folder"""
        mock_credentials = Mock()
        folder_path = "Projects/Client"
        
        mock_files = {
            'files': [
                {'id': 'file1', 'name': 'doc1.pdf'},
                {'id': 'file2', 'name': 'doc2.docx'}
            ]
        }
        
        mock_files_obj = Mock()
        mock_files_obj.list.return_value.execute.return_value = mock_files
        
        mock_drive_service = Mock()
        mock_drive_service.files.return_value = mock_files_obj
        
        with patch('app.services.google_oauth.build', return_value=mock_drive_service), \
             patch.object(mock_service, 'refresh_credentials_if_needed', return_value=mock_credentials), \
             patch.object(mock_service, 'create_folder_structure', new_callable=AsyncMock, return_value='folder_id'):
            
            result = await mock_service.list_files_in_folder(mock_credentials, folder_path)
            
            assert result['success'] is True
            assert len(result['files']) == 2
            assert result['folder_path'] == folder_path


class TestCalendarAPI:
    """Test suite for Calendar API methods"""

    @pytest.fixture
    def mock_service(self):
        return GoogleOAuthService()

    @pytest.mark.asyncio
    async def test_get_calendar_events_success(self, mock_service):
        """Test successful Calendar events retrieval"""
        mock_credentials = Mock()
        
        mock_events = {
            'items': [
                {
                    'id': 'event1',
                    'summary': 'Meeting 1',
                    'start': {'dateTime': '2024-01-01T10:00:00Z'}
                },
                {
                    'id': 'event2', 
                    'summary': 'Meeting 2',
                    'start': {'dateTime': '2024-01-02T14:00:00Z'}
                }
            ],
            'nextPageToken': 'next_token'
        }
        
        mock_events_obj = Mock()
        mock_events_obj.list.return_value.execute.return_value = mock_events
        
        mock_calendar_service = Mock()
        mock_calendar_service.events.return_value = mock_events_obj
        
        with patch('app.services.google_oauth.build', return_value=mock_calendar_service):
            result = await mock_service.get_calendar_events(mock_credentials, 'primary', 10, True)
            
            assert len(result['events']) == 2
            assert result['nextPageToken'] == 'next_token'
            assert result['events'][0]['summary'] == 'Meeting 1'

    @pytest.mark.asyncio
    async def test_get_calendar_events_upcoming_only(self, mock_service):
        """Test Calendar events with upcoming_only filter"""
        mock_credentials = Mock()
        
        mock_events = {'items': []}
        
        mock_events_obj = Mock()
        mock_events_obj.list.return_value.execute.return_value = mock_events
        
        mock_calendar_service = Mock()
        mock_calendar_service.events.return_value = mock_events_obj
        
        with patch('app.services.google_oauth.build', return_value=mock_calendar_service):
            await mock_service.get_calendar_events(mock_credentials, upcoming_only=True)
            
            # Verify that timeMin was added to query
            call_args = mock_events_obj.list.call_args[1]
            assert 'timeMin' in call_args
            # Should be a recent timestamp
            assert call_args['timeMin'].startswith('2024') or call_args['timeMin'].startswith('2025')

    @pytest.mark.asyncio
    async def test_get_calendar_events_all_time(self, mock_service):
        """Test Calendar events without time filtering"""
        mock_credentials = Mock()
        
        mock_events = {'items': []}
        
        mock_events_obj = Mock()
        mock_events_obj.list.return_value.execute.return_value = mock_events
        
        mock_calendar_service = Mock()
        mock_calendar_service.events.return_value = mock_events_obj
        
        with patch('app.services.google_oauth.build', return_value=mock_calendar_service):
            await mock_service.get_calendar_events(mock_credentials, upcoming_only=False)
            
            # Verify that timeMin was NOT added to query
            call_args = mock_events_obj.list.call_args[1]
            assert 'timeMin' not in call_args

    @pytest.mark.asyncio
    async def test_get_calendar_events_error(self, mock_service):
        """Test Calendar events retrieval with error"""
        from googleapiclient.errors import HttpError
        
        mock_credentials = Mock()
        
        mock_events_obj = Mock()
        mock_events_obj.list.return_value.execute.side_effect = HttpError(Mock(status=403), b"Forbidden")
        
        mock_calendar_service = Mock()
        mock_calendar_service.events.return_value = mock_events_obj
        
        with patch('app.services.google_oauth.build', return_value=mock_calendar_service):
            result = await mock_service.get_calendar_events(mock_credentials)
            
            assert 'error' in result
            assert result['events'] == []


class TestEdgeCasesAndErrorHandling:
    """Test suite for edge cases and error handling"""

    @pytest.fixture
    def mock_service(self):
        return GoogleOAuthService()

    def test_base64url_decoding_with_padding(self, mock_service):
        """Test base64url decoding with missing padding"""
        # Test string that needs padding
        test_string = "Hello World"
        # Create base64url without proper padding
        encoded = base64.urlsafe_b64encode(test_string.encode()).decode().rstrip('=')
        
        payload = {
            'mimeType': 'text/plain',
            'body': {'data': encoded}
        }
        
        result = mock_service._extract_email_body(payload)
        assert result == test_string

    def test_base64url_decoding_error_handling(self, mock_service):
        """Test base64url decoding with invalid data"""
        payload = {
            'mimeType': 'text/plain',
            'body': {'data': 'invalid_base64_data!!!'}
        }
        
        # Should not raise exception, should return empty string
        result = mock_service._extract_email_body(payload)
        assert result == ""

    @pytest.mark.asyncio
    async def test_concurrent_api_calls(self, mock_service):
        """Test concurrent API calls don't interfere"""
        mock_credentials = Mock()
        
        # Mock different API responses
        mock_gmail_service = Mock()
        mock_gmail_service.users.return_value.messages.return_value.list.return_value.execute.return_value = {
            'messages': [], 'resultSizeEstimate': 0
        }
        
        mock_drive_service = Mock()
        mock_drive_service.files.return_value.list.return_value.execute.return_value = {
            'files': [], 'nextPageToken': None
        }
        
        with patch('app.services.google_oauth.build') as mock_build:
            def build_side_effect(service_name, *args, **kwargs):
                if service_name == 'gmail':
                    return mock_gmail_service
                elif service_name == 'drive':
                    return mock_drive_service
                return Mock()
            
            mock_build.side_effect = build_side_effect
            
            with patch.object(mock_service, 'refresh_credentials_if_needed', return_value=mock_credentials):
                # Execute concurrent calls
                import asyncio
                gmail_task = mock_service.get_gmail_messages(mock_credentials)
                drive_task = mock_service.get_drive_files(mock_credentials)
                
                gmail_result, drive_result = await asyncio.gather(gmail_task, drive_task)
                
                assert 'messages' in gmail_result
                assert 'files' in drive_result

    def test_large_email_body_processing(self, mock_service):
        """Test processing of large email bodies"""
        # Create a large text content
        large_text = "x" * 10000  # 10KB of text
        encoded_data = base64.urlsafe_b64encode(large_text.encode()).decode().rstrip('=')
        
        payload = {
            'mimeType': 'text/plain',
            'body': {'data': encoded_data}
        }
        
        result = mock_service._extract_email_body(payload)
        assert len(result) == 10000
        assert result == large_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
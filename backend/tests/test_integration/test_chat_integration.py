"""
Integration tests for Chat functionality that test actual data flow.

These tests verify that the complete chat pipeline works correctly, 
including conversation persistence, message metadata, and sources extraction.
Unlike ping tests, these validate that business logic functions properly.
"""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app


class TestChatIntegration:
    """Integration tests for complete chat functionality"""
    
    @pytest.fixture
    def client(self):
        """Test client fixture"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_auth_user(self):
        """Mock authenticated user"""
        return {"id": "test-user-123", "email": "test@example.com"}
    
    @pytest.fixture
    def mock_api_response(self):
        """Mock OpenAI API response with sources"""
        return {
            "id": "resp-123",
            "status": "completed",
            "output_text": "Here's the J1 League standings: https://example.com/j1-league Check out more at https://sports.com/soccer",
            "usage": {"completion_tokens": 50, "prompt_tokens": 100}
        }
    
    @pytest.mark.asyncio
    @patch('app.core.simple_auth.get_current_user_from_token')
    @patch('app.services.enhanced_chat_service.EnhancedChatService.call_responses_api')
    @patch('app.services.enhanced_chat_service.EnhancedChatService.save_message_to_conversation')
    async def test_chat_send_preserves_sources_metadata(
        self, 
        mock_save_message,
        mock_api_call,
        mock_auth,
        client,
        mock_auth_user,
        mock_api_response
    ):
        """Test that chat messages preserve sources in metadata"""
        # Setup mocks
        mock_auth.return_value = mock_auth_user
        mock_api_call.return_value = mock_api_response
        mock_save_message.return_value = True
        
        # Send chat message
        response = client.post(
            "/api/v1/chat/send",
            headers={"Authorization": "Bearer test-token"},
            json={"message": "Show me J1 League standings"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "conversation_id" in data
        assert "user_message" in data
        assert "assistant_message" in data
        assert "sources" in data
        
        # Verify sources were extracted from response
        sources = data["sources"]
        assert isinstance(sources, list)
        assert len(sources) > 0
        
        # Check that sources have required fields
        for source in sources:
            assert "url" in source
            assert "site" in source
            assert "favicon" in source
            
        # Verify save_message was called with sources metadata
        calls = mock_save_message.call_args_list
        assistant_call = None
        for call in calls:
            args, kwargs = call
            if args[2] == "assistant":  # role parameter
                assistant_call = call
                break
        
        assert assistant_call is not None
        metadata = assistant_call[0][4]  # metadata parameter
        assert "sources" in metadata
        assert len(metadata["sources"]) > 0
    
    @pytest.mark.asyncio
    @patch('app.core.simple_auth.get_current_user_from_token')
    @patch('app.services.enhanced_chat_service.EnhancedChatService.get_conversation_history')
    async def test_conversation_history_includes_metadata(
        self,
        mock_get_history,
        mock_auth,
        client,
        mock_auth_user
    ):
        """Test that conversation history preserves message metadata including sources"""
        # Setup mock conversation history with sources
        mock_messages = [
            {
                "id": "msg-1",
                "role": "user",
                "content": "Show me J1 League standings",
                "created_at": "2025-08-30T12:00:00Z",
                "metadata": {}
            },
            {
                "id": "msg-2", 
                "role": "assistant",
                "content": "Here are the standings: https://example.com/j1-league",
                "created_at": "2025-08-30T12:01:00Z",
                "metadata": {
                    "sources": [
                        {
                            "url": "https://example.com/j1-league",
                            "site": "example.com",
                            "favicon": "https://www.google.com/s2/favicons?domain=example.com&sz=64"
                        }
                    ],
                    "model": "gpt-4o"
                }
            }
        ]
        
        # Setup mocks
        mock_auth.return_value = mock_auth_user
        mock_get_history.return_value = mock_messages
        
        # Get conversation
        response = client.get(
            "/api/v1/chat/conversations/test-conv-123",
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "conversation" in data
        assert "messages" in data
        
        # Verify messages preserve metadata
        messages = data["messages"]
        assert len(messages) == 2
        
        # Check assistant message has metadata with sources
        assistant_msg = next(msg for msg in messages if msg["role"] == "assistant")
        assert "metadata" in assistant_msg
        assert "sources" in assistant_msg["metadata"]
        assert len(assistant_msg["metadata"]["sources"]) > 0
        
        # Verify source structure
        source = assistant_msg["metadata"]["sources"][0]
        assert "url" in source
        assert "site" in source
        assert "favicon" in source
    
    @pytest.mark.asyncio
    @patch('app.core.simple_auth.get_current_user_from_token')
    async def test_conversation_not_found_returns_404(
        self,
        mock_auth,
        client,
        mock_auth_user
    ):
        """Test that requesting non-existent conversation returns 404"""
        mock_auth.return_value = mock_auth_user
        
        # Mock empty conversation history (conversation doesn't exist)
        with patch('app.services.enhanced_chat_service.EnhancedChatService.get_conversation_history', return_value=[]):
            response = client.get(
                "/api/v1/chat/conversations/nonexistent-id",
                headers={"Authorization": "Bearer test-token"}
            )
            
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    @patch('app.core.simple_auth.get_current_user_from_token')
    @patch('app.services.enhanced_chat_service.EnhancedChatService.call_responses_api')
    async def test_api_error_handling_preserves_conversation(
        self,
        mock_api_call,
        mock_auth,
        client,
        mock_auth_user
    ):
        """Test that API errors don't break conversation flow"""
        # Setup mocks
        mock_auth.return_value = mock_auth_user
        mock_api_call.side_effect = Exception("OpenAI API error")
        
        # Mock conversation creation and saving
        with patch('app.services.enhanced_chat_service.EnhancedChatService.create_conversation', return_value="conv-123"), \
             patch('app.services.enhanced_chat_service.EnhancedChatService.save_message_to_conversation', return_value=True):
            
            response = client.post(
                "/api/v1/chat/send",
                headers={"Authorization": "Bearer test-token"},
                json={"message": "Test message"}
            )
            
            # Should still return 200 with error message
            assert response.status_code == 200
            data = response.json()
            
            # Verify error handling structure
            assert "conversation_id" in data
            assert "assistant_message" in data
            assert "error" in data
            
            # Assistant message should contain error explanation
            assert "error" in data["assistant_message"]["content"].lower()
    
    @pytest.mark.asyncio
    @patch('app.core.simple_auth.get_current_user_from_token')
    async def test_send_message_validates_required_fields(
        self,
        mock_auth,
        client,
        mock_auth_user
    ):
        """Test input validation for required message field"""
        mock_auth.return_value = mock_auth_user
        
        # Test empty message
        response = client.post(
            "/api/v1/chat/send",
            headers={"Authorization": "Bearer test-token"},
            json={"message": ""}
        )
        
        # Should return validation error
        assert response.status_code == 422
        error_data = response.json()
        assert "detail" in error_data
        
        # Check validation error mentions message field
        error_details = error_data["detail"]
        message_error = next(
            (err for err in error_details if err.get("loc") and "message" in err["loc"]),
            None
        )
        assert message_error is not None
    
    def test_unauthorized_requests_rejected(self, client):
        """Test that endpoints properly reject unauthorized requests"""
        endpoints_to_test = [
            ("POST", "/api/v1/chat/send", {"message": "test"}),
            ("GET", "/api/v1/chat/conversations", None),
            ("GET", "/api/v1/chat/conversations/test-id", None),
            ("DELETE", "/api/v1/chat/conversations/test-id", None)
        ]
        
        for method, endpoint, json_data in endpoints_to_test:
            if method == "POST":
                response = client.post(endpoint, json=json_data)
            elif method == "GET":
                response = client.get(endpoint)
            elif method == "DELETE":
                response = client.delete(endpoint)
            
            assert response.status_code == 401, f"Endpoint {method} {endpoint} should require auth"


class TestChatDataFlow:
    """Tests that verify complete data flow through the chat system"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def mock_user(self):
        return {"id": "user-456", "email": "dataflow@test.com"}
    
    @pytest.mark.asyncio
    @patch('app.core.simple_auth.get_current_user_from_token')
    @patch('httpx.AsyncClient')
    async def test_sources_extraction_pipeline(
        self,
        mock_httpx,
        mock_auth,
        client,
        mock_user
    ):
        """Test complete sources extraction pipeline from API response to frontend"""
        # Setup auth
        mock_auth.return_value = mock_user
        
        # Mock HTTP client for API calls and source enrichment
        mock_client_instance = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_client_instance
        
        # Mock API response with URLs
        api_response = MagicMock()
        api_response.status_code = 200
        api_response.json.return_value = {
            "id": "resp-456",
            "status": "completed",
            "output_text": "Check out https://www.jleague.jp/en/ for official standings and https://sports.yahoo.com/soccer for more analysis."
        }
        
        # Mock source enrichment response
        enrichment_response = MagicMock()
        enrichment_response.status_code = 200
        enrichment_response.text = """
        <html>
        <head><title>J.League Official Site</title></head>
        <meta property="og:image" content="https://www.jleague.jp/images/logo.jpg">
        </html>
        """
        
        mock_client_instance.post.return_value = api_response
        mock_client_instance.get.return_value = enrichment_response
        
        # Mock database operations
        with patch('app.services.enhanced_chat_service.EnhancedChatService.create_conversation', return_value="conv-789"), \
             patch('app.services.enhanced_chat_service.EnhancedChatService.get_conversation_history', return_value=[]), \
             patch('app.services.enhanced_chat_service.EnhancedChatService.save_message_to_conversation', return_value=True):
            
            # Send message that should trigger sources extraction
            response = client.post(
                "/api/v1/chat/send",
                headers={"Authorization": "Bearer test-token"},
                json={"message": "Show me J1 League info"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify sources were extracted and enriched
            sources = data.get("sources", [])
            assert len(sources) >= 2  # Should have extracted at least 2 URLs
            
            # Verify source structure matches frontend expectations
            for source in sources:
                assert all(key in source for key in ["url", "site", "favicon"])
                assert source["url"].startswith("http")
                assert len(source["site"]) > 0
                assert "favicon" in source["favicon"]
    
    @pytest.mark.asyncio
    @patch('app.core.simple_auth.get_current_user_from_token')
    async def test_conversation_persistence_flow(
        self,
        mock_auth,
        client,
        mock_user
    ):
        """Test complete conversation persistence from creation to retrieval"""
        mock_auth.return_value = mock_user
        
        conversation_data = {}
        messages_data = {}
        
        # Mock database operations to track data flow
        async def mock_create_conv(user_id, title=None):
            conv_id = "persistent-conv-123"
            conversation_data[conv_id] = {
                "id": conv_id,
                "user_id": user_id,
                "title": title or "New Conversation",
                "created_at": "2025-08-30T12:00:00Z"
            }
            return {"id": conv_id}
        
        async def mock_save_message(conv_id, user_id, role, content, metadata=None):
            if conv_id not in messages_data:
                messages_data[conv_id] = []
            
            message = {
                "id": f"msg-{len(messages_data[conv_id]) + 1}",
                "role": role,
                "content": content,
                "created_at": "2025-08-30T12:00:00Z",
                "metadata": metadata or {}
            }
            messages_data[conv_id].append(message)
            return True
        
        async def mock_get_history(conv_id, user_id):
            return messages_data.get(conv_id, [])
        
        async def mock_get_conversations(user_id):
            return [
                {
                    "id": conv_id,
                    "title": data["title"],
                    "created_at": data["created_at"],
                    "updated_at": data["created_at"]
                }
                for conv_id, data in conversation_data.items()
                if data["user_id"] == user_id
            ]
        
        with patch('app.services.enhanced_chat_service.EnhancedChatService.create_conversation', side_effect=mock_create_conv), \
             patch('app.services.enhanced_chat_service.EnhancedChatService.save_message_to_conversation', side_effect=mock_save_message), \
             patch('app.services.enhanced_chat_service.EnhancedChatService.get_conversation_history', side_effect=mock_get_history), \
             patch('app.services.enhanced_chat_service.EnhancedChatService.get_conversation_list', side_effect=mock_get_conversations), \
             patch('app.services.enhanced_chat_service.EnhancedChatService.call_responses_api', return_value={"output_text": "Hello! How can I help?"}):
            
            # 1. Send initial message (creates conversation)
            send_response = client.post(
                "/api/v1/chat/send",
                headers={"Authorization": "Bearer test-token"},
                json={"message": "Hello, start a new conversation"}
            )
            
            assert send_response.status_code == 200
            send_data = send_response.json()
            conv_id = send_data["conversation_id"]
            
            # 2. Verify conversation appears in list
            list_response = client.get(
                "/api/v1/chat/conversations",
                headers={"Authorization": "Bearer test-token"}
            )
            
            assert list_response.status_code == 200
            conversations = list_response.json()["conversations"]
            assert len(conversations) == 1
            assert conversations[0]["id"] == conv_id
            
            # 3. Retrieve conversation history
            history_response = client.get(
                f"/api/v1/chat/conversations/{conv_id}",
                headers={"Authorization": "Bearer test-token"}
            )
            
            assert history_response.status_code == 200
            history_data = history_response.json()
            
            # Verify complete data flow
            assert history_data["conversation"]["id"] == conv_id
            messages = history_data["messages"]
            assert len(messages) == 2  # User + assistant message
            
            # Verify message structure and metadata preservation
            user_msg = next(msg for msg in messages if msg["role"] == "user")
            assistant_msg = next(msg for msg in messages if msg["role"] == "assistant")
            
            assert user_msg["content"] == "Hello, start a new conversation"
            assert "metadata" in user_msg
            assert "metadata" in assistant_msg
            assert assistant_msg["content"] == "Hello! How can I help?"
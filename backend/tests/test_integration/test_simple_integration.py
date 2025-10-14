"""
Simple integration tests for Chat API to demonstrate the difference from ping tests
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app


class TestSimpleChatIntegration:
    """Simple integration tests that verify actual functionality"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_health_endpoint_returns_correct_data(self, client):
        """Test that health endpoint returns actual service data"""
        response = client.get("/api/v1/chat/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify actual content (not just that it exists)
        assert data["status"] == "healthy"
        assert data["service"] == "chat"
        assert "timestamp" in data
    
    def test_models_endpoint_returns_actual_models(self, client):
        """Test that models endpoint returns expected model list"""
        response = client.get("/api/v1/chat/models")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify actual models are present (not just any list)
        models = data["models"]
        model_ids = [m["id"] for m in models]
        
        # These should be the actual models from the endpoint
        expected_models = ["gpt-4o", "gpt-4o-mini", "o1", "o1-mini", "o1-preview"]
        for expected in expected_models:
            assert expected in model_ids, f"Expected model {expected} not found"
    
    @patch('app.core.jwt_auth.get_current_user_from_token')
    def test_send_message_requires_authentication(self, mock_auth, client):
        """Test that send message properly validates authentication"""
        # Test without auth header
        response = client.post("/api/v1/chat/send", json={"message": "test"})
        assert response.status_code == 401
        
        # Test with mock auth
        mock_auth.return_value = {"id": "user123", "email": "test@example.com"}
        
        with patch('app.services.chat_service.EnhancedChatService.process_chat_request') as mock_process:
            mock_process.return_value = {
                "conversation_id": "conv123",
                "user_message": {"role": "user", "content": "test"},
                "assistant_message": {"role": "assistant", "content": "response"},
                "sources": []
            }
            
            response = client.post(
                "/api/v1/chat/send",
                headers={"Authorization": "Bearer valid-token"},
                json={"message": "test message"}
            )
            
            # Should succeed with proper auth
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure matches what frontend expects
            assert "conversation_id" in data
            assert "user_message" in data
            assert "assistant_message" in data
            assert "sources" in data  # This would have failed before our fix!
    
    @patch('app.core.jwt_auth.get_current_user_from_token')
    def test_conversation_history_preserves_metadata(self, mock_auth, client):
        """Test that conversation history includes message metadata (sources)"""
        mock_auth.return_value = {"id": "user123", "email": "test@example.com"}
        
        # Mock conversation with sources metadata
        mock_messages = [
            {
                "id": "msg1",
                "role": "user", 
                "content": "Show me J1 League standings",
                "created_at": "2025-08-30T12:00:00Z",
                "metadata": {}
            },
            {
                "id": "msg2",
                "role": "assistant",
                "content": "Here are the standings from https://jleague.jp",
                "created_at": "2025-08-30T12:00:01Z",
                "metadata": {
                    "sources": [
                        {
                            "url": "https://jleague.jp", 
                            "site": "jleague.jp",
                            "favicon": "https://www.google.com/s2/favicons?domain=jleague.jp&sz=64"
                        }
                    ]
                }
            }
        ]
        
        with patch('app.services.chat_service.EnhancedChatService.get_conversation_history') as mock_history, \
             patch('app.services.chat_service.EnhancedChatService.get_conversation_list') as mock_list:
            
            mock_history.return_value = mock_messages
            mock_list.return_value = [{"id": "conv123", "title": "Test Conversation"}]
            
            response = client.get(
                "/api/v1/chat/conversations/conv123",
                headers={"Authorization": "Bearer valid-token"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify conversation structure
            assert "conversation" in data
            assert "messages" in data
            
            messages = data["messages"]
            assert len(messages) == 2
            
            # Find assistant message
            assistant_msg = next(msg for msg in messages if msg["role"] == "assistant")
            
            # THIS is what would have failed before our fix!
            assert "metadata" in assistant_msg
            assert "sources" in assistant_msg["metadata"]
            assert len(assistant_msg["metadata"]["sources"]) > 0
            
            # Verify source structure matches frontend expectations
            source = assistant_msg["metadata"]["sources"][0]
            assert "url" in source
            assert "site" in source  
            assert "favicon" in source

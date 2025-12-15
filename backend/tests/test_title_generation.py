import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.api.v1.chat import generate_title_background

@pytest.mark.asyncio
async def test_generate_title_background_success():
    """Test successful title generation and update"""
    
    # Mock LLM and response
    mock_llm = AsyncMock()
    mock_response = MagicMock()
    mock_response.text = '"J1 League Analysis"'
    mock_llm.acomplete.return_value = mock_response

    # Mock dependencies
    with patch('app.api.v1.chat.llm_factory') as mock_factory, \
         patch('app.api.v1.chat.ConversationService') as mock_service, \
         patch('asyncio.sleep', new_callable=AsyncMock):  # Skip sleep
        
        mock_factory.create_llm.return_value = mock_llm
        
        # Execute
        await generate_title_background(
            conversation_id="test-123",
            user_message="Tell me about J1 League top scorers"
        )
        
        # Verify LLM call
        mock_factory.create_llm.assert_called_with("gpt-4o-mini", temperature=0.5)
        mock_llm.acomplete.assert_called_once()
        
        # Verify DB update
        mock_service.update_conversation_title.assert_called_with(
            "test-123", 
            "J1 League Analysis"
        )

@pytest.mark.asyncio
async def test_generate_title_background_long_title_truncation():
    """Test that long titles are truncated"""
    
    mock_llm = AsyncMock()
    mock_response = MagicMock()
    # 60 chars title
    long_title = "This is a very long title that definitely exceeds the fifty character limit set in the code"
    mock_response.text = long_title
    mock_llm.acomplete.return_value = mock_response

    with patch('app.api.v1.chat.llm_factory') as mock_factory, \
         patch('app.api.v1.chat.ConversationService') as mock_service, \
         patch('asyncio.sleep', new_callable=AsyncMock):
        
        mock_factory.create_llm.return_value = mock_llm
        
        await generate_title_background("test-123", "msg")
        
        # Verify truncation (first 47 chars + ...)
        expected_title = long_title[:47] + "..."
        mock_service.update_conversation_title.assert_called_with("test-123", expected_title)

@pytest.mark.asyncio
async def test_generate_title_background_error_handling():
    """Test error handling during generation"""
    
    mock_llm = AsyncMock()
    mock_llm.acomplete.side_effect = Exception("LLM Error")

    with patch('app.api.v1.chat.llm_factory') as mock_factory, \
         patch('app.api.v1.chat.ConversationService') as mock_service, \
         patch('asyncio.sleep', new_callable=AsyncMock):
        
        mock_factory.create_llm.return_value = mock_llm
        
        # Should not raise exception (logged only)
        await generate_title_background("test-123", "msg")
        
        # Verify NO DB update
        mock_service.update_conversation_title.assert_not_called()

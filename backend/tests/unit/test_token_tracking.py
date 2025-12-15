import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.llamaindex.workflows.unified_workflow import UnifiedWorkflow, UnifiedWorkflowInput, UnifiedWorkflowOutput
from app.llamaindex.services.llm_factory import LLMFactory

@pytest.mark.asyncio
async def test_token_tracking_in_workflow():
    # Mock dependencies
    mock_db_pool = AsyncMock()
    mock_memory_manager = AsyncMock()
    
    # Mock LLM Factory and LLM
    mock_llm = MagicMock()
    mock_llm.metadata.model_name = "gpt-4o"
    
    # Mock TokenCountingHandler
    with patch("app.llamaindex.workflows.unified_workflow.TokenCountingHandler") as MockTokenHandler:
        mock_handler_instance = MockTokenHandler.return_value
        mock_handler_instance.prompt_llm_token_count = 100
        mock_handler_instance.completion_llm_token_count = 50
        mock_handler_instance.total_llm_token_count = 150
        
        # Mock LLM Factory creation
        with patch("app.llamaindex.workflows.unified_workflow.llm_factory") as mock_factory:
            mock_factory.create_llm.return_value = mock_llm
            
            # Initialize workflow
            workflow = UnifiedWorkflow(db_pool=mock_db_pool, memory_manager=mock_memory_manager)
            
            # Mock context and store
            mock_ctx = AsyncMock()
            mock_ctx.store.get.side_effect = lambda key: {
                "workflow_input": UnifiedWorkflowInput(
                    user_id="user1", 
                    conversation_id="conv1", 
                    message="hello"
                ),
                "workflow_context": MagicMock(),
                "user_memory": AsyncMock(),
                "conversation_memory": AsyncMock(),
                "tools": [],
                "web_search_sources": [],
                "response_text": "Hello world",
                "model_used": "gpt-4o",
                "tools_used": [],
                "reasoning_steps": [],
                "tokens_used": {"prompt": 100, "completion": 50, "total": 150} # Pre-populate for save_and_respond test
            }.get(key)

            # Test save_and_respond step (where output is constructed)
            # We skip execute_agent because it's complex to mock all internal logic, 
            # but we verify that save_and_respond correctly picks up the tokens_used from store
            
            # Create a dummy event
            mock_event = MagicMock()
            
            # Run step
            result_event = await workflow.save_and_respond(mock_ctx, mock_event)
            
            # Verify output
            output = result_event.result
            assert isinstance(output, UnifiedWorkflowOutput)
            assert output.tokens_used == {"prompt": 100, "completion": 50, "total": 150}

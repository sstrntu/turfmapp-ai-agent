"""
Comprehensive tests for master_agent.py - Intelligent conversation orchestration and response generation
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import json
import asyncio
from typing import Dict, Any, List

# Import the service to test
from app.services.master_agent import MasterAgent, master_agent


class TestMasterAgent:
    """Test suite for MasterAgent initialization and basic functionality"""

    def test_master_agent_initialization(self):
        """Test MasterAgent initializes correctly"""
        agent = MasterAgent()
        assert hasattr(agent, 'conversation_memory')
        assert isinstance(agent.conversation_memory, dict)

    def test_global_instance_exists(self):
        """Test that global master_agent instance exists"""
        assert master_agent is not None
        assert isinstance(master_agent, MasterAgent)


class TestProcessUserRequest:
    """Test suite for process_user_request method"""

    @pytest.fixture
    def mock_agent(self):
        """Create a MasterAgent with mocked dependencies"""
        agent = MasterAgent()
        
        # Mock all the imported services to avoid circular import issues
        with patch.multiple(
            'app.services.master_agent',
            intelligent_classifier=Mock(),
            tool_analytics=Mock(),
            response_evaluator=Mock(),
            EnhancedChatService=Mock(),
        ):
            yield agent

    @pytest.fixture
    def sample_conversation_history(self):
        """Sample conversation history for testing"""
        return [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there! How can I help you?"},
            {"role": "user", "content": "Tell me about the weather"}
        ]

    @pytest.fixture
    def mock_mcp_client(self):
        """Mock MCP client"""
        client = Mock()
        client.call_tool = AsyncMock(return_value={"success": True, "response": "Tool result"})
        return client

    @pytest.fixture
    def mock_user_settings(self):
        """Mock user settings"""
        settings = Mock()
        settings.tool_preferences = Mock()
        settings.tool_preferences.auto_tool_usage = True
        settings.tool_preferences.enable_gmail_tools = True
        settings.tool_preferences.enable_drive_tools = True
        settings.tool_preferences.enable_calendar_tools = True
        settings.tool_preferences.max_tools_per_query = 3
        settings.tool_preferences.preferred_approach = "balanced"
        return settings

    @pytest.mark.asyncio
    async def test_process_user_request_auto_tools_disabled(self, mock_agent):
        """Test behavior when auto tool usage is disabled"""
        with patch.object(mock_agent, '_get_user_settings') as mock_settings:
            mock_settings.return_value.tool_preferences.auto_tool_usage = False
            
            result = await mock_agent.process_user_request(
                "Test message", [], "user123", Mock()
            )
            
            assert result["success"] is False
            assert result["approach"] == "user_disabled_tools"
            assert result["classification"]["classification"] == "USER_DISABLED"
            assert result["tools_used"] == []

    @pytest.mark.asyncio
    async def test_process_user_request_general_knowledge(self, mock_agent, sample_conversation_history, mock_mcp_client, mock_user_settings):
        """Test general knowledge classification and processing"""
        
        # Mock the dependencies
        mock_classifier = AsyncMock()
        mock_classifier.classify_request.return_value = {
            "classification": "GENERAL_KNOWLEDGE",
            "confidence": 0.9,
            "tier_used": 1,
            "reasoning": "This is a general knowledge question",
            "suggested_tools": []
        }
        
        mock_chat_service = Mock()
        mock_chat_service.call_responses_api = AsyncMock(return_value={
            "content": "This is a general knowledge response",
            "tool_calls": []
        })
        
        with patch.object(mock_agent, '_get_user_settings', return_value=mock_user_settings), \
             patch('app.services.master_agent.intelligent_classifier', mock_classifier), \
             patch('app.services.master_agent.EnhancedChatService', return_value=mock_chat_service), \
             patch.object(mock_agent, '_evaluate_and_learn', new_callable=AsyncMock):
            
            result = await mock_agent.process_user_request(
                "What is the capital of France?", 
                sample_conversation_history, 
                "user123", 
                mock_mcp_client
            )
            
            assert result["success"] is True
            assert result["approach"] == "general_knowledge_with_responses_api"
            assert result["classification"]["classification"] == "GENERAL_KNOWLEDGE"
            assert "This is a general knowledge response" in result["response"]

    @pytest.mark.asyncio
    async def test_process_user_request_current_info(self, mock_agent, sample_conversation_history, mock_mcp_client, mock_user_settings):
        """Test current information classification and processing"""
        
        mock_classifier = AsyncMock()
        mock_classifier.classify_request.return_value = {
            "classification": "CURRENT_INFO",
            "confidence": 0.85,
            "tier_used": 1,
            "reasoning": "User wants current information",
            "suggested_tools": ["web_search"]
        }
        
        mock_chat_service = Mock()
        mock_chat_service.call_responses_api = AsyncMock(return_value={
            "content": "Current information response with web search",
            "tool_calls": [{"name": "web_search"}]
        })
        
        with patch.object(mock_agent, '_get_user_settings', return_value=mock_user_settings), \
             patch('app.services.master_agent.intelligent_classifier', mock_classifier), \
             patch('app.services.master_agent.EnhancedChatService', return_value=mock_chat_service), \
             patch.object(mock_agent, '_evaluate_and_learn', new_callable=AsyncMock):
            
            result = await mock_agent.process_user_request(
                "What's the weather today?", 
                sample_conversation_history, 
                "user123", 
                mock_mcp_client
            )
            
            assert result["success"] is True
            assert result["approach"] == "responses_api_with_web_search"
            assert result["tools_used"] == ["web_search"]

    @pytest.mark.asyncio
    async def test_process_user_request_personal_data(self, mock_agent, sample_conversation_history, mock_mcp_client, mock_user_settings):
        """Test personal data classification and tool execution"""
        
        mock_classifier = AsyncMock()
        mock_classifier.classify_request.return_value = {
            "classification": "PERSONAL_DATA",
            "confidence": 0.9,
            "tier_used": 1,
            "reasoning": "User wants personal data",
            "suggested_tools": ["gmail_search", "gmail_recent"]
        }
        
        with patch.object(mock_agent, '_get_user_settings', return_value=mock_user_settings), \
             patch('app.services.master_agent.intelligent_classifier', mock_classifier), \
             patch.object(mock_agent, '_execute_tool_based_request', new_callable=AsyncMock, return_value="Tool execution response"), \
             patch.object(mock_agent, '_evaluate_and_learn', new_callable=AsyncMock):
            
            result = await mock_agent.process_user_request(
                "Show me my recent emails", 
                sample_conversation_history, 
                "user123", 
                mock_mcp_client
            )
            
            assert result["success"] is True
            assert result["approach"] == "tool_based"
            assert result["response"] == "Tool execution response"
            assert "gmail_search" in result["tools_used"]

    @pytest.mark.asyncio
    async def test_process_user_request_context_dependent(self, mock_agent, sample_conversation_history, mock_mcp_client, mock_user_settings):
        """Test context-dependent classification and processing"""
        
        mock_classifier = AsyncMock()
        mock_classifier.classify_request.return_value = {
            "classification": "CONTEXT_DEPENDENT",
            "confidence": 0.7,
            "tier_used": 2,
            "reasoning": "Needs context analysis",
            "suggested_tools": []
        }
        
        # Mock context analysis to return existing data
        with patch.object(mock_agent, '_get_user_settings', return_value=mock_user_settings), \
             patch('app.services.master_agent.intelligent_classifier', mock_classifier), \
             patch.object(mock_agent, '_analyze_conversation_context', return_value="Has recent email data"), \
             patch.object(mock_agent, '_answer_from_existing_context', new_callable=AsyncMock, return_value="Context-based response"), \
             patch.object(mock_agent, '_evaluate_and_learn', new_callable=AsyncMock):
            
            result = await mock_agent.process_user_request(
                "What are they about?", 
                sample_conversation_history, 
                "user123", 
                mock_mcp_client
            )
            
            assert result["success"] is True
            assert result["approach"] == "context_analysis"
            assert result["response"] == "Context-based response"
            assert result["tools_used"] == []

    @pytest.mark.asyncio
    async def test_process_user_request_ambiguous(self, mock_agent, sample_conversation_history, mock_mcp_client, mock_user_settings):
        """Test ambiguous classification requiring comprehensive analysis"""
        
        mock_classifier = AsyncMock()
        mock_classifier.classify_request.return_value = {
            "classification": "AMBIGUOUS",
            "confidence": 0.5,
            "tier_used": 3,
            "reasoning": "Needs comprehensive analysis",
            "suggested_tools": []
        }
        
        with patch.object(mock_agent, '_get_user_settings', return_value=mock_user_settings), \
             patch('app.services.master_agent.intelligent_classifier', mock_classifier), \
             patch.object(mock_agent, '_intelligent_tool_planning_and_execution', new_callable=AsyncMock, return_value={
                 "success": True,
                 "response": "Comprehensive analysis response",
                 "approach": "llm_analysis_with_tools",
                 "classification": {"classification": "PERSONAL_DATA", "confidence": 0.7},
                 "tools_used": ["gmail_search"]
             }):
            
            result = await mock_agent.process_user_request(
                "What should I do?", 
                sample_conversation_history, 
                "user123", 
                mock_mcp_client
            )
            
            assert result["success"] is True
            assert result["approach"] == "llm_analysis_with_tools"
            assert result["response"] == "Comprehensive analysis response"


class TestToolExecution:
    """Test suite for tool execution methods"""

    @pytest.fixture
    def mock_agent(self):
        return MasterAgent()

    @pytest.fixture
    def mock_mcp_client(self):
        client = Mock()
        client.call_tool = AsyncMock(return_value={"success": True, "response": "Tool result"})
        return client

    @pytest.mark.asyncio
    async def test_execute_tool_based_request(self, mock_agent, mock_mcp_client):
        """Test tool-based request execution"""
        
        with patch.object(mock_agent, '_extract_tool_parameters', return_value={"query": "test", "max_results": 5}), \
             patch.object(mock_agent, '_synthesize_tool_results', new_callable=AsyncMock, return_value="Synthesized response"):
            
            result = await mock_agent._execute_tool_based_request(
                "Show me emails about project X",
                [],
                "user123",
                mock_mcp_client,
                ["gmail_search"]
            )
            
            assert result == "Synthesized response"
            mock_mcp_client.call_tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_tool_based_request_with_error(self, mock_agent):
        """Test tool execution with error handling"""
        
        mock_mcp_client = Mock()
        mock_mcp_client.call_tool = AsyncMock(side_effect=Exception("Tool failed"))
        
        with patch.object(mock_agent, '_extract_tool_parameters', return_value={}), \
             patch.object(mock_agent, '_synthesize_tool_results', new_callable=AsyncMock, return_value="Error response"):
            
            result = await mock_agent._execute_tool_based_request(
                "Test message", [], "user123", mock_mcp_client, ["gmail_search"]
            )
            
            assert result == "Error response"

    def test_extract_tool_parameters_gmail(self, mock_agent):
        """Test parameter extraction for Gmail tools"""
        
        # Test recent emails
        params = mock_agent._extract_tool_parameters("Show me recent emails", "gmail_recent")
        assert params["max_results"] == 5
        
        # Test search query extraction
        with patch.object(mock_agent, '_extract_smart_search_query', return_value="project X"):
            params = mock_agent._extract_tool_parameters("Find emails about project X", "gmail_search")
            assert params["query"] == "project X"
            assert params["max_results"] == 5

    def test_extract_tool_parameters_drive(self, mock_agent):
        """Test parameter extraction for Drive tools"""
        params = mock_agent._extract_tool_parameters("List my files", "drive_list_files")
        assert params["max_results"] == 10

    def test_extract_tool_parameters_calendar(self, mock_agent):
        """Test parameter extraction for Calendar tools"""
        # Test upcoming events
        params = mock_agent._extract_tool_parameters("Show upcoming meetings", "calendar_upcoming")
        assert params["max_results"] == 5
        
        # Test general calendar
        params = mock_agent._extract_tool_parameters("Show my calendar", "calendar_events")
        assert params["max_results"] == 10

    @pytest.mark.asyncio
    async def test_synthesize_tool_results(self, mock_agent):
        """Test synthesis of tool results"""
        
        tool_results = [
            {
                "tool": "gmail_search",
                "success": True,
                "result": {"success": True, "response": "Email data"}
            },
            {
                "tool": "drive_list",
                "success": False,
                "result": {"success": False, "error": "No access"}
            }
        ]
        
        with patch.object(mock_agent, '_analyze_content_with_llm', new_callable=AsyncMock, return_value={
            "answer": "Analyzed response from successful tools"
        }):
            
            result = await mock_agent._synthesize_tool_results(
                "Tell me about my data", tool_results, []
            )
            
            assert "Based on your gmail_search: Analyzed response from successful tools" in result

    @pytest.mark.asyncio
    async def test_synthesize_tool_results_no_success(self, mock_agent):
        """Test synthesis when no tools succeed"""
        
        tool_results = [
            {
                "tool": "gmail_search",
                "success": False,
                "result": {"success": False, "error": "Failed"}
            }
        ]
        
        result = await mock_agent._synthesize_tool_results(
            "Tell me about my data", tool_results, []
        )
        
        assert "didn't return any useful data" in result


class TestIntelligentToolPlanning:
    """Test suite for intelligent tool planning methods"""

    @pytest.fixture
    def mock_agent(self):
        return MasterAgent()

    @pytest.mark.asyncio
    async def test_get_available_tools(self, mock_agent):
        """Test getting available tools"""
        
        mock_mcp_client = Mock()
        
        # Mock the get_all_google_tools function
        mock_tools = [
            {
                "name": "gmail_search",
                "description": "Search Gmail emails",
                "inputSchema": {"type": "object", "properties": {}}
            },
            {
                "name": "drive_list_files",
                "description": "List Google Drive files",
                "inputSchema": {"type": "object", "properties": {}}
            }
        ]
        
        with patch('app.services.master_agent.get_all_google_tools', new_callable=AsyncMock, return_value=mock_tools):
            tools = await mock_agent._get_available_tools(mock_mcp_client)
            
            assert "gmail_search" in tools
            assert "drive_list_files" in tools
            assert tools["gmail_search"]["category"] == "email"
            assert tools["drive_list_files"]["category"] == "files"

    @pytest.mark.asyncio
    async def test_get_available_tools_error_fallback(self, mock_agent):
        """Test fallback when getting tools fails"""
        
        mock_mcp_client = Mock()
        
        with patch('app.services.master_agent.get_all_google_tools', new_callable=AsyncMock, side_effect=Exception("Failed")):
            tools = await mock_agent._get_available_tools(mock_mcp_client)
            
            # Should return fallback tools
            assert "gmail_search" in tools
            assert "gmail_recent" in tools
            assert "drive_list_files" in tools

    def test_categorize_tool(self, mock_agent):
        """Test tool categorization"""
        assert mock_agent._categorize_tool("gmail_search") == "email"
        assert mock_agent._categorize_tool("drive_list_files") == "files"
        assert mock_agent._categorize_tool("calendar_events") == "calendar"
        assert mock_agent._categorize_tool("unknown_tool") == "other"

    @pytest.mark.asyncio
    async def test_intelligent_tool_planning(self, mock_agent):
        """Test intelligent tool planning with LLM analysis"""
        
        available_tools = {
            "gmail_search": {"description": "Search Gmail", "category": "email"}
        }
        
        # Mock successful LLM analysis
        mock_llm_result = {
            "needs_tools": True,
            "reasoning": "User wants personal email data",
            "tool_sequence": [
                {
                    "tool": "gmail_search",
                    "params": {"query": "project", "max_results": 5},
                    "purpose": "Find relevant emails"
                }
            ],
            "expected_outcome": "Email data to answer question"
        }
        
        with patch.object(mock_agent, '_analyze_conversation_context', return_value="No recent data context"), \
             patch.object(mock_agent, '_analyze_content_with_llm', new_callable=AsyncMock, return_value=mock_llm_result):
            
            plan = await mock_agent._intelligent_tool_planning(
                "Find emails about the project",
                [],
                available_tools
            )
            
            assert plan["needs_tools"] is True
            assert len(plan["tool_sequence"]) == 1
            assert plan["tool_sequence"][0]["tool"] == "gmail_search"

    @pytest.mark.asyncio
    async def test_intelligent_tool_planning_fallback(self, mock_agent):
        """Test fallback to basic planning when LLM fails"""
        
        available_tools = {
            "gmail_search": {"description": "Search Gmail", "category": "email"}
        }
        
        with patch.object(mock_agent, '_analyze_conversation_context', return_value="No context"), \
             patch.object(mock_agent, '_analyze_content_with_llm', new_callable=AsyncMock, return_value=None), \
             patch.object(mock_agent, '_basic_tool_planning', return_value={"needs_tools": False}):
            
            plan = await mock_agent._intelligent_tool_planning(
                "What is the weather?",
                [],
                available_tools
            )
            
            assert plan["needs_tools"] is False

    def test_basic_tool_planning_general_knowledge(self, mock_agent):
        """Test basic tool planning for general knowledge questions"""
        
        plan = mock_agent._basic_tool_planning(
            "Who is the president of the United States?",
            "No context",
            {}
        )
        
        assert plan["needs_tools"] is False
        assert "general knowledge" in plan["reasoning"].lower()

    def test_basic_tool_planning_email_request(self, mock_agent):
        """Test basic tool planning for email requests"""
        
        with patch.object(mock_agent, '_extract_smart_search_query', return_value="project"):
            plan = mock_agent._basic_tool_planning(
                "Show me my emails about the project",
                "No context",
                {"gmail_search": {"description": "Search Gmail", "category": "email"}}
            )
            
            assert plan["needs_tools"] is True
            assert plan["tool_sequence"][0]["tool"] == "gmail_search"
            assert plan["tool_sequence"][0]["params"]["query"] == "project"


class TestSearchQueryExtraction:
    """Test suite for search query extraction"""

    @pytest.fixture
    def mock_agent(self):
        return MasterAgent()

    def test_extract_smart_search_query_basic_patterns(self, mock_agent):
        """Test basic search query patterns"""
        
        # Test "comments for" pattern
        query = mock_agent._extract_smart_search_query("Show me comments for Made in J.League ep3")
        assert query == "J.League"
        
        # Test "about" pattern
        query = mock_agent._extract_smart_search_query("Find emails about project alpha")
        assert query == "project alpha"
        
        # Test "regarding" pattern
        query = mock_agent._extract_smart_search_query("Show emails regarding the contract")
        assert query == "the contract"

    def test_extract_smart_search_query_episode_cleanup(self, mock_agent):
        """Test cleanup of episode references"""
        
        query = mock_agent._extract_smart_search_query("Comments for project X ep5")
        assert "ep5" not in query
        assert "episode 5" not in query

    def test_extract_smart_search_query_fallback_terms(self, mock_agent):
        """Test fallback to key term extraction"""
        
        # Test J.League extraction
        query = mock_agent._extract_smart_search_query("Tell me about J.League stuff")
        assert query == "J.League"
        
        # Test frame.io extraction
        query = mock_agent._extract_smart_search_query("Any frame.io updates?")
        assert query == "frame.io"
        
        # Test Jubilo extraction
        query = mock_agent._extract_smart_search_query("What about Jubilo?")
        assert query == "Jubilo"
        
        # Test multiple terms with OR
        query = mock_agent._extract_smart_search_query("J.League and frame.io updates")
        assert "J.League" in query and "frame.io" in query and "OR" in query

    def test_extract_smart_search_query_no_match(self, mock_agent):
        """Test when no patterns match"""
        
        query = mock_agent._extract_smart_search_query("Random message with no keywords")
        assert query == ""


class TestContextAnalysis:
    """Test suite for conversation context analysis"""

    @pytest.fixture
    def mock_agent(self):
        return MasterAgent()

    def test_analyze_conversation_context_email_data(self, mock_agent):
        """Test context analysis with email data"""
        
        history = [
            {"role": "assistant", "content": "Here are your recent emails from Gmail..."},
            {"role": "user", "content": "What about Jubilo?"}
        ]
        
        context = mock_agent._analyze_conversation_context(history)
        assert "Has recent email data" in context
        assert "Jubilo email discussions" in context

    def test_analyze_conversation_context_drive_data(self, mock_agent):
        """Test context analysis with Drive data"""
        
        history = [
            {"role": "assistant", "content": "Here are your Google Drive files..."}
        ]
        
        context = mock_agent._analyze_conversation_context(history)
        assert "Has recent Drive data" in context

    def test_analyze_conversation_context_calendar_data(self, mock_agent):
        """Test context analysis with calendar data"""
        
        history = [
            {"role": "assistant", "content": "Here are your upcoming calendar events..."}
        ]
        
        context = mock_agent._analyze_conversation_context(history)
        assert "Has recent Calendar data" in context

    def test_analyze_conversation_context_user_clarification(self, mock_agent):
        """Test detection of user clarification requests"""
        
        history = [
            {"role": "user", "content": "what are they?"}
        ]
        
        context = mock_agent._analyze_conversation_context(history)
        assert "User asking for clarification" in context

    def test_analyze_conversation_context_specific_topics(self, mock_agent):
        """Test detection of specific topics"""
        
        history = [
            {"role": "assistant", "content": "I found comments about Made in J.League episode..."},
            {"role": "user", "content": "Tell me about frame.io comments"}
        ]
        
        context = mock_agent._analyze_conversation_context(history)
        assert "Made in J.League episode content" in context
        assert "User mentioned Frame.io" in context

    def test_analyze_conversation_context_no_context(self, mock_agent):
        """Test when no relevant context is found"""
        
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        
        context = mock_agent._analyze_conversation_context(history)
        assert context == "No recent data context"


class TestResponseAnalysis:
    """Test suite for response analysis and synthesis"""

    @pytest.fixture
    def mock_agent(self):
        return MasterAgent()

    @pytest.mark.asyncio
    async def test_answer_from_existing_context_pronoun_question(self, mock_agent):
        """Test answering pronoun questions from existing context"""
        
        history = [
            {"role": "assistant", "content": "I found several Frame.io comments about your video project"},
            {"role": "user", "content": "what are they?"}
        ]
        
        mock_analysis_result = {
            "answer": "The Frame.io comments are feedback on your video project..."
        }
        
        with patch.object(mock_agent, '_analyze_content_with_llm', new_callable=AsyncMock, return_value=mock_analysis_result):
            result = await mock_agent._answer_from_existing_context("what are they?", history)
            assert result == mock_analysis_result["answer"]

    @pytest.mark.asyncio
    async def test_answer_from_existing_context_no_context(self, mock_agent):
        """Test when no relevant context exists"""
        
        history = []
        
        result = await mock_agent._answer_from_existing_context("What are they?", history)
        assert "don't have enough context" in result

    @pytest.mark.asyncio
    async def test_analyze_and_synthesize_response(self, mock_agent):
        """Test analysis and synthesis of tool results"""
        
        tool_results = [
            {
                "tool": "gmail_search",
                "result": {"success": True, "response": "Email data about project"}
            }
        ]
        
        mock_analysis = {
            "answer": "Based on the emails, the project status is...",
            "confidence": "high",
            "date_validation": "valid"
        }
        
        with patch.object(mock_agent, '_analyze_content_with_llm', new_callable=AsyncMock, return_value=mock_analysis):
            result = await mock_agent._analyze_and_synthesize_response(
                "What's the project status?", tool_results, []
            )
            
            assert "Based on the data I gathered using gmail_search:" in result
            assert mock_analysis["answer"] in result

    @pytest.mark.asyncio
    async def test_analyze_and_synthesize_response_no_results(self, mock_agent):
        """Test synthesis when no tool results are successful"""
        
        tool_results = [
            {
                "tool": "gmail_search",
                "result": {"success": False, "error": "No access"}
            }
        ]
        
        result = await mock_agent._analyze_and_synthesize_response(
            "What's my status?", tool_results, []
        )
        
        assert "didn't return any useful data" in result

    @pytest.mark.asyncio
    async def test_analyze_and_synthesize_response_outdated_data(self, mock_agent):
        """Test handling of outdated data"""
        
        tool_results = [
            {
                "tool": "calendar_events",
                "result": {"success": True, "response": "Calendar data"}
            }
        ]
        
        mock_analysis = {
            "answer": "Found calendar events",
            "date_validation": "outdated - events are from last month"
        }
        
        with patch.object(mock_agent, '_analyze_content_with_llm', new_callable=AsyncMock, return_value=mock_analysis):
            result = await mock_agent._analyze_and_synthesize_response(
                "What's my next meeting?", tool_results, []
            )
            
            assert "appears to be outdated" in result
            assert "check your calendar for more recent events" in result


class TestLLMAnalysis:
    """Test suite for LLM analysis methods"""

    @pytest.fixture
    def mock_agent(self):
        return MasterAgent()

    @pytest.mark.asyncio
    async def test_analyze_content_with_llm_action_extraction(self, mock_agent):
        """Test LLM analysis for action extraction"""
        
        mock_response = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "actions": [
                            {
                                "action": "Review contract",
                                "details": "Review the partnership agreement",
                                "priority": "high",
                                "deadline": "2025-01-15"
                            }
                        ],
                        "summary": "Contract review required"
                    })
                }
            }]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=Mock(status_code=200, json=Mock(return_value=mock_response))
            )
            
            with patch('os.getenv', return_value='test-api-key'):
                result = await mock_agent._analyze_content_with_llm(
                    "Email content about contract",
                    "action_extraction",
                    "What do I need to do?"
                )
                
                assert "actions" in result
                assert len(result["actions"]) == 1
                assert result["actions"][0]["action"] == "Review contract"
                assert result["actions"][0]["priority"] == "high"

    @pytest.mark.asyncio
    async def test_analyze_content_with_llm_question_answering(self, mock_agent):
        """Test LLM analysis for question answering"""
        
        mock_response = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "answer": "The project status is on track",
                        "confidence": "high",
                        "key_points": ["Milestone 1 completed", "On schedule"],
                        "date_validation": "valid"
                    })
                }
            }]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=Mock(status_code=200, json=Mock(return_value=mock_response))
            )
            
            with patch('os.getenv', return_value='test-api-key'):
                result = await mock_agent._analyze_content_with_llm(
                    "Project status email",
                    "question_answering",
                    "What's the project status?"
                )
                
                assert result["answer"] == "The project status is on track"
                assert result["confidence"] == "high"
                assert "Milestone 1 completed" in result["key_points"]

    @pytest.mark.asyncio
    async def test_analyze_content_with_llm_no_api_key(self, mock_agent):
        """Test LLM analysis when API key is missing"""
        
        with patch('os.getenv', return_value=None):
            result = await mock_agent._analyze_content_with_llm(
                "Content",
                "action_extraction",
                "Question"
            )
            
            assert result == {}

    @pytest.mark.asyncio
    async def test_analyze_content_with_llm_api_error(self, mock_agent):
        """Test LLM analysis with API error"""
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=Mock(status_code=500, text="Server error")
            )
            
            with patch('os.getenv', return_value='test-api-key'):
                result = await mock_agent._analyze_content_with_llm(
                    "Content",
                    "action_extraction",
                    "Question"
                )
                
                assert result == {}

    @pytest.mark.asyncio
    async def test_analyze_content_with_llm_json_parse_error(self, mock_agent):
        """Test LLM analysis with JSON parsing error"""
        
        mock_response = {
            "choices": [{
                "message": {
                    "content": "Invalid JSON response that cannot be parsed"
                }
            }]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=Mock(status_code=200, json=Mock(return_value=mock_response))
            )
            
            with patch('os.getenv', return_value='test-api-key'):
                result = await mock_agent._analyze_content_with_llm(
                    "Content",
                    "action_extraction",
                    "Question"
                )
                
                assert "raw_analysis" in result
                assert result["raw_analysis"] == "Invalid JSON response that cannot be parsed"

    @pytest.mark.asyncio
    async def test_analyze_content_with_llm_markdown_cleanup(self, mock_agent):
        """Test cleanup of markdown formatting in LLM responses"""
        
        mock_response = {
            "choices": [{
                "message": {
                    "content": '```json\n{"answer": "Test response"}\n```'
                }
            }]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=Mock(status_code=200, json=Mock(return_value=mock_response))
            )
            
            with patch('os.getenv', return_value='test-api-key'):
                result = await mock_agent._analyze_content_with_llm(
                    "Content",
                    "question_answering",
                    "Question"
                )
                
                assert result["answer"] == "Test response"


class TestUserSettingsAndPreferences:
    """Test suite for user settings and preferences"""

    @pytest.fixture
    def mock_agent(self):
        return MasterAgent()

    def test_get_user_settings_success(self, mock_agent):
        """Test successful user settings retrieval"""
        
        mock_settings = Mock()
        mock_settings.tool_preferences.auto_tool_usage = True
        
        with patch('app.services.master_agent.get_user_agent_settings', return_value=mock_settings):
            settings = mock_agent._get_user_settings("user123")
            assert settings.tool_preferences.auto_tool_usage is True

    def test_get_user_settings_error_fallback(self, mock_agent):
        """Test fallback to default settings when retrieval fails"""
        
        with patch('app.services.master_agent.get_user_agent_settings', side_effect=Exception("Failed")):
            settings = mock_agent._get_user_settings("user123")
            
            # Should return default settings
            assert hasattr(settings, 'tool_preferences')
            assert hasattr(settings, 'analytics_enabled')

    def test_filter_tools_by_preferences_gmail_disabled(self, mock_agent):
        """Test filtering when Gmail tools are disabled"""
        
        mock_settings = Mock()
        mock_settings.tool_preferences.enable_gmail_tools = False
        mock_settings.tool_preferences.enable_drive_tools = True
        mock_settings.tool_preferences.enable_calendar_tools = True
        mock_settings.tool_preferences.preferred_approach = "balanced"
        
        suggested_tools = ["gmail_search", "drive_list_files", "calendar_events"]
        filtered = mock_agent._filter_tools_by_preferences(suggested_tools, mock_settings)
        
        assert "gmail_search" not in filtered
        assert "drive_list_files" in filtered
        assert "calendar_events" in filtered

    def test_filter_tools_by_preferences_conservative_approach(self, mock_agent):
        """Test conservative approach that limits to one tool"""
        
        mock_settings = Mock()
        mock_settings.tool_preferences.enable_gmail_tools = True
        mock_settings.tool_preferences.enable_drive_tools = True
        mock_settings.tool_preferences.enable_calendar_tools = True
        mock_settings.tool_preferences.preferred_approach = "conservative"
        
        suggested_tools = ["gmail_search", "drive_list_files", "calendar_events"]
        filtered = mock_agent._filter_tools_by_preferences(suggested_tools, mock_settings)
        
        assert len(filtered) == 1
        assert filtered[0] == "gmail_search"  # First tool

    def test_filter_tools_by_preferences_aggressive_approach(self, mock_agent):
        """Test aggressive approach that uses all allowed tools"""
        
        mock_settings = Mock()
        mock_settings.tool_preferences.enable_gmail_tools = True
        mock_settings.tool_preferences.enable_drive_tools = True
        mock_settings.tool_preferences.enable_calendar_tools = True
        mock_settings.tool_preferences.preferred_approach = "aggressive"
        
        suggested_tools = ["gmail_search", "drive_list_files", "calendar_events"]
        filtered = mock_agent._filter_tools_by_preferences(suggested_tools, mock_settings)
        
        assert len(filtered) == 3
        assert set(filtered) == set(suggested_tools)


class TestDirectLLMResponse:
    """Test suite for direct LLM response methods"""

    @pytest.fixture
    def mock_agent(self):
        return MasterAgent()

    @pytest.mark.asyncio
    async def test_answer_with_llm_only(self, mock_agent):
        """Test direct LLM answer without tools"""
        
        mock_response = {
            "choices": [{
                "message": {
                    "content": "The capital of France is Paris."
                }
            }]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=Mock(status_code=200, json=Mock(return_value=mock_response))
            )
            
            with patch('os.getenv', return_value='test-api-key'):
                result = await mock_agent._answer_with_llm_only(
                    "What is the capital of France?",
                    [{"role": "user", "content": "Hello"}]
                )
                
                assert result == "The capital of France is Paris."

    @pytest.mark.asyncio
    async def test_answer_with_llm_only_no_api_key(self, mock_agent):
        """Test direct LLM answer when API key is missing"""
        
        with patch('os.getenv', return_value=None):
            result = await mock_agent._answer_with_llm_only("Question", [])
            assert "not able to access my knowledge base" in result

    @pytest.mark.asyncio
    async def test_answer_with_llm_only_api_error(self, mock_agent):
        """Test direct LLM answer with API error"""
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=Mock(status_code=500)
            )
            
            with patch('os.getenv', return_value='test-api-key'):
                result = await mock_agent._answer_with_llm_only("Question", [])
                assert "having trouble accessing" in result


class TestAsyncEvaluationAndLearning:
    """Test suite for evaluation and learning methods"""

    @pytest.fixture
    def mock_agent(self):
        return MasterAgent()

    @pytest.mark.asyncio
    async def test_evaluate_and_learn(self, mock_agent):
        """Test response evaluation and learning process"""
        
        mock_evaluator = Mock()
        mock_evaluator.evaluate_response_quality = AsyncMock(return_value={
            "evaluation": "good",
            "quality_score": 0.8
        })
        mock_evaluator.suggest_better_approach = AsyncMock(return_value={})
        
        mock_analytics = Mock()
        mock_analytics.log_approach_effectiveness = Mock()
        mock_analytics.log_tool_usage = Mock()
        mock_analytics.log_classification_result = Mock()
        
        with patch('app.services.master_agent.response_evaluator', mock_evaluator), \
             patch('app.services.master_agent.tool_analytics', mock_analytics):
            
            await mock_agent._evaluate_and_learn(
                "Test question",
                "Test response",
                "tool_based",
                ["gmail_search"],
                1234567890.0,
                "user123",
                {"classification": "PERSONAL_DATA", "confidence": 0.9}
            )
            
            mock_evaluator.evaluate_response_quality.assert_called_once()
            mock_analytics.log_approach_effectiveness.assert_called_once()
            mock_analytics.log_tool_usage.assert_called_once()

    @pytest.mark.asyncio
    async def test_evaluate_and_learn_poor_quality(self, mock_agent):
        """Test evaluation for poor quality responses"""
        
        mock_evaluator = Mock()
        mock_evaluator.evaluate_response_quality = AsyncMock(return_value={
            "evaluation": "poor",
            "quality_score": 0.3
        })
        mock_evaluator.suggest_better_approach = AsyncMock(return_value={
            "alternative_approach": "general_knowledge",
            "reasoning": "Should use direct knowledge instead"
        })
        
        mock_analytics = Mock()
        mock_analytics.log_approach_effectiveness = Mock()
        mock_analytics.log_classification_result = Mock()
        
        with patch('app.services.master_agent.response_evaluator', mock_evaluator), \
             patch('app.services.master_agent.tool_analytics', mock_analytics):
            
            await mock_agent._evaluate_and_learn(
                "Test question",
                "Poor response",
                "tool_based",
                [],
                1234567890.0,
                "user123",
                {"classification": "GENERAL_KNOWLEDGE", "confidence": 0.9}
            )
            
            mock_evaluator.suggest_better_approach.assert_called_once()

    @pytest.mark.asyncio
    async def test_evaluate_and_learn_error_handling(self, mock_agent):
        """Test error handling in evaluation process"""
        
        with patch('app.services.master_agent.response_evaluator', side_effect=Exception("Evaluation failed")):
            # Should not raise exception
            await mock_agent._evaluate_and_learn(
                "Test question", "Test response", "approach", [], 1234567890.0, "user123", {}
            )
            # Test passes if no exception is raised


class TestExecuteAndAnalyzeIteratively:
    """Test suite for iterative tool execution and analysis"""

    @pytest.fixture
    def mock_agent(self):
        return MasterAgent()

    @pytest.fixture
    def mock_mcp_client(self):
        client = Mock()
        client.call_tool = AsyncMock(return_value={"success": True, "response": "Tool result"})
        return client

    @pytest.mark.asyncio
    async def test_execute_and_analyze_iteratively_no_tools_needed(self, mock_agent):
        """Test when no tools are needed"""
        
        tool_plan = {"needs_tools": False}
        
        with patch.object(mock_agent, '_answer_from_existing_context', new_callable=AsyncMock, return_value="Context response"):
            result = await mock_agent._execute_and_analyze_iteratively(
                tool_plan, "Question", [], "user123", Mock()
            )
            
            assert result == "Context response"

    @pytest.mark.asyncio
    async def test_execute_and_analyze_iteratively_with_tools(self, mock_agent, mock_mcp_client):
        """Test iterative execution with tools"""
        
        tool_plan = {
            "needs_tools": True,
            "tool_sequence": [
                {
                    "tool": "gmail_search",
                    "params": {"query": "test"},
                    "purpose": "Find emails"
                }
            ]
        }
        
        with patch.object(mock_agent, '_resolve_dynamic_params', return_value={"query": "test", "user_id": "user123"}), \
             patch.object(mock_agent, '_analyze_and_synthesize_response', new_callable=AsyncMock, return_value="Final response"):
            
            result = await mock_agent._execute_and_analyze_iteratively(
                tool_plan, "Question", [], "user123", mock_mcp_client
            )
            
            assert result == "Final response"
            mock_mcp_client.call_tool.assert_called_once_with("gmail_search", {"query": "test", "user_id": "user123"})

    @pytest.mark.asyncio
    async def test_execute_and_analyze_iteratively_raw_analysis(self, mock_agent):
        """Test handling of raw analysis responses"""
        
        tool_plan = {
            "raw_analysis": '{"needs_tools": false, "reasoning": "No tools needed"}'
        }
        
        with patch.object(mock_agent, '_answer_from_existing_context', new_callable=AsyncMock, return_value="Context response"):
            result = await mock_agent._execute_and_analyze_iteratively(
                tool_plan, "Question", [], "user123", Mock()
            )
            
            assert result == "Context response"

    def test_resolve_dynamic_params(self, mock_agent):
        """Test resolution of dynamic parameters"""
        
        tool_params = {"message_id": "id_of_the_found_message"}
        previous_results = [
            {
                "tool": "gmail_search",
                "result": {
                    "success": True,
                    "response": "Found email with Message ID: abc123def456"
                }
            }
        ]
        
        with patch.object(mock_agent, '_extract_message_id_from_response', return_value="abc123def456"):
            resolved = mock_agent._resolve_dynamic_params(tool_params, previous_results)
            assert resolved["message_id"] == "abc123def456"

    def test_extract_message_id_from_response(self, mock_agent):
        """Test Gmail message ID extraction from response text"""
        
        # Test with explicit Message ID format
        response = "Here's your email: Message ID: abc123def456"
        message_id = mock_agent._extract_message_id_from_response(response)
        assert message_id == "abc123def456"
        
        # Test with JSON format
        response = 'Email data: {"id": "xyz789abc123", "subject": "Test"}'
        message_id = mock_agent._extract_message_id_from_response(response)
        assert message_id == "xyz789abc123"
        
        # Test with long alphanumeric string (Gmail format)
        response = "Found email thread 1a2b3c4d5e6f7g8h9i0j with subject Test"
        message_id = mock_agent._extract_message_id_from_response(response)
        assert message_id == "1a2b3c4d5e6f7g8h9i0j"
        
        # Test no match
        response = "No email IDs found in this text"
        message_id = mock_agent._extract_message_id_from_response(response)
        assert message_id is None


class TestIntelligentToolPlanningAndExecution:
    """Test suite for comprehensive intelligent tool planning and execution"""

    @pytest.fixture
    def mock_agent(self):
        return MasterAgent()

    @pytest.fixture
    def mock_mcp_client(self):
        client = Mock()
        client.call_tool = AsyncMock(return_value={"success": True, "response": "Tool result"})
        return client

    @pytest.mark.asyncio
    async def test_intelligent_tool_planning_and_execution_no_tools(self, mock_agent, mock_mcp_client):
        """Test when LLM analysis determines no tools are needed"""
        
        mock_tool_plan = {
            "needs_tools": False,
            "reasoning": "General knowledge question"
        }
        
        with patch.object(mock_agent, '_get_available_tools', new_callable=AsyncMock, return_value={}), \
             patch.object(mock_agent, '_intelligent_tool_planning', new_callable=AsyncMock, return_value=mock_tool_plan), \
             patch.object(mock_agent, '_answer_from_existing_context', new_callable=AsyncMock, return_value="Knowledge response"):
            
            result = await mock_agent._intelligent_tool_planning_and_execution(
                "What is the capital of France?", [], "user123", mock_mcp_client
            )
            
            assert result["success"] is True
            assert result["approach"] == "llm_analysis_no_tools"
            assert result["response"] == "Knowledge response"
            assert result["tools_used"] == []

    @pytest.mark.asyncio
    async def test_intelligent_tool_planning_and_execution_with_tools(self, mock_agent, mock_mcp_client):
        """Test when tools are needed and executed"""
        
        mock_tool_plan = {
            "needs_tools": True,
            "tool_sequence": [
                {"tool": "gmail_search", "params": {}, "purpose": "Find emails"}
            ]
        }
        
        with patch.object(mock_agent, '_get_available_tools', new_callable=AsyncMock, return_value={"gmail_search": {}}), \
             patch.object(mock_agent, '_intelligent_tool_planning', new_callable=AsyncMock, return_value=mock_tool_plan), \
             patch.object(mock_agent, '_execute_and_analyze_iteratively', new_callable=AsyncMock, return_value="Tool-based response"):
            
            result = await mock_agent._intelligent_tool_planning_and_execution(
                "Show me my emails", [], "user123", mock_mcp_client
            )
            
            assert result["success"] is True
            assert result["approach"] == "llm_analysis_with_tools" 
            assert result["response"] == "Tool-based response"
            assert result["tools_used"] == ["gmail_search"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
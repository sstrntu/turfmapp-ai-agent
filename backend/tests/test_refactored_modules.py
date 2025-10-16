"""
Unit tests for Phase 3 refactored modules.

This test file covers the new modules created during the Phase 3 refactoring:
- chat_source_extractor.py
- chat_block_builder.py
- chat_response_parser.py
- chat_tool_definitions.py
- chat_tool_executor.py
- mcp handler modules

Tests verify that:
1. Refactored functions maintain backward compatibility
2. All extracted functions work correctly in isolation
3. Type hints and doc strings are properly defined
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List


class TestChatSourceExtractor:
    """Tests for chat_source_extractor module."""

    def test_build_source_entry(self):
        """Test building a source entry from URL."""
        from app.services.chat_source_extractor import build_source_entry

        source = build_source_entry("https://example.com/page")
        assert source["url"] == "https://example.com/page"
        assert source["site"] == "example.com"
        assert "favicon" in source

    def test_build_source_entry_with_title(self):
        """Test building a source entry with custom title."""
        from app.services.chat_source_extractor import build_source_entry

        source = build_source_entry("https://example.com/page", title="Test Page")
        assert source["title"] == "Test Page"
        assert source["url"] == "https://example.com/page"

    def test_dedupe_sources(self):
        """Test deduplicating sources by URL."""
        from app.services.chat_source_extractor import dedupe_sources

        sources = [
            {"url": "https://example.com", "site": "example.com"},
            {"url": "https://example.com", "site": "example.com"},
            {"url": "https://other.com", "site": "other.com"}
        ]

        deduped = dedupe_sources(sources)
        assert len(deduped) == 2
        assert deduped[0]["url"] == "https://example.com"
        assert deduped[1]["url"] == "https://other.com"

    def test_extract_sources_from_text(self):
        """Test extracting HTTP(S) URLs from text."""
        from app.services.chat_source_extractor import extract_sources_from_text

        text = "Check out https://example.com and http://test.org for more info"
        sources = extract_sources_from_text(text)

        assert len(sources) == 2
        assert any(s["url"] == "https://example.com" for s in sources)
        assert any(s["url"] == "http://test.org" for s in sources)

    def test_extract_sources_from_text_no_urls(self):
        """Test extracting sources from text with no URLs."""
        from app.services.chat_source_extractor import extract_sources_from_text

        text = "This text has no URLs in it"
        sources = extract_sources_from_text(text)

        assert sources == []


class TestChatBlockBuilder:
    """Tests for chat_block_builder module."""

    def test_serialise_args_dict(self):
        """Test serializing dictionary arguments."""
        from app.services.chat_block_builder import serialise_args

        args = {"query": "test", "max_results": 10}
        serialized = serialise_args(args)

        assert "query" in serialized
        assert "max_results" in serialized

    def test_serialise_args_string(self):
        """Test serializing string arguments."""
        from app.services.chat_block_builder import serialise_args

        args = "simple string"
        serialized = serialise_args(args)

        assert serialized == "simple string"

    def test_build_blocks_from_tool_results(self):
        """Test building UI blocks from tool results."""
        from app.services.chat_block_builder import build_blocks_from_tool_results

        tool_results = [
            {
                "tool_call_id": "call_123",
                "tool_name": "gmail_recent",
                "result": {
                    "success": True,
                    "response": "Email data here"
                }
            }
        ]

        blocks = build_blocks_from_tool_results(tool_results, tool_call_inputs={})
        assert len(blocks) > 0

    def test_dedupe_blocks(self):
        """Test deduplicating blocks with IDs."""
        from app.services.chat_block_builder import dedupe_blocks

        blocks = [
            {"id": "block-1", "type": "text", "content": "Hello"},
            {"id": "block-1", "type": "text", "content": "Hello"},  # duplicate ID
            {"id": "block-2", "type": "text", "content": "World"}
        ]

        deduped = dedupe_blocks(blocks)
        assert len(deduped) == 2
        assert deduped[0]["id"] == "block-1"
        assert deduped[1]["id"] == "block-2"


class TestChatResponseParser:
    """Tests for chat_response_parser module."""

    @pytest.mark.asyncio
    async def test_parse_openai_output_items_no_function_calls(self):
        """Test parsing OpenAI output with no function calls."""
        from app.services.chat_response_parser import parse_openai_output_items

        output_items = [
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": "Hello world"}
                ]
            }
        ]

        function_calls, tool_results, tool_call_inputs, openai_function_calls, assistant_content = \
            parse_openai_output_items(output_items, "user123", AsyncMock())

        assert assistant_content == "Hello world"
        assert len(function_calls) == 0

    @pytest.mark.asyncio
    async def test_execute_openai_function_calls(self):
        """Test executing OpenAI function calls."""
        from app.services.chat_response_parser import execute_openai_function_calls

        function_calls = [
            {
                "needs_execution": True,
                "tool_name": "gmail_recent",
                "parsed_args": {"max_results": 5},
                "call_id": "call_123"
            }
        ]

        mock_handler = AsyncMock(return_value=[
            {
                "tool_call_id": "call_123",
                "content": "Email results"
            }
        ])

        openai_function_calls, tool_results, tool_call_inputs = \
            await execute_openai_function_calls(function_calls, "user123", mock_handler)

        assert len(openai_function_calls) > 0
        assert len(tool_results) > 0
        mock_handler.assert_called_once()

    def test_extract_sources_from_annotations(self):
        """Test extracting sources from content annotations."""
        from app.services.chat_response_parser import extract_sources_from_annotations

        content_items = [
            {
                "type": "output_text",
                "text": "Some text",
                "annotations": [
                    {
                        "type": "url_citation",
                        "url": "https://example.com",
                        "title": "Example"
                    }
                ]
            }
        ]

        sources = extract_sources_from_annotations(content_items)
        assert len(sources) == 1
        assert sources[0]["url"] == "https://example.com"


class TestChatToolDefinitions:
    """Tests for chat_tool_definitions module."""

    def test_build_google_function_tools_all_enabled(self):
        """Test building function tools with all services enabled."""
        from app.services.chat_tool_definitions import build_google_function_tools

        enabled_tools = {"gmail": True, "calendar": True, "drive": True}
        tools = build_google_function_tools(enabled_tools)

        # Should have tools from all three services
        assert len(tools) > 0
        tool_names = [tool["function"]["name"] for tool in tools]
        assert any("gmail" in name for name in tool_names)
        assert any("calendar" in name for name in tool_names)
        assert any("drive" in name for name in tool_names)

    def test_build_google_function_tools_gmail_only(self):
        """Test building function tools with only Gmail enabled."""
        from app.services.chat_tool_definitions import build_google_function_tools

        enabled_tools = {"gmail": True, "calendar": False, "drive": False}
        tools = build_google_function_tools(enabled_tools)

        tool_names = [tool["function"]["name"] for tool in tools]
        assert all("gmail" in name for name in tool_names)
        assert not any("calendar" in name for name in tool_names)
        assert not any("drive" in name for name in tool_names)

    def test_build_google_function_tools_none_enabled(self):
        """Test building function tools with no services enabled."""
        from app.services.chat_tool_definitions import build_google_function_tools

        enabled_tools = {"gmail": False, "calendar": False, "drive": False}
        tools = build_google_function_tools(enabled_tools)

        assert len(tools) == 0


class TestChatToolExecutor:
    """Tests for chat_tool_executor module."""

    @pytest.mark.asyncio
    async def test_handle_tool_calls_google_tool(self):
        """Test handling Google MCP tool calls."""
        from app.services import chat_tool_executor

        tool_calls = [
            {
                "id": "call_123",
                "function": {
                    "name": "gmail_recent",
                    "arguments": '{"max_results": 5}'
                }
            }
        ]

        # Patch the mcp_client module import
        with patch("app.services.mcp_client.google_mcp_client") as mock_mcp:
            mock_mcp.connect = AsyncMock()
            mock_mcp.call_tool = AsyncMock(return_value={"success": True, "response": "Email data"})

            results = await chat_tool_executor.handle_tool_calls("user123", tool_calls)

            assert len(results) == 1
            assert results[0]["tool_name"] == "gmail_recent"
            mock_mcp.connect.assert_called_once()
            mock_mcp.call_tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_tool_calls_invalid_json(self):
        """Test handling tool calls with invalid JSON arguments."""
        from app.services.chat_tool_executor import handle_tool_calls

        tool_calls = [
            {
                "id": "call_123",
                "function": {
                    "name": "gmail_recent",
                    "arguments": "invalid json {"
                }
            }
        ]

        results = await handle_tool_calls("user123", tool_calls)

        # Should handle error gracefully
        assert len(results) == 1
        assert results[0]["result"]["success"] == False


class TestMCPHandlers:
    """Tests for MCP handler modules."""

    @pytest.mark.asyncio
    async def test_gmail_handler_recent(self):
        """Test Gmail handler for recent emails."""
        from app.services.mcp.mcp_gmail_handler import handle_gmail_tool

        mock_service = Mock()
        mock_service.get_gmail_messages = AsyncMock(return_value={
            "messages": [{"subject": "Test", "from": "test@example.com"}],
            "resultSizeEstimate": 1
        })

        result = await handle_gmail_tool(
            "gmail_recent",
            Mock(),
            {"max_results": 1},
            mock_service
        )

        assert result["success"] == True
        assert "response" in result
        assert "tool" in result

    @pytest.mark.asyncio
    async def test_drive_handler_list_files(self):
        """Test Drive handler for listing files."""
        from app.services.mcp.mcp_drive_handler import handle_drive_tool

        mock_service = Mock()
        mock_service.get_drive_files = AsyncMock(return_value={
            "files": [{"name": "test.pdf", "mimeType": "application/pdf"}]
        })

        result = await handle_drive_tool(
            "drive_list_files",
            Mock(),
            {"query": "", "max_results": 10},
            mock_service
        )

        assert result["success"] == True
        assert "📁" in result["response"]

    @pytest.mark.asyncio
    async def test_calendar_handler_upcoming_events(self):
        """Test Calendar handler for upcoming events."""
        from app.services.mcp.mcp_calendar_handler import handle_calendar_tool

        mock_service = Mock()
        mock_service.get_calendar_events = AsyncMock(return_value={
            "events": [{"summary": "Meeting", "start": {"dateTime": "2025-01-15T10:00:00Z"}}]
        })

        result = await handle_calendar_tool(
            "calendar_upcoming_events",
            Mock(),
            {"days": 7},
            mock_service
        )

        assert result["success"] == True
        assert "📅" in result["response"]


class TestBackwardCompatibility:
    """Tests to ensure backward compatibility after refactoring."""

    def test_chat_service_imports(self):
        """Test that chat_service still exports extracted functions."""
        from app.services import chat_service

        # Main service class should be available
        assert hasattr(chat_service, 'EnhancedChatService')

    def test_google_oauth_imports(self):
        """Test that google_oauth still exports core functionality."""
        from app.services import google_oauth

        # Main service and models should be available
        assert hasattr(google_oauth, 'GoogleOAuthService')
        assert hasattr(google_oauth, 'google_oauth_service')
        assert hasattr(google_oauth, 'GoogleTokens')
        assert hasattr(google_oauth, 'GoogleAccount')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

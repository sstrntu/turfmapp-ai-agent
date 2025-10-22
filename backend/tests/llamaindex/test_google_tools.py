"""
Unit tests for LlamaIndex Tools (Gmail, Drive, Calendar)

These tests focus on tool creation and configuration.
Integration testing with actual async operations is covered in separate integration tests.
"""

import pytest
from unittest.mock import MagicMock
from google.oauth2.credentials import Credentials

from app.llamaindex.tools.gmail_tools import create_gmail_tools
from app.llamaindex.tools.drive_tools import create_drive_tools
from app.llamaindex.tools.calendar_tools import create_calendar_tools


@pytest.fixture
def mock_credentials():
    """Create mock Google credentials."""
    return MagicMock(spec=Credentials)


class TestGmailTools:
    """Test cases for Gmail tools creation and configuration."""

    def test_create_gmail_tools(self, mock_credentials):
        """Test creating Gmail FunctionTools."""
        tools = create_gmail_tools(mock_credentials)

        assert len(tools) == 2, "Should create exactly 2 Gmail tools"

        # Verify tool names
        tool_names = [tool.metadata.name for tool in tools]
        assert "search_gmail_messages" in tool_names
        assert "get_gmail_message" in tool_names

        # Verify all tools have descriptions
        for tool in tools:
            assert tool.metadata.description
            assert len(tool.metadata.description) > 20
            assert callable(tool.fn)

    def test_gmail_tool_descriptions(self, mock_credentials):
        """Test that Gmail tools have proper descriptions."""
        tools = create_gmail_tools(mock_credentials)

        search_tool = next(t for t in tools if t.metadata.name == "search_gmail_messages")
        get_tool = next(t for t in tools if t.metadata.name == "get_gmail_message")

        assert "search" in search_tool.metadata.description.lower()
        assert "gmail" in search_tool.metadata.description.lower()

        assert "message" in get_tool.metadata.description.lower()
        assert "detailed" in get_tool.metadata.description.lower() or "specific" in get_tool.metadata.description.lower()


class TestDriveTools:
    """Test cases for Drive tools creation and configuration."""

    def test_create_drive_tools(self, mock_credentials):
        """Test creating Drive FunctionTools."""
        tools = create_drive_tools(mock_credentials)

        assert len(tools) == 4, "Should create exactly 4 Drive tools"

        # Verify tool names
        tool_names = [tool.metadata.name for tool in tools]
        assert "search_drive_files" in tool_names
        assert "search_drive_folders" in tool_names
        assert "list_recent_drive_files" in tool_names
        assert "list_shared_drives" in tool_names

        # Verify all tools have descriptions and callable functions
        for tool in tools:
            assert tool.metadata.description
            assert len(tool.metadata.description) > 20
            assert callable(tool.fn)

    def test_drive_tool_descriptions(self, mock_credentials):
        """Test that Drive tools have proper descriptions."""
        tools = create_drive_tools(mock_credentials)

        search_files = next(t for t in tools if t.metadata.name == "search_drive_files")
        search_folders = next(t for t in tools if t.metadata.name == "search_drive_folders")
        list_recent = next(t for t in tools if t.metadata.name == "list_recent_drive_files")
        list_drives = next(t for t in tools if t.metadata.name == "list_shared_drives")

        assert "search" in search_files.metadata.description.lower()
        assert "files" in search_files.metadata.description.lower()

        assert "folders" in search_folders.metadata.description.lower()

        assert "recent" in list_recent.metadata.description.lower()

        assert "shared" in list_drives.metadata.description.lower() or "team" in list_drives.metadata.description.lower()


class TestCalendarTools:
    """Test cases for Calendar tools creation and configuration."""

    def test_create_calendar_tools(self, mock_credentials):
        """Test creating Calendar FunctionTools."""
        tools = create_calendar_tools(mock_credentials)

        assert len(tools) == 3, "Should create exactly 3 Calendar tools"

        # Verify tool names
        tool_names = [tool.metadata.name for tool in tools]
        assert "list_upcoming_calendar_events" in tool_names
        assert "list_recent_calendar_events" in tool_names
        assert "search_calendar_events" in tool_names

        # Verify all tools have descriptions and callable functions
        for tool in tools:
            assert tool.metadata.description
            assert len(tool.metadata.description) > 20
            assert callable(tool.fn)

    def test_calendar_tool_descriptions(self, mock_credentials):
        """Test that Calendar tools have proper descriptions."""
        tools = create_calendar_tools(mock_credentials)

        list_upcoming = next(t for t in tools if t.metadata.name == "list_upcoming_calendar_events")
        list_recent = next(t for t in tools if t.metadata.name == "list_recent_calendar_events")
        search = next(t for t in tools if t.metadata.name == "search_calendar_events")

        assert "upcoming" in list_upcoming.metadata.description.lower()
        assert "events" in list_upcoming.metadata.description.lower()

        assert "recent" in list_recent.metadata.description.lower()
        assert "events" in list_recent.metadata.description.lower()

        assert "search" in search.metadata.description.lower()
        assert "events" in search.metadata.description.lower()


class TestAllToolsIntegration:
    """Integration tests for all tools together."""

    def test_all_tools_creation(self, mock_credentials):
        """Test creating all tools at once."""
        gmail_tools = create_gmail_tools(mock_credentials)
        drive_tools = create_drive_tools(mock_credentials)
        calendar_tools = create_calendar_tools(mock_credentials)

        all_tools = gmail_tools + drive_tools + calendar_tools

        # Total: 2 Gmail + 4 Drive + 3 Calendar = 9 tools
        assert len(all_tools) == 9

        # Verify all tools have unique names
        tool_names = [tool.metadata.name for tool in all_tools]
        assert len(tool_names) == len(set(tool_names)), "Tool names should be unique"

        # Verify all tools have descriptions
        for tool in all_tools:
            assert tool.metadata.description
            assert len(tool.metadata.description) > 0

    def test_tool_names_convention(self, mock_credentials):
        """Test that all tool names follow naming convention."""
        gmail_tools = create_gmail_tools(mock_credentials)
        drive_tools = create_drive_tools(mock_credentials)
        calendar_tools = create_calendar_tools(mock_credentials)

        all_tools = gmail_tools + drive_tools + calendar_tools

        for tool in all_tools:
            name = tool.metadata.name
            # Check naming convention (snake_case)
            assert name.islower() or "_" in name, f"Tool name {name} should be snake_case"
            # Check contains service name
            assert any(
                service in name
                for service in ["gmail", "drive", "calendar"]
            ), f"Tool name {name} should contain service identifier"

    def test_all_tools_have_callable_functions(self, mock_credentials):
        """Test that all tools have callable functions."""
        gmail_tools = create_gmail_tools(mock_credentials)
        drive_tools = create_drive_tools(mock_credentials)
        calendar_tools = create_calendar_tools(mock_credentials)

        all_tools = gmail_tools + drive_tools + calendar_tools

        for tool in all_tools:
            assert callable(tool.fn), f"Tool {tool.metadata.name} should have callable function"
            assert tool.metadata.name
            assert tool.metadata.description

    def test_tool_metadata_completeness(self, mock_credentials):
        """Test that all tools have complete metadata."""
        gmail_tools = create_gmail_tools(mock_credentials)
        drive_tools = create_drive_tools(mock_credentials)
        calendar_tools = create_calendar_tools(mock_credentials)

        all_tools = gmail_tools + drive_tools + calendar_tools

        for tool in all_tools:
            # Check required metadata fields
            assert hasattr(tool, 'metadata')
            assert hasattr(tool.metadata, 'name')
            assert hasattr(tool.metadata, 'description')

            # Check metadata quality
            assert isinstance(tool.metadata.name, str)
            assert isinstance(tool.metadata.description, str)
            assert len(tool.metadata.name) > 0
            assert len(tool.metadata.description) > 0

    def test_gmail_vs_drive_vs_calendar_separation(self, mock_credentials):
        """Test that Gmail, Drive, and Calendar tools are properly separated."""
        gmail_tools = create_gmail_tools(mock_credentials)
        drive_tools = create_drive_tools(mock_credentials)
        calendar_tools = create_calendar_tools(mock_credentials)

        # Check Gmail tools only reference Gmail
        for tool in gmail_tools:
            assert "gmail" in tool.metadata.name.lower()
            assert "gmail" in tool.metadata.description.lower() or "email" in tool.metadata.description.lower() or "message" in tool.metadata.description.lower()

        # Check Drive tools only reference Drive
        for tool in drive_tools:
            assert "drive" in tool.metadata.name.lower()
            assert "drive" in tool.metadata.description.lower() or "file" in tool.metadata.description.lower() or "folder" in tool.metadata.description.lower()

        # Check Calendar tools only reference Calendar
        for tool in calendar_tools:
            assert "calendar" in tool.metadata.name.lower()
            assert "calendar" in tool.metadata.description.lower() or "event" in tool.metadata.description.lower()

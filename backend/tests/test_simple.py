"""
Simple Test to Validate Testing Setup

Basic tests to ensure pytest configuration works without complex dependencies.
"""

import pytest
import os


class TestBasicFunctionality:
    """Test basic functionality without database dependencies."""

    def test_environment_variables(self) -> None:
        """Test that environment variables are set correctly in tests."""
        assert os.getenv("TESTING") == "true"
        assert os.getenv("SUPABASE_URL") is not None
        assert os.getenv("OPENAI_API_KEY") is not None

    def test_simple_math(self) -> None:
        """Test basic functionality."""
        assert 2 + 2 == 4
        assert 10 - 5 == 5
        assert 3 * 3 == 9

    def test_string_operations(self) -> None:
        """Test string operations."""
        test_string = "TURFMAPP"
        assert test_string.lower() == "turfmapp"
        assert len(test_string) == 8
        assert "TURF" in test_string

    def test_list_operations(self) -> None:
        """Test list operations."""
        test_list = [1, 2, 3, 4, 5]
        assert len(test_list) == 5
        assert max(test_list) == 5
        assert min(test_list) == 1

    @pytest.mark.asyncio
    async def test_async_function(self) -> None:
        """Test async functionality."""
        async def async_add(a: int, b: int) -> int:
            return a + b
        
        result = await async_add(5, 3)
        assert result == 8


class TestDataStructures:
    """Test data structure handling."""

    def test_dictionary_operations(self) -> None:
        """Test dictionary operations."""
        test_dict = {
            "id": "test-123",
            "name": "Test User",
            "active": True
        }
        
        assert test_dict["id"] == "test-123"
        assert test_dict.get("name") == "Test User"
        assert test_dict.get("missing", "default") == "default"

    def test_json_like_data(self) -> None:
        """Test JSON-like data structures."""
        user_data = {
            "user": {
                "id": "user-123",
                "profile": {
                    "email": "test@example.com",
                    "preferences": {
                        "theme": "dark",
                        "notifications": True
                    }
                }
            }
        }
        
        assert user_data["user"]["id"] == "user-123"
        assert user_data["user"]["profile"]["email"] == "test@example.com"
        assert user_data["user"]["profile"]["preferences"]["theme"] == "dark"

    def test_list_comprehensions(self) -> None:
        """Test list comprehensions and filtering."""
        numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        
        evens = [n for n in numbers if n % 2 == 0]
        assert evens == [2, 4, 6, 8, 10]
        
        squares = [n ** 2 for n in numbers if n <= 5]
        assert squares == [1, 4, 9, 16, 25]
"""
Unit tests for LLM Factory
"""

import pytest
from unittest.mock import patch, MagicMock
from app.llamaindex.services.llm_factory import (
    LLMFactory,
    MODEL_REGISTRY,
    TaskType,
    ModelCapability,
)


class TestLLMFactory:
    """Test cases for LLMFactory."""

    @pytest.fixture
    def factory(self):
        """Create an LLM Factory instance for testing."""
        with patch.dict(
            "os.environ",
            {
                "OPENAI_API_KEY": "test-openai-key",
                "ANTHROPIC_API_KEY": "test-anthropic-key",
            },
        ):
            return LLMFactory()

    def test_initialization(self, factory):
        """Test factory initialization."""
        assert factory.openai_api_key == "test-openai-key"
        assert factory.anthropic_api_key == "test-anthropic-key"

    def test_initialization_without_keys(self):
        """Test factory initialization without API keys."""
        with patch.dict("os.environ", {}, clear=True):
            factory = LLMFactory()
            assert factory.openai_api_key is None
            assert factory.anthropic_api_key is None

    def test_get_model_config(self, factory):
        """Test getting model configuration."""
        config = factory.get_model_config("gpt-4o")
        assert config.model_id == "gpt-4o"
        assert config.provider == "openai"
        assert ModelCapability.CHAT in config.capabilities

    def test_get_model_config_invalid(self, factory):
        """Test getting config for invalid model."""
        with pytest.raises(ValueError, match="Unknown model"):
            factory.get_model_config("invalid-model")

    def test_list_available_models(self, factory):
        """Test listing all available models."""
        models = factory.list_available_models()
        assert len(models) > 0
        assert all(hasattr(m, "model_id") for m in models)

    def test_list_available_models_by_provider(self, factory):
        """Test listing models filtered by provider."""
        openai_models = factory.list_available_models(provider="openai")
        assert all(m.provider == "openai" for m in openai_models)

        anthropic_models = factory.list_available_models(provider="anthropic")
        assert all(m.provider == "anthropic" for m in anthropic_models)

    def test_recommend_model_for_task(self, factory):
        """Test model recommendation for different tasks."""
        # Test different task types
        chat_model = factory.recommend_model_for_task(TaskType.CHAT)
        assert chat_model in MODEL_REGISTRY

        code_model = factory.recommend_model_for_task(TaskType.CODE_GENERATION)
        assert code_model in MODEL_REGISTRY

    @patch("app.llamaindex.services.llm_factory.OpenAI")
    def test_create_openai_llm(self, mock_openai, factory):
        """Test creating an OpenAI LLM instance."""
        mock_instance = MagicMock()
        mock_openai.return_value = mock_instance

        llm = factory.create_llm(
            model_id="gpt-4o",
            temperature=0.7,
            max_tokens=2048,
            streaming=False,
        )

        mock_openai.assert_called_once_with(
            model="gpt-4o",
            temperature=0.7,
            max_tokens=2048,
            api_key="test-openai-key",
            streaming=False,
        )
        assert llm == mock_instance

    @patch("app.llamaindex.services.llm_factory.Anthropic")
    def test_create_anthropic_llm(self, mock_anthropic, factory):
        """Test creating an Anthropic LLM instance."""
        mock_instance = MagicMock()
        mock_anthropic.return_value = mock_instance

        llm = factory.create_llm(
            model_id="claude-sonnet-4-5-20250929",
            temperature=0.8,
            max_tokens=4096,
            streaming=True,
        )

        mock_anthropic.assert_called_once_with(
            model="claude-sonnet-4-5-20250929",
            temperature=0.8,
            max_tokens=4096,
            api_key="test-anthropic-key",
            streaming=True,
        )
        assert llm == mock_instance

    @patch("app.llamaindex.services.llm_factory.OpenAI")
    def test_create_llm_with_defaults(self, mock_openai, factory):
        """Test creating LLM with default parameters."""
        mock_instance = MagicMock()
        mock_openai.return_value = mock_instance

        llm = factory.create_llm(model_id="gpt-4o")

        # Should use config defaults
        call_kwargs = mock_openai.call_args.kwargs
        assert call_kwargs["temperature"] == 0.7  # Default from ModelConfig
        assert call_kwargs["max_tokens"] == 4096  # Default from ModelConfig

    def test_create_llm_without_api_key(self):
        """Test creating LLM without API key raises error."""
        with patch.dict("os.environ", {}, clear=True):
            factory = LLMFactory()

            with pytest.raises(ValueError, match="OPENAI_API_KEY is not configured"):
                factory.create_llm(model_id="gpt-4o")

            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY is not configured"):
                factory.create_llm(model_id="claude-sonnet-4-5-20250929")

    def test_estimate_cost(self, factory):
        """Test cost estimation."""
        cost = factory.estimate_cost(
            model_id="gpt-4o",
            input_tokens=1000,
            output_tokens=500,
        )

        assert cost["input_tokens"] == 1000
        assert cost["output_tokens"] == 500
        assert cost["total_cost"] > 0
        assert cost["currency"] == "USD"

        # Check calculation
        config = MODEL_REGISTRY["gpt-4o"]
        expected_input = (1000 / 1000) * config.cost_per_1k_input
        expected_output = (500 / 1000) * config.cost_per_1k_output
        assert cost["input_cost"] == expected_input
        assert cost["output_cost"] == expected_output
        assert cost["total_cost"] == expected_input + expected_output

    def test_estimate_cost_different_models(self, factory):
        """Test cost estimation for different models."""
        gpt4_cost = factory.estimate_cost("gpt-4o", 1000, 1000)
        gpt35_cost = factory.estimate_cost("gpt-3.5-turbo", 1000, 1000)

        # GPT-4o should be more expensive than GPT-3.5
        assert gpt4_cost["total_cost"] > gpt35_cost["total_cost"]

    def test_model_registry_completeness(self):
        """Test that all models in registry have required fields."""
        for model_id, config in MODEL_REGISTRY.items():
            assert config.model_id == model_id
            assert config.provider in ["openai", "anthropic"]
            assert config.display_name
            assert config.max_tokens > 0
            assert len(config.capabilities) > 0
            assert config.cost_per_1k_input >= 0
            assert config.cost_per_1k_output >= 0
            assert config.context_window > 0
            assert 0 <= config.default_temperature <= 1


class TestTaskTypeRecommendations:
    """Test task-based model recommendations."""

    @pytest.fixture
    def factory(self):
        """Create an LLM Factory instance."""
        with patch.dict(
            "os.environ",
            {"OPENAI_API_KEY": "test-key", "ANTHROPIC_API_KEY": "test-key"},
        ):
            return LLMFactory()

    def test_all_task_types_have_recommendations(self, factory):
        """Test that all task types return a valid model."""
        for task_type in TaskType:
            model_id = factory.recommend_model_for_task(task_type)
            assert model_id in MODEL_REGISTRY


class TestModelCapabilities:
    """Test model capability checks."""

    def test_function_calling_models(self):
        """Test that models with function calling capability are properly marked."""
        function_calling_models = [
            model_id
            for model_id, config in MODEL_REGISTRY.items()
            if ModelCapability.FUNCTION_CALLING in config.capabilities
        ]

        # Ensure we have function-calling capable models
        assert len(function_calling_models) > 0

    def test_streaming_models(self):
        """Test that models with streaming capability are properly marked."""
        streaming_models = [
            model_id
            for model_id, config in MODEL_REGISTRY.items()
            if ModelCapability.STREAMING in config.capabilities
        ]

        # Ensure we have streaming capable models
        assert len(streaming_models) > 0

    def test_large_context_models(self):
        """Test that large context models have appropriate context windows."""
        for model_id, config in MODEL_REGISTRY.items():
            if ModelCapability.LARGE_CONTEXT in config.capabilities:
                assert config.context_window >= 100000  # 100k+ tokens

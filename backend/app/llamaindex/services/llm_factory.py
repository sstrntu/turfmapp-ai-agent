"""
LLM Factory - Unified Multi-Model Interface

Provides a centralized factory for creating and managing LLM instances
across different providers (OpenAI, Anthropic) using LlamaIndex.

Features:
- Unified interface for all LLM providers
- Model registry with capabilities
- Automatic model selection based on task type
- Streaming support
- Token counting and cost estimation
"""

from __future__ import annotations

import os
import logging
from typing import Optional, Dict, Any, List
from enum import Enum

from llama_index.core.llms import LLM
from llama_index.llms.openai import OpenAI
from llama_index.llms.anthropic import Anthropic

logger = logging.getLogger(__name__)


class TaskType(str, Enum):
    """Types of tasks that can be performed with LLMs."""
    CHAT = "chat"
    COMPLETION = "completion"
    CODE_GENERATION = "code_generation"
    ANALYSIS = "analysis"
    SUMMARIZATION = "summarization"
    TOOL_USE = "tool_use"


class ModelCapability(str, Enum):
    """Capabilities that models can have."""
    CHAT = "chat"
    FUNCTION_CALLING = "function_calling"
    STREAMING = "streaming"
    VISION = "vision"
    LARGE_CONTEXT = "large_context"  # 100k+ tokens


class ModelConfig:
    """Configuration for an LLM model."""

    def __init__(
        self,
        model_id: str,
        provider: str,
        display_name: str,
        max_tokens: int,
        capabilities: List[ModelCapability],
        cost_per_1k_input: float,
        cost_per_1k_output: float,
        context_window: int,
        default_temperature: float = 0.7,
        recommended_for: Optional[List[TaskType]] = None,
    ):
        self.model_id = model_id
        self.provider = provider
        self.display_name = display_name
        self.max_tokens = max_tokens
        self.capabilities = capabilities
        self.cost_per_1k_input = cost_per_1k_input
        self.cost_per_1k_output = cost_per_1k_output
        self.context_window = context_window
        self.default_temperature = default_temperature
        self.recommended_for = recommended_for or []


# Model Registry
MODEL_REGISTRY: Dict[str, ModelConfig] = {
    # OpenAI Models
    "gpt-4o": ModelConfig(
        model_id="gpt-4o",
        provider="openai",
        display_name="GPT-4o",
        max_tokens=4096,
        capabilities=[
            ModelCapability.CHAT,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.STREAMING,
            ModelCapability.VISION,
            ModelCapability.LARGE_CONTEXT,
        ],
        cost_per_1k_input=0.005,
        cost_per_1k_output=0.015,
        context_window=128000,
        default_temperature=0.7,
        recommended_for=[TaskType.CHAT, TaskType.TOOL_USE, TaskType.ANALYSIS],
    ),
    "gpt-4o-mini": ModelConfig(
        model_id="gpt-4o-mini",
        provider="openai",
        display_name="GPT-4o Mini",
        max_tokens=4096,
        capabilities=[
            ModelCapability.CHAT,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.STREAMING,
        ],
        cost_per_1k_input=0.00015,
        cost_per_1k_output=0.0006,
        context_window=128000,
        default_temperature=0.7,
        recommended_for=[TaskType.CHAT, TaskType.SUMMARIZATION],
    ),
    "gpt-3.5-turbo": ModelConfig(
        model_id="gpt-3.5-turbo",
        provider="openai",
        display_name="GPT-3.5 Turbo",
        max_tokens=4096,
        capabilities=[
            ModelCapability.CHAT,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.STREAMING,
        ],
        cost_per_1k_input=0.0005,
        cost_per_1k_output=0.0015,
        context_window=16385,
        default_temperature=0.7,
        recommended_for=[TaskType.CHAT, TaskType.COMPLETION],
    ),

    # Anthropic Models
    "claude-sonnet-4-5-20250929": ModelConfig(
        model_id="claude-sonnet-4-5-20250929",
        provider="anthropic",
        display_name="Claude Sonnet 4.5",
        max_tokens=8192,
        capabilities=[
            ModelCapability.CHAT,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.STREAMING,
            ModelCapability.LARGE_CONTEXT,
        ],
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015,
        context_window=200000,
        default_temperature=0.7,
        recommended_for=[TaskType.CHAT, TaskType.ANALYSIS, TaskType.CODE_GENERATION],
    ),
    "claude-3-5-sonnet-20241022": ModelConfig(
        model_id="claude-3-5-sonnet-20241022",
        provider="anthropic",
        display_name="Claude 3.5 Sonnet",
        max_tokens=8192,
        capabilities=[
            ModelCapability.CHAT,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.STREAMING,
            ModelCapability.LARGE_CONTEXT,
        ],
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015,
        context_window=200000,
        default_temperature=0.7,
        recommended_for=[TaskType.CHAT, TaskType.ANALYSIS, TaskType.CODE_GENERATION],
    ),
    "claude-3-haiku-20240307": ModelConfig(
        model_id="claude-3-haiku-20240307",
        provider="anthropic",
        display_name="Claude 3 Haiku",
        max_tokens=4096,
        capabilities=[
            ModelCapability.CHAT,
            ModelCapability.STREAMING,
            ModelCapability.LARGE_CONTEXT,
        ],
        cost_per_1k_input=0.00025,
        cost_per_1k_output=0.00125,
        context_window=200000,
        default_temperature=0.7,
        recommended_for=[TaskType.CHAT, TaskType.SUMMARIZATION],
    ),
}


class LLMFactory:
    """Factory for creating and managing LLM instances."""

    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

        if not self.openai_api_key:
            logger.warning("⚠️  OPENAI_API_KEY not configured")
        if not self.anthropic_api_key:
            logger.warning("⚠️  ANTHROPIC_API_KEY not configured")

    def get_model_config(self, model_id: str) -> ModelConfig:
        """Get configuration for a specific model."""
        if model_id not in MODEL_REGISTRY:
            raise ValueError(f"Unknown model: {model_id}. Available models: {list(MODEL_REGISTRY.keys())}")
        return MODEL_REGISTRY[model_id]

    def list_available_models(self, provider: Optional[str] = None) -> List[ModelConfig]:
        """List all available models, optionally filtered by provider."""
        models = list(MODEL_REGISTRY.values())
        if provider:
            models = [m for m in models if m.provider == provider]
        return models

    def recommend_model_for_task(self, task_type: TaskType) -> str:
        """Recommend a model for a specific task type."""
        # Find models recommended for this task
        candidates = [
            (model_id, config)
            for model_id, config in MODEL_REGISTRY.items()
            if task_type in config.recommended_for
        ]

        if not candidates:
            # Default fallback
            return "gpt-4o"

        # Sort by cost efficiency (input cost)
        candidates.sort(key=lambda x: x[1].cost_per_1k_input)

        return candidates[0][0]

    def create_llm(
        self,
        model_id: str = "gpt-4o",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        streaming: bool = False,
        **kwargs: Any,
    ) -> LLM:
        """
        Create an LLM instance for the specified model.

        Args:
            model_id: Model identifier (e.g., "gpt-4o", "claude-sonnet-4-5-20250929")
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            streaming: Whether to enable streaming
            **kwargs: Additional provider-specific parameters

        Returns:
            LLM instance configured for the specified model
        """
        config = self.get_model_config(model_id)

        # Use config defaults if not specified
        if temperature is None:
            temperature = config.default_temperature
        if max_tokens is None:
            max_tokens = config.max_tokens

        logger.info(
            f"🤖 Creating LLM: {config.display_name} "
            f"(temp={temperature}, max_tokens={max_tokens}, streaming={streaming})"
        )

        if config.provider == "openai":
            return self._create_openai_llm(
                model_id=model_id,
                temperature=temperature,
                max_tokens=max_tokens,
                streaming=streaming,
                **kwargs,
            )
        elif config.provider == "anthropic":
            return self._create_anthropic_llm(
                model_id=model_id,
                temperature=temperature,
                max_tokens=max_tokens,
                streaming=streaming,
                **kwargs,
            )
        else:
            raise ValueError(f"Unsupported provider: {config.provider}")

    def _create_openai_llm(
        self,
        model_id: str,
        temperature: float,
        max_tokens: int,
        streaming: bool,
        **kwargs: Any,
    ) -> OpenAI:
        """Create an OpenAI LLM instance."""
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not configured")

        return OpenAI(
            model=model_id,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=self.openai_api_key,
            streaming=streaming,
            **kwargs,
        )

    def _create_anthropic_llm(
        self,
        model_id: str,
        temperature: float,
        max_tokens: int,
        streaming: bool,
        **kwargs: Any,
    ) -> Anthropic:
        """Create an Anthropic LLM instance."""
        if not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is not configured")

        return Anthropic(
            model=model_id,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=self.anthropic_api_key,
            **kwargs,
        )

    def estimate_cost(
        self,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
    ) -> Dict[str, float]:
        """
        Estimate the cost for a request.

        Args:
            model_id: Model identifier
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Dictionary with cost breakdown
        """
        config = self.get_model_config(model_id)

        input_cost = (input_tokens / 1000) * config.cost_per_1k_input
        output_cost = (output_tokens / 1000) * config.cost_per_1k_output
        total_cost = input_cost + output_cost

        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost,
            "currency": "USD",
        }


# Global instance
llm_factory = LLMFactory()

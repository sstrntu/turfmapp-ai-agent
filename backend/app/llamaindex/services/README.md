# LLM Factory Usage Guide

The LLM Factory provides a unified interface for working with multiple LLM providers (OpenAI, Anthropic) through LlamaIndex.

## Quick Start

```python
from app.llamaindex.services.llm_factory import llm_factory, TaskType

# Create an LLM instance (defaults to GPT-4o)
llm = llm_factory.create_llm()

# Use it with LlamaIndex
response = llm.complete("What is the capital of France?")
print(response.text)
```

## Creating LLMs for Different Models

### OpenAI Models

```python
# GPT-4o (most capable)
llm = llm_factory.create_llm(
    model_id="gpt-4o",
    temperature=0.7,
    max_tokens=2048,
    streaming=False
)

# GPT-4o Mini (faster, cheaper)
llm = llm_factory.create_llm(model_id="gpt-4o-mini")

# GPT-3.5 Turbo (legacy, cheapest)
llm = llm_factory.create_llm(model_id="gpt-3.5-turbo")
```

### Anthropic Models

```python
# Claude Sonnet 4.5 (latest, most capable)
llm = llm_factory.create_llm(
    model_id="claude-sonnet-4-5-20250929",
    temperature=0.8,
    max_tokens=4096
)

# Claude 3.5 Sonnet
llm = llm_factory.create_llm(model_id="claude-3-5-sonnet-20241022")

# Claude 3 Haiku (fastest, cheapest)
llm = llm_factory.create_llm(model_id="claude-3-haiku-20240307")
```

## Task-Based Model Selection

Let the factory recommend the best model for your task:

```python
from app.llamaindex.services.llm_factory import TaskType

# Get recommended model for chat
chat_model_id = llm_factory.recommend_model_for_task(TaskType.CHAT)
llm = llm_factory.create_llm(model_id=chat_model_id)

# Get recommended model for code generation
code_model_id = llm_factory.recommend_model_for_task(TaskType.CODE_GENERATION)
llm = llm_factory.create_llm(model_id=code_model_id)
```

## Streaming Responses

```python
# Enable streaming for real-time responses
llm = llm_factory.create_llm(
    model_id="gpt-4o",
    streaming=True
)

# Stream the response
response_stream = llm.stream_complete("Tell me a story")
for chunk in response_stream:
    print(chunk.delta, end="", flush=True)
```

## Cost Estimation

```python
# Estimate cost before making a request
cost_info = llm_factory.estimate_cost(
    model_id="gpt-4o",
    input_tokens=1000,
    output_tokens=500
)

print(f"Estimated cost: ${cost_info['total_cost']:.4f}")
print(f"Input: ${cost_info['input_cost']:.4f}")
print(f"Output: ${cost_info['output_cost']:.4f}")
```

## Model Information

```python
# Get configuration for a specific model
config = llm_factory.get_model_config("gpt-4o")
print(f"Model: {config.display_name}")
print(f"Provider: {config.provider}")
print(f"Context Window: {config.context_window} tokens")
print(f"Capabilities: {config.capabilities}")

# List all available models
all_models = llm_factory.list_available_models()
for model in all_models:
    print(f"{model.display_name} ({model.provider})")

# List models by provider
openai_models = llm_factory.list_available_models(provider="openai")
anthropic_models = llm_factory.list_available_models(provider="anthropic")
```

## Advanced Usage with LlamaIndex

### Chat with Message History

```python
from llama_index.core.llms import ChatMessage, MessageRole

llm = llm_factory.create_llm(model_id="gpt-4o")

messages = [
    ChatMessage(role=MessageRole.SYSTEM, content="You are a helpful assistant."),
    ChatMessage(role=MessageRole.USER, content="What is Python?"),
    ChatMessage(role=MessageRole.ASSISTANT, content="Python is a programming language."),
    ChatMessage(role=MessageRole.USER, content="What are its main features?"),
]

response = llm.chat(messages)
print(response.message.content)
```

### Async Operations

```python
import asyncio

async def chat_async():
    llm = llm_factory.create_llm(model_id="gpt-4o")

    response = await llm.acomplete("What is artificial intelligence?")
    print(response.text)

asyncio.run(chat_async())
```

## Available Task Types

- `TaskType.CHAT` - General conversation
- `TaskType.COMPLETION` - Text completion
- `TaskType.CODE_GENERATION` - Code generation and programming
- `TaskType.ANALYSIS` - Data analysis and reasoning
- `TaskType.SUMMARIZATION` - Text summarization
- `TaskType.TOOL_USE` - Function calling / tool use

## Model Capabilities

Each model has different capabilities:

- `ModelCapability.CHAT` - Conversational AI
- `ModelCapability.FUNCTION_CALLING` - Can call tools/functions
- `ModelCapability.STREAMING` - Supports streaming responses
- `ModelCapability.VISION` - Can process images
- `ModelCapability.LARGE_CONTEXT` - Supports 100k+ token context

## Best Practices

1. **Use task-based selection** when you don't have a specific model preference
2. **Enable streaming** for better user experience with long responses
3. **Estimate costs** before production deployment
4. **Use cheaper models** (mini/haiku) for simple tasks
5. **Cache LLM instances** when making multiple requests with the same configuration

## Error Handling

```python
try:
    llm = llm_factory.create_llm(model_id="invalid-model")
except ValueError as e:
    print(f"Invalid model: {e}")

try:
    # Without API key configured
    llm = llm_factory.create_llm(model_id="gpt-4o")
except ValueError as e:
    print(f"API key not configured: {e}")
```

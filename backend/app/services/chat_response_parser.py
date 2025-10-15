"""
Response parsing for various AI model formats.

This module handles parsing and processing of responses from different AI providers
(OpenAI and Claude), including tool calls, function calls, and content extraction.

Functions:
    parse_openai_response: Parse OpenAI API response format
    parse_claude_response: Parse Claude API response format
    extract_assistant_content: Extract text content from API responses
"""

from __future__ import annotations

import json
import logging
from typing import List, Dict, Any, Tuple

from .chat_source_extractor import build_source_entry
from .chat_block_builder import serialise_args

# Configure logger
logger = logging.getLogger(__name__)


def parse_openai_output_items(
    output_items: List[Dict[str, Any]],
    user_id: str,
    handle_tool_calls_fn,
) -> Tuple[List[Any], List[Dict[str, Any]], Dict[str, Dict[str, Any]], List[Dict[str, Any]], str]:
    """Parse OpenAI output items for function calls and messages.

    Args:
        output_items: List of output items from OpenAI response
        user_id: User ID for tool execution
        handle_tool_calls_fn: Async function to handle tool calls

    Returns:
        Tuple of (function_calls, tool_results, tool_call_inputs, openai_function_calls, assistant_content)
    """
    function_calls = []
    tool_results: List[Dict[str, Any]] = []
    tool_call_inputs: Dict[str, Dict[str, Any]] = {}
    openai_function_calls = []
    assistant_content = ""

    for i, item in enumerate(output_items):
        if not isinstance(item, dict):
            continue

        item_type = item.get("type")
        logger.warning(f"🔧 Output item {i}: type={item_type}")

        if item_type == "function_call":
            logger.warning(f"🔧 Function call found: {item}")
            function_calls.append(item)

            # Execute tool if completed
            status = item.get("status")
            logger.warning(f"🔧 Function call status: {status}")

            if status == "completed":
                tool_name = item.get("name")
                arguments = item.get("arguments")
                call_id = item.get("call_id")

                logger.warning(f"🔧 Status is 'completed' - will execute tool: {tool_name} with args: {arguments}")

                # Parse arguments if string
                if isinstance(arguments, str):
                    try:
                        parsed_args = json.loads(arguments)
                    except (TypeError, ValueError):
                        parsed_args = {}
                else:
                    parsed_args = arguments or {}

                # Track for later execution (will be awaited)
                function_calls.append({
                    "needs_execution": True,
                    "tool_name": tool_name,
                    "parsed_args": parsed_args,
                    "call_id": call_id,
                })

        elif item_type == "tool_call":
            logger.debug(f"🔧 Tool call found: {item}")
            function_calls.append(item)
            call_id = item.get("id") or item.get("tool_call_id") or item.get("call_id")
            if call_id:
                arguments = item.get("arguments") or item.get("input")
                parsed_args = None
                if isinstance(arguments, str):
                    try:
                        parsed_args = json.loads(arguments)
                    except (TypeError, ValueError):
                        parsed_args = None
                tool_call_inputs[call_id] = {
                    "name": item.get("name"),
                    "args": parsed_args if parsed_args is not None else arguments,
                    "args_text": serialise_args(parsed_args if parsed_args is not None else arguments),
                }

        elif item_type == "tool_result":
            logger.debug(f"🔧 Tool result found: {item}")
            tool_results.append(item)

        elif item_type == "message":
            content = item.get("content", [])
            logger.debug(f"🔧 Message content: {content}")

            # Extract text from message content
            if content and isinstance(content, list):
                for content_item in content:
                    if isinstance(content_item, dict) and content_item.get("type") == "output_text":
                        text = content_item.get("text", "")
                        if text:
                            assistant_content = text
                            logger.debug(f"🔧 Extracted message text: {text[:100]}...")
                            break

    return function_calls, tool_results, tool_call_inputs, openai_function_calls, assistant_content


async def execute_openai_function_calls(
    function_calls: List[Dict[str, Any]],
    user_id: str,
    handle_tool_calls_fn,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """Execute OpenAI function calls and return results.

    Args:
        function_calls: List of function calls to execute
        user_id: User ID for tool execution
        handle_tool_calls_fn: Async function to handle tool calls

    Returns:
        Tuple of (openai_function_calls, tool_results, tool_call_inputs)
    """
    openai_function_calls = []
    tool_results: List[Dict[str, Any]] = []
    tool_call_inputs: Dict[str, Dict[str, Any]] = {}

    for call in function_calls:
        if not call.get("needs_execution"):
            continue

        tool_name = call["tool_name"]
        parsed_args = call["parsed_args"]
        call_id = call["call_id"]

        try:
            tool_call_format = [{
                "id": call_id,
                "type": "function",
                "function": {
                    "name": tool_name,
                    "arguments": json.dumps(parsed_args) if not isinstance(parsed_args, str) else parsed_args
                }
            }]

            executed_results = await handle_tool_calls_fn(user_id, tool_call_format)
            logger.warning(f"🔧 Tool execution results: {executed_results}")

            openai_function_calls.append({
                "tool_name": tool_name,
                "args": parsed_args,
                "call_id": call_id,
                "results": executed_results
            })
            logger.warning(f"🔧 Added to openai_function_calls, new count: {len(openai_function_calls)}")

            for result in executed_results:
                tool_results.append(result)

            tool_call_inputs[call_id] = {
                "name": tool_name,
                "args": parsed_args,
                "args_text": serialise_args(parsed_args),
            }

        except Exception as tool_error:
            logger.error(f"❌ Tool execution failed: {tool_error}")
            tool_results.append({
                "tool_call_id": call_id,
                "content": f"Error executing {tool_name}: {str(tool_error)}"
            })

    return openai_function_calls, tool_results, tool_call_inputs


async def parse_claude_tool_uses(
    content_items: List[Dict[str, Any]],
    user_id: str,
    handle_tool_calls_fn,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """Parse and execute Claude tool_use blocks.

    Args:
        content_items: Content items from Claude response
        user_id: User ID for tool execution
        handle_tool_calls_fn: Async function to handle tool calls

    Returns:
        Tuple of (collected_tool_data, tool_results, tool_call_inputs)
    """
    claude_tool_uses = []

    for i, item in enumerate(content_items):
        if isinstance(item, dict) and item.get("type") == "tool_use":
            logger.warning(f"🔧 Claude tool_use found: {item}")
            claude_tool_uses.append(item)

    if not claude_tool_uses:
        return [], [], {}

    logger.warning(f"🔧 Claude requested {len(claude_tool_uses)} tools - executing")

    collected_tool_data = []
    tool_results: List[Dict[str, Any]] = []
    tool_call_inputs: Dict[str, Dict[str, Any]] = {}

    for tool_use in claude_tool_uses:
        tool_name = tool_use.get("name")
        tool_input = tool_use.get("input", {})
        tool_id = tool_use.get("id")

        logger.warning(f"🔧 Executing tool: {tool_name} with input: {tool_input}")

        try:
            tool_call_format = [{
                "id": tool_id,
                "type": "function",
                "function": {
                    "name": tool_name,
                    "arguments": json.dumps(tool_input) if isinstance(tool_input, dict) else str(tool_input)
                }
            }]

            executed_results = await handle_tool_calls_fn(user_id, tool_call_format)
            logger.warning(f"🔧 Tool execution results: {executed_results}")

            for result in executed_results:
                result_data = result.get("result", {})
                raw_data = result_data.get("response") or result_data.get("content") or json.dumps(result_data)

                service_type = "Gmail" if tool_name.startswith('gmail') else \
                             "Calendar" if tool_name.startswith('calendar') else \
                             "Drive" if tool_name.startswith('drive') else "Unknown"

                collected_tool_data.append({
                    "service": service_type,
                    "tool": tool_name,
                    "data": raw_data
                })

                tool_call_inputs[tool_id] = {
                    "name": tool_name,
                    "args": tool_input,
                    "args_text": serialise_args(tool_input),
                }
                tool_results.append(result)

        except Exception as tool_error:
            logger.error(f"❌ Tool execution failed: {tool_error}")
            collected_tool_data.append({
                "service": "Error",
                "tool": tool_name,
                "data": f"Error: {str(tool_error)}"
            })

    return collected_tool_data, tool_results, tool_call_inputs


async def summarize_tool_results_with_ai(
    collected_tool_data: List[Dict[str, Any]],
    user_message: str,
    model: str,
    is_claude_model: bool,
    call_claude_api_fn,
    call_responses_api_fn,
    **kwargs
) -> str:
    """Use AI to summarize tool execution results.

    Args:
        collected_tool_data: List of tool execution data
        user_message: Original user message
        model: AI model to use for summarization
        is_claude_model: Whether using Claude model
        call_claude_api_fn: Function to call Claude API
        call_responses_api_fn: Function to call OpenAI API
        **kwargs: Additional arguments for API calls

    Returns:
        Summarized assistant content
    """
    if not collected_tool_data:
        return ""

    logger.warning(f"🔧 Using {model} to summarize {len(collected_tool_data)} tool results")

    analysis_prompt = f"""User Question: {user_message}

Retrieved Data from Google Services:
{chr(10).join([f"{item['service']}: {item['data']}" for item in collected_tool_data])}

Please analyze the retrieved data and provide a helpful, concise answer to the user's question. Focus on:
1. Directly answering what the user asked
2. Summarizing key information rather than listing raw data
3. Being conversational and helpful
4. Highlighting important dates, names, or action items if relevant

CRITICAL: When URLs or links are provided in the data, you MUST include them EXACTLY as provided. NEVER truncate, shorten, or summarize URLs. Always show complete clickable links.

Respond as if you're having a natural conversation with the user."""

    analysis_messages = [
        {"role": "user", "content": f"{analysis_prompt}\n\nPlease analyze and summarize this information to answer the user's question."}
    ]

    try:
        if is_claude_model:
            analysis_result = await call_claude_api_fn(
                messages=analysis_messages,
                model=model,
                **{k: v for k, v in kwargs.items() if k not in ["model", "tools"]}
            )
        else:
            analysis_result = await call_responses_api_fn(
                messages=analysis_messages,
                model=model,
                **{k: v for k, v in kwargs.items() if k not in ["model", "tools"]}
            )

        logger.warning(f"🔧 {model} analysis result: {analysis_result}")

        # Extract AI summary
        assistant_content = analysis_result.get("output_text", "")

        if not assistant_content:
            output_array = analysis_result.get("output", [])
            for out_item in output_array:
                if isinstance(out_item, dict) and out_item.get("type") == "message":
                    content_list = out_item.get("content", [])
                    for content_item in content_list:
                        if isinstance(content_item, dict) and content_item.get("type") == "output_text":
                            text = content_item.get("text", "")
                            if text:
                                assistant_content = text
                                break
                    if assistant_content:
                        break

        logger.warning(f"🔧 {model} final summary: {assistant_content[:200] if assistant_content else 'STILL EMPTY'}")
        return assistant_content

    except Exception as e:
        logger.error(f"❌ AI summarization failed: {e}")
        # Fallback to raw results
        return "\n\n".join([
            f"📧 **{item['service']}**: {item['data']}" for item in collected_tool_data
        ])


def extract_sources_from_annotations(
    content_items: List[Dict[str, Any]]
) -> List[Dict[str, str]]:
    """Extract sources from content item annotations.

    Args:
        content_items: List of content items that may contain annotations

    Returns:
        List of source dictionaries
    """
    sources = []

    for content_item in content_items:
        if isinstance(content_item, dict) and content_item.get("type") == "output_text":
            annotations = content_item.get("annotations", [])
            if annotations:
                logger.debug(f"🔧 Found {len(annotations)} annotations")
                for annotation in annotations:
                    if annotation.get("type") == "url_citation":
                        source = build_source_entry(
                            annotation.get("url", ""),
                            annotation.get("title"),
                        )
                        if source:
                            sources.append(source)
                            logger.debug(f"🔧 Added annotated source: {source['site']}")

    return sources

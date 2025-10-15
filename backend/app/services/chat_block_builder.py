"""
Block builders for frontend rendering.

This module converts tool results into structured UI blocks for frontend display.
Handles multiple block types including search results, key-value pairs, markdown,
and generic tool calls.

Functions:
    extract_tool_payloads: Extract raw payloads from tool results
    serialise_args: Serialize tool arguments for display
    build_blocks_from_tool_results: Convert tool results into UI blocks
    dedupe_blocks: Remove duplicate blocks while preserving order
"""

from __future__ import annotations

import json
from typing import List, Dict, Any, Optional, Iterable

from .chat_source_extractor import build_source_entry


def extract_tool_payloads(tool_result: Dict[str, Any]) -> List[Any]:
    """Extract raw payloads from tool result for block rendering.

    Extracts structured and text payloads from tool results for frontend display.
    Handles both content arrays (with type-specific extraction) and direct output
    fields. JSON text is parsed, while plain text is preserved as-is.

    Args:
        tool_result: Dictionary containing tool execution results with 'content'
            array or direct output fields ('result', 'output', 'data', 'value').

    Returns:
        List of payload values extracted from the tool result. Can contain mixed
        types (dicts, strings, etc.). Returns empty list if input is not a dict
        or contains no extractable payloads.

    Example:
        >>> result = {"content": [{"type": "json", "json": {"key": "value"}}]}
        >>> payloads = extract_tool_payloads(result)
        >>> payloads[0]
        {'key': 'value'}
    """
    if not isinstance(tool_result, dict):
        return []

    payloads: List[Any] = []

    def _add_payload(value: Any) -> None:
        if value is None:
            return
        payloads.append(value)

    content_items = tool_result.get("content")
    if isinstance(content_items, list):
        for entry in content_items:
            if not isinstance(entry, dict):
                continue
            entry_type = entry.get("type")
            if entry_type in {"json", "json_object"} and entry.get("json") is not None:
                _add_payload(entry.get("json"))
            elif entry_type in {"text", "output_text"}:
                text = entry.get("text")
                if not text:
                    continue
                try:
                    _add_payload(json.loads(text))
                except (TypeError, ValueError):
                    _add_payload(text)

    for key in ("result", "output", "data", "value"):
        if key in tool_result and tool_result[key]:
            _add_payload(tool_result[key])

    return payloads


def serialise_args(args: Any) -> Optional[str]:
    """Serialise tool arguments for display.

    Converts tool call arguments to a human-readable string format for UI display.
    Handles strings (pass-through), JSON-serializable objects (pretty-print), and
    non-serializable objects (fallback to str()).

    Args:
        args: Tool arguments to serialize - can be None, str, dict, list, or any
            other type.

    Returns:
        String representation of the arguments formatted for display, or None if
        args is None. JSON objects are indented for readability.

    Example:
        >>> serialise_args({"query": "test", "limit": 10})
        '{\\n  "query": "test",\\n  "limit": 10\\n}'
        >>> serialise_args("already a string")
        'already a string'
        >>> serialise_args(None)
        None
    """
    if args is None:
        return None
    if isinstance(args, str):
        return args
    try:
        return json.dumps(args, ensure_ascii=False, indent=2)
    except TypeError:
        return str(args)


def build_blocks_from_tool_results(
    tool_results: Iterable[Dict[str, Any]],
    tool_call_inputs: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Convert tool results into structured blocks for frontend rendering.

    Transforms raw tool execution results into UI-friendly block structures with
    appropriate types (search-results, key-value, markdown, tool-call) based on
    the payload content. Enriches blocks with metadata from tool call inputs.

    Args:
        tool_results: Iterable of tool result dictionaries, each typically containing
            'tool_call_id', 'name', and result data in various formats.
        tool_call_inputs: Optional mapping of tool call IDs to their input metadata
            (name, args, args_text). Used to enrich blocks with call context.
            Defaults to empty dict if not provided.

    Returns:
        Deduplicated list of block dictionaries (max 8 items), each containing:
        - id: Unique block identifier
        - type: Block type (search-results, key-value, markdown, tool-call)
        - toolName: Name of the tool that generated this block
        - args: Original tool arguments
        - argsText: Serialized display version of arguments
        - callId: Tool call identifier
        - Additional type-specific fields (results, pairs, text, result, title)

    Example:
        >>> results = [{"tool_call_id": "1", "name": "search", "result": {...}}]
        >>> blocks = build_blocks_from_tool_results(results)
        >>> blocks[0]['type']
        'search-results'
    """
    blocks: List[Dict[str, Any]] = []

    if tool_call_inputs is None:
        tool_call_inputs = {}

    for index, tool_result in enumerate(tool_results):
        if not isinstance(tool_result, dict):
            continue

        call_id = (
            tool_result.get("tool_call_id")
            or tool_result.get("id")
            or tool_result.get("tool_use_id")
        )
        tool_name = (
            tool_result.get("name")
            or tool_result.get("tool_name")
            or tool_call_inputs.get(call_id, {}).get("name")
        )

        args_info = tool_call_inputs.get(call_id, {})
        args_payload = args_info.get("args")
        args_text = args_info.get("args_text") or serialise_args(args_payload)

        payloads = extract_tool_payloads(tool_result)

        block_id_prefix = (tool_name or "tool").replace(" ", "-").lower()
        base_common = {
            "toolName": tool_name,
            "args": args_payload,
            "argsText": args_text,
            "callId": call_id,
        }

        created_block = False
        for payload in payloads:
            if isinstance(payload, dict):
                results = None
                for key in ("results", "search_results", "items"):
                    candidate = payload.get(key)
                    if isinstance(candidate, list) and candidate:
                        results = candidate
                        break

                if results:
                    normalised_results = []
                    for item in results:
                        if isinstance(item, dict):
                            source = build_source_entry(
                                item.get("url")
                                or item.get("link")
                                or item.get("source_url"),
                                item.get("title") or item.get("name"),
                            )
                            snippet = (
                                item.get("snippet")
                                or item.get("description")
                                or item.get("text")
                            )
                            entry = {
                                "title": source["title"] if source else (item.get("title") or item.get("name") or "Result"),
                                "url": source["url"] if source else item.get("url") or item.get("link"),
                                "snippet": snippet,
                                "site": source["site"] if source else item.get("site"),
                                "favicon": source["favicon"] if source else item.get("favicon"),
                            }
                            normalised_results.append(entry)
                        elif isinstance(item, str):
                            normalised_results.append(
                                {
                                    "title": item,
                                    "url": None,
                                    "snippet": None,
                                }
                            )

                    if normalised_results:
                        blocks.append(
                            {
                                "id": f"{block_id_prefix}-search-{index}",
                                "type": "search-results",
                                "title": payload.get("title")
                                or payload.get("query")
                                or payload.get("topic")
                                or (tool_name or "Search results"),
                                "results": normalised_results,
                                **base_common,
                            }
                        )
                        created_block = True
                        continue

                # Fallback to key-value representation for structured dicts
                pairs = []
                for key, value in payload.items():
                    if isinstance(value, (dict, list)):
                        value_repr = json.dumps(value, ensure_ascii=False, indent=2)
                    else:
                        value_repr = str(value)
                    pairs.append({"label": key, "value": value_repr})

                if pairs:
                    blocks.append(
                        {
                            "id": f"{block_id_prefix}-object-{index}",
                            "type": "key-value",
                            "title": payload.get("title") or (tool_name or "Tool output"),
                            "pairs": pairs,
                            **base_common,
                        }
                    )
                    created_block = True
                    continue

            elif isinstance(payload, str):
                text = payload.strip()
                if text:
                    blocks.append(
                        {
                            "id": f"{block_id_prefix}-markdown-{index}",
                            "type": "markdown",
                            "text": text,
                            **base_common,
                        }
                    )
                    created_block = True
                    continue

        if not created_block:
            fallback_payload = payloads[0] if payloads else tool_result
            blocks.append(
                {
                    "id": f"{block_id_prefix}-raw-{index}",
                    "type": "tool-call",
                    "title": tool_name or "Tool response",
                    "result": fallback_payload,
                    **base_common,
                }
            )

    return dedupe_blocks(blocks)


def dedupe_blocks(blocks: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate blocks while preserving order.

    Deduplicates block dictionaries using either explicit 'id' field or a composite
    hash of (type, toolName, title) for blocks without IDs. Limits output to
    maximum of 8 blocks.

    Args:
        blocks: Iterable of block dictionaries to deduplicate. Non-dict items are
            silently skipped.

    Returns:
        List of unique blocks in original order, limited to 8 items maximum.
        Uniqueness determined by 'id' field if present, otherwise by composite
        key of block metadata.

    Example:
        >>> blocks = [
        ...     {"id": "1", "type": "search"},
        ...     {"id": "1", "type": "search"},  # duplicate
        ...     {"id": "2", "type": "tool"}
        ... ]
        >>> deduped = dedupe_blocks(blocks)
        >>> len(deduped)
        2
    """
    cleaned: List[Dict[str, Any]] = []
    seen: set = set()

    for block in blocks:
        if not isinstance(block, dict):
            continue
        block_id = block.get("id")
        if block_id:
            key = ("id", block_id)
        else:
            key = ("hash", block.get("type"), block.get("toolName"), block.get("title"))
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(block)
        if len(cleaned) >= 8:
            break

    return cleaned

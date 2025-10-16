"""
Source extraction utilities for chat responses.

This module provides utilities for extracting and normalizing URLs from various
data structures (text, objects, tool results, Claude responses). Sources are
converted into structured dictionaries with metadata for frontend display.

Functions:
    build_source_entry: Build a normalized source entry from URL and title
    dedupe_sources: Deduplicate sources, preserving order
    extract_sources_from_text: Extract HTTP(S) URLs from plain text
    extract_sources_from_object: Recursively extract sources from nested structures
    extract_sources_from_tool_result: Extract sources from tool result payload
    extract_sources_from_claude_response: Extract sources from Claude response
"""

from __future__ import annotations

import re
import json
from typing import List, Dict, Any, Optional, Iterable
from collections import deque
from urllib.parse import urlparse

# URL pattern for extracting HTTP(S) URLs from text
_URL_PATTERN = re.compile(r"https?://[^\s\]\)\"'>]+")


def build_source_entry(url: Optional[str], title: Optional[str] = None) -> Optional[Dict[str, str]]:
    """
    Build a normalized source entry from URL and title.

    Args:
        url: The URL to normalize and validate
        title: Optional display title for the source

    Returns:
        Dictionary with url, title, site, and favicon keys, or None if invalid
    """
    if not isinstance(url, str):
        return None

    url = url.strip()
    if not url:
        return None

    if url.startswith("//"):
        url = f"https:{url}"
    elif not url.lower().startswith(("http://", "https://")):
        url = f"https://{url}"

    try:
        parsed = urlparse(url)
    except ValueError:
        return None

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None

    site = parsed.netloc
    display_title = title.strip() if isinstance(title, str) and title.strip() else site

    return {
        "url": url,
        "title": display_title,
        "site": site,
        "favicon": f"https://www.google.com/s2/favicons?domain={site}&sz=64",
    }


def dedupe_sources(sources: Iterable[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Deduplicate sources, preserving order and limiting count.

    Args:
        sources: Iterable of source dictionaries with 'url' keys

    Returns:
        List of unique sources, limited to 8 items maximum
    """
    unique: List[Dict[str, str]] = []
    seen = set()

    for source in sources:
        url = source.get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        unique.append(source)
        if len(unique) >= 8:
            break

    return unique


def extract_sources_from_text(text: str) -> List[Dict[str, str]]:
    """Extract HTTP(S) URLs from plain text and convert to sources.

    Scans the provided text for HTTP(S) URLs using regex pattern matching,
    cleans each URL by removing trailing punctuation, validates and normalizes
    them into source entries with metadata.

    Args:
        text: Plain text string to search for URLs.

    Returns:
        List of source dictionaries, each containing 'url', 'title', 'site',
        and 'favicon' keys. Returns empty list if input is not a string or
        contains no valid URLs.

    Example:
        >>> text = "Check out https://example.com and https://test.org!"
        >>> sources = extract_sources_from_text(text)
        >>> len(sources)
        2
    """
    if not isinstance(text, str):
        return []

    matches = _URL_PATTERN.findall(text)
    sources = []
    for match in matches:
        cleaned = match.rstrip(".,);]")
        source = build_source_entry(cleaned)
        if source:
            sources.append(source)
    return sources


def extract_sources_from_object(obj: Any) -> List[Dict[str, str]]:
    """Recursively extract source entries from nested data structures.

    Performs breadth-first traversal of nested dictionaries, lists, and JSON strings
    to find and extract URL-based source entries. Handles multiple URL field names
    (url, link, href) and title field names (title, name, headline, text).

    Args:
        obj: Any data structure to search - can be dict, list, str (JSON), or
            any nested combination thereof.

    Returns:
        List of source dictionaries extracted from the object tree, each containing
        'url', 'title', 'site', and 'favicon' keys. Returns empty list if no valid
        sources found.

    Example:
        >>> data = {"results": [{"url": "https://example.com", "title": "Example"}]}
        >>> sources = extract_sources_from_object(data)
        >>> sources[0]['site']
        'example.com'
    """
    sources: List[Dict[str, str]] = []
    queue: deque[Any] = deque([obj])

    while queue:
        current = queue.popleft()

        if isinstance(current, dict):
            url = current.get("url") or current.get("link") or current.get("href")
            title = current.get("title") or current.get("name") or current.get("headline") or current.get("text")

            source = build_source_entry(url, title)
            if source:
                sources.append(source)

            for value in current.values():
                if isinstance(value, (list, dict, str)):
                    queue.append(value)

        elif isinstance(current, list):
            for item in current:
                if isinstance(item, (list, dict, str)):
                    queue.append(item)

        elif isinstance(current, str):
            try:
                parsed = json.loads(current)
            except (TypeError, ValueError):
                sources.extend(extract_sources_from_text(current))
            else:
                queue.append(parsed)

    return sources


def extract_sources_from_tool_result(tool_result: Dict[str, Any]) -> List[Dict[str, str]]:
    """Extract sources from a tool result payload.

    Searches tool result dictionaries for common output fields (output, content,
    outputs, results, data, value) and extracts URL sources from each. Also checks
    nested 'tool' object for additional output fields.

    Args:
        tool_result: Dictionary containing tool execution results, typically with
            fields like 'output', 'content', or 'results' containing response data.

    Returns:
        Deduplicated list of source dictionaries (max 8 items), each containing
        'url', 'title', 'site', and 'favicon' keys. Returns empty list if input
        is not a dict or contains no valid sources.

    Example:
        >>> result = {"output": {"url": "https://example.com", "title": "Test"}}
        >>> sources = extract_sources_from_tool_result(result)
        >>> len(sources)
        1
    """
    if not isinstance(tool_result, dict):
        return []

    candidate_values: List[Any] = []
    for key in ("output", "content", "outputs", "results", "data", "value"):
        value = tool_result.get(key)
        if value:
            candidate_values.append(value)

    tool_info = tool_result.get("tool")
    if isinstance(tool_info, dict):
        for key in ("output", "outputs", "results"):
            if tool_info.get(key):
                candidate_values.append(tool_info[key])

    sources: List[Dict[str, str]] = []
    for candidate in candidate_values:
        sources.extend(extract_sources_from_object(candidate))

    return dedupe_sources(sources)


def extract_sources_from_claude_response(response: Dict[str, Any]) -> List[Dict[str, str]]:
    """Extract sources from Claude response payload.

    Searches Claude API response for sources in multiple locations:
    - Content block citations (both direct and in metadata)
    - Tool result blocks
    - Search results within blocks
    - Top-level citations array

    Args:
        response: Claude API response dictionary, typically containing 'content'
            array with text blocks, tool results, and optional 'citations' field.

    Returns:
        Deduplicated list of source dictionaries (max 8 items), each containing
        'url', 'title', 'site', and 'favicon' keys. Returns empty list if no
        valid sources found in response.

    Example:
        >>> response = {
        ...     "content": [{"citations": [{"url": "https://example.com", "title": "Test"}]}],
        ...     "citations": [{"url": "https://test.org"}]
        ... }
        >>> sources = extract_sources_from_claude_response(response)
        >>> len(sources)
        2
    """
    sources: List[Dict[str, str]] = []

    content_blocks = response.get("content", [])
    if isinstance(content_blocks, list):
        for block in content_blocks:
            if not isinstance(block, dict):
                continue

            citations = block.get("citations") or block.get("metadata", {}).get("citations")
            if isinstance(citations, list):
                for citation in citations:
                    if isinstance(citation, dict):
                        source = build_source_entry(
                            citation.get("url") or citation.get("source_url") or citation.get("source"),
                            citation.get("title") or citation.get("text"),
                        )
                        if source:
                            sources.append(source)

            if block.get("type") == "tool_result":
                sources.extend(extract_sources_from_tool_result(block))

            sources.extend(extract_sources_from_object(block.get("search_results")))

    top_level_citations = response.get("citations")
    if isinstance(top_level_citations, list):
        for citation in top_level_citations:
            if isinstance(citation, dict):
                source = build_source_entry(
                    citation.get("url") or citation.get("source_url") or citation.get("source"),
                    citation.get("title") or citation.get("text"),
                )
                if source:
                    sources.append(source)

    return dedupe_sources(sources)

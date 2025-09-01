"""
Chat utility functions for text processing and API helpers.

This module contains utility functions extracted from the chat API to improve
modularity and maintain the 500-line file limit per code.md guidelines.
"""

from __future__ import annotations

import json
from typing import List, Dict, Any
from urllib.parse import urlparse, urljoin


def stringify_text(value) -> str:
    """Best-effort conversion of Responses API text payloads to a plain string."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        # Common shapes: {"text": "..."} or {"text": {"value": "..."}} or {"value": "..."}
        text_field = value.get("text")
        if isinstance(text_field, str):
            return text_field
        if isinstance(text_field, dict):
            inner_val = text_field.get("value")
            if isinstance(inner_val, str):
                return inner_val
        value_field = value.get("value")
        if isinstance(value_field, str):
            return value_field
        # Fallthrough: serialize the dict
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        parts: List[str] = []
        for item in value:
            parts.append(stringify_text(item))
        return "".join(parts)
    # Fallback: JSON-serialize
    return json.dumps(value, ensure_ascii=False)


def is_valid_url(url: str) -> bool:
    """Check if a URL is valid for source citation."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def sanitize_url(url: str, base_url: str = "") -> str:
    """Sanitize and normalize URLs for citations."""
    if not url:
        return ""
    
    try:
        # Handle relative URLs
        if url.startswith(('//', 'http://', 'https://')):
            return url
        elif url.startswith('/'):
            if base_url:
                return urljoin(base_url, url)
            return url
        else:
            # Relative path
            if base_url:
                return urljoin(base_url, url)
            return url
    except Exception:
        return url


def extract_sources_from_response(response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract source citations from API response."""
    sources = []
    
    # Extract from various possible response structures
    if isinstance(response_data, dict):
        # Check for sources in common locations
        if "sources" in response_data:
            sources.extend(response_data["sources"])
        
        if "citations" in response_data:
            sources.extend(response_data["citations"])
        
        # Check in nested structures
        if "data" in response_data and isinstance(response_data["data"], dict):
            data_sources = extract_sources_from_response(response_data["data"])
            sources.extend(data_sources)
    
    # Validate and normalize sources
    valid_sources = []
    for source in sources:
        if isinstance(source, dict) and source.get("url"):
            if is_valid_url(source["url"]):
                valid_sources.append({
                    "url": sanitize_url(source["url"]),
                    "title": source.get("title", ""),
                    "snippet": source.get("snippet", "")
                })
    
    return valid_sources


def format_chat_history(messages: List[Dict[str, Any]], max_context: int = 10) -> List[Dict[str, Any]]:
    """Format chat history for API consumption with context limiting."""
    if not messages:
        return []
    
    # Limit to most recent messages to avoid token limits
    recent_messages = messages[-max_context:] if len(messages) > max_context else messages
    
    formatted_messages = []
    for msg in recent_messages:
        if isinstance(msg, dict) and msg.get("role") and msg.get("content"):
            formatted_messages.append({
                "role": msg["role"],
                "content": str(msg["content"])
            })
    
    return formatted_messages


def process_attachments(attachments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Process and validate chat attachments."""
    if not attachments:
        return []
    
    processed_attachments = []
    for attachment in attachments:
        if not isinstance(attachment, dict):
            continue
            
        # Basic validation
        if attachment.get("type") and attachment.get("content"):
            processed_attachments.append({
                "type": attachment["type"],
                "content": attachment["content"],
                "metadata": attachment.get("metadata", {})
            })
    
    return processed_attachments
"""
Response Parser Module

Handles parsing and extraction from API responses including:
- Source extraction from annotations and URLs
- Function call parsing
- Response text extraction
- URL validation and favicon generation

Extracted from chat_service.py to improve maintainability and separation of concerns.
"""

from __future__ import annotations

import re
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class ResponseParser:
    """Parses API responses and extracts structured data."""
    
    @staticmethod
    def stringify_text(text) -> str:
        """
        Helper method to stringify text from various formats.
        
        Args:
            text: Text in various formats (str, list, other)
            
        Returns:
            String representation
        """
        if isinstance(text, str):
            return text
        elif isinstance(text, list):
            return "".join(str(item) for item in text)
        return str(text)
    
    @staticmethod
    def extract_sources_from_annotations(annotations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract sources from URL citations in annotations.
        
        Args:
            annotations: List of annotation dicts from API response
            
        Returns:
            List of source dicts with url, title, site, favicon
        """
        sources = []
        
        if not annotations:
            return sources
        
        logger.debug(f"Found {len(annotations)} annotations")
        
        for annotation in annotations:
            if annotation.get("type") == "url_citation":
                url = annotation.get("url", "")
                title = annotation.get("title", "")
                
                if url:
                    try:
                        parsed = urlparse(url)
                        domain = parsed.netloc
                        
                        source = {
                            "url": url,
                            "title": title if title else domain,
                            "site": domain,
                            "favicon": f"https://www.google.com/s2/favicons?domain={domain}&sz=64"
                        }
                        sources.append(source)
                        logger.debug(f"Added source from annotation: {domain}")
                    except Exception as e:
                        logger.error(f"Failed to parse URL {url}: {e}", exc_info=True)
        
        return sources
    
    @staticmethod
    def extract_sources_from_text(text: str, max_sources: int = 8) -> List[Dict[str, Any]]:
        """
        Extract sources from URLs found in text content.
        
        Args:
            text: Text content to search for URLs
            max_sources: Maximum number of sources to return
            
        Returns:
            List of source dicts
        """
        sources = []
        
        if not isinstance(text, str) or not text:
            return sources
        
        # Find URLs in the response text
        raw_urls = re.findall(r"https?://[^\s)]+", text)
        logger.debug(f"Found {len(raw_urls)} URLs in response text")
        
        seen = set()
        for u in raw_urls:
            cleaned = u.rstrip('.,);]')
            if cleaned in seen:
                continue
            seen.add(cleaned)
            
            try:
                parsed = urlparse(cleaned)
                if parsed.scheme in {"http", "https"} and parsed.netloc:
                    source = {
                        "url": cleaned,
                        "title": parsed.netloc,
                        "site": parsed.netloc,
                        "favicon": f"https://www.google.com/s2/favicons?domain={parsed.netloc}&sz=64"
                    }
                    sources.append(source)
                    logger.debug(f"Added URL source: {parsed.netloc}")
            except Exception as e:
                logger.error(f"Failed to parse URL {cleaned}: {e}", exc_info=True)
                continue
        
        # Limit sources
        if sources:
            sources = sources[:max_sources]
            logger.info(f"Extracted {len(sources)} sources from URLs")
        
        return sources
    
    @staticmethod
    def parse_function_calls(output_items: List[Any]) -> List[Dict[str, Any]]:
        """
        Parse function calls from API output items.
        
        Args:
            output_items: List of output items from API response
            
        Returns:
            List of parsed function call dicts
        """
        function_calls = []
        
        if not output_items:
            return function_calls
        
        logger.debug(f"Parsing {len(output_items)} output items for function calls")
        
        for i, item in enumerate(output_items):
            if not isinstance(item, dict):
                continue
            
            item_type = item.get("type")
            logger.debug(f"Output item {i}: type={item_type}")
            
            if item_type in ["function_call", "tool_call"]:
                logger.debug(f"Function call found: {item}")
                function_calls.append(item)
        
        return function_calls
    
    @staticmethod
    def extract_text_from_message(content: List[Dict[str, Any]]) -> tuple[str, List[Dict[str, Any]]]:
        """
        Extract text and sources from message content items.
        
        Args:
            content: List of content items from message
            
        Returns:
            Tuple of (extracted_text, sources_list)
        """
        text = ""
        sources = []
        
        if not content or not isinstance(content, list):
            return text, sources
        
        logger.debug(f"Extracting text from {len(content)} content items")
        
        for content_item in content:
            if not isinstance(content_item, dict):
                continue
            
            if content_item.get("type") == "output_text":
                extracted = content_item.get("text", "")
                if extracted:
                    text = extracted
                    logger.debug(f"Extracted message text: {text[:100]}...")
                    
                    # Extract sources from annotations
                    annotations = content_item.get("annotations", [])
                    if annotations:
                        sources = ResponseParser.extract_sources_from_annotations(annotations)
                    break
        
        return text, sources
    
    @staticmethod
    def parse_api_response(
        api_response: Dict[str, Any],
        model: str
    ) -> tuple[str, Optional[str], List[Dict[str, Any]]]:
        """
        Parse complete API response to extract content, reasoning, and sources.
        
        Args:
            api_response: Complete API response dict
            model: Model name used for the request
            
        Returns:
            Tuple of (assistant_content, reasoning, sources)
        """
        assistant_content = ""
        reasoning = None
        sources = []
        
        logger.debug(f"Parsing API response for model {model}")
        
        # Check for tool calls
        if "tool_calls" in api_response:
            logger.debug(f"Tool calls found in response: {api_response['tool_calls']}")
        
        # Parse output items
        output_items = api_response.get("output", [])
        logger.debug(f"Output items: {len(output_items) if output_items else 0}")
        
        # Extract function calls
        function_calls = ResponseParser.parse_function_calls(output_items)
        
        # Process output items for text and sources
        for item in output_items:
            if isinstance(item, dict) and item.get("type") == "message":
                content = item.get("content", [])
                logger.debug(f"Message content: {content}")
                
                # Extract text and sources from message
                text, extracted_sources = ResponseParser.extract_text_from_message(content)
                if text:
                    assistant_content = text
                    sources.extend(extracted_sources)
                    break
        
        # Fallback to output_text if no content extracted
        if not assistant_content:
            assistant_content = ResponseParser.stringify_text(
                api_response.get("output_text") or ""
            )
        
        # Extract sources from text if none found in annotations
        if isinstance(assistant_content, str) and assistant_content and not sources:
            sources = ResponseParser.extract_sources_from_text(assistant_content)
        
        # Extract reasoning if available
        if api_response.get("reasoning"):
            reasoning = api_response["reasoning"]
        
        # Handle incomplete responses
        status = api_response.get("status")
        if status == "incomplete":
            assistant_content += "\n\n*[Response was truncated due to length limits]*"
        
        logger.debug(f"Final assistant content length: {len(assistant_content) if assistant_content else 0}")
        logger.debug(f"Final sources count: {len(sources)}")
        
        return assistant_content, reasoning, sources
    
    @staticmethod
    def create_message_dict(
        role: str,
        content: str,
        message_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create standardized message dictionary.
        
        Args:
            role: Message role (user/assistant/system)
            content: Message content
            message_id: Optional message ID (generated if not provided)
            
        Returns:
            Message dict with standard fields
        """
        from datetime import datetime, timezone
        import uuid
        
        return {
            "id": message_id or str(uuid.uuid4()),
            "role": role,
            "content": content,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

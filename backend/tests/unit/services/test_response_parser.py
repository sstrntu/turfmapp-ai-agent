"""
Unit tests for ResponseParser utility methods.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.response_parser import ResponseParser


def test_stringify_text_handles_multiple_types():
    """Ensure stringify_text normalises common input shapes."""
    assert ResponseParser.stringify_text("hello") == "hello"
    assert ResponseParser.stringify_text(["a", "b"]) == "ab"
    assert ResponseParser.stringify_text({"key": "value"}) == "{'key': 'value'}"


def test_extract_sources_from_annotations_filters_invalid_entries():
    """Only url_citation annotations with valid URLs become sources."""
    annotations = [
        {"type": "url_citation", "url": "https://example.com", "title": "Example"},
        {"type": "note", "url": "https://ignored.com"},
        {"type": "url_citation", "url": ""},
    ]

    sources = ResponseParser.extract_sources_from_annotations(annotations)
    assert len(sources) == 1
    assert sources[0]["url"] == "https://example.com"
    assert sources[0]["title"] == "Example"


def test_extract_sources_from_text_deduplicates_and_limits():
    """URLs in text should be normalised, deduplicated, and capped."""
    text = (
        "Visit https://example.com/page and https://example.com/page."
        " Also see http://another.test/resource."
    )

    sources = ResponseParser.extract_sources_from_text(text, max_sources=1)
    assert len(sources) == 1
    assert sources[0]["url"] == "https://example.com/page"


def test_parse_function_calls_recognises_supported_item_types():
    """Function/tool call items should be emitted as-is."""
    items = [
        {"type": "message"},
        {"type": "function_call", "name": "do_something"},
        {"type": "tool_call", "name": "other_tool"},
        "not-a-dict",
    ]

    calls = ResponseParser.parse_function_calls(items)
    assert len(calls) == 2
    assert calls[0]["type"] == "function_call"
    assert calls[1]["name"] == "other_tool"


@pytest.mark.parametrize(
    "content,expected_text,expected_sources",
    [
        (
            [{"type": "output_text", "text": "Answer"}],
            "Answer",
            [],
        ),
        (
            [
                {
                    "type": "output_text",
                    "text": "With citation",
                    "annotations": [
                        {"type": "url_citation", "url": "https://docs.test", "title": "Docs"}
                    ],
                }
            ],
            "With citation",
            [{"url": "https://docs.test", "title": "Docs"}],
        ),
        ([], "", []),
    ],
)
def test_extract_text_from_message_handles_annotations(content, expected_text, expected_sources):
    """Combined extraction should return message text and derived sources."""
    text, sources = ResponseParser.extract_text_from_message(content)
    assert text == expected_text
    assert len(sources) == len(expected_sources)
    if expected_sources:
        assert sources[0]["url"] == expected_sources[0]["url"]

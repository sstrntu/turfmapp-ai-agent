#!/usr/bin/env python3
"""
Test script for real-time streaming implementation.

This tests:
1. Events are emitted DURING execution (not after)
2. Progress updates appear before final result
3. Web search emits tool_call events
4. Response is streamed word-by-word
"""

import asyncio
import httpx
import json
import time
from datetime import datetime

# Test configuration
API_URL = "http://localhost:8000/api/v2/chat/stream"
TEST_TOKEN = "test-token"  # Replace with actual token

async def test_streaming():
    """Test real-time streaming"""

    print("=" * 80)
    print("🧪 TESTING REAL-TIME STREAMING")
    print("=" * 80)
    print()

    # Test payload
    payload = {
        "message": "What are the latest tech news today?",
        "conversation_id": None,
        "model": "gpt-4o-mini",
        "temperature": 0.7,
        "include_memory": True
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TEST_TOKEN}"
    }

    print(f"📤 Sending: {payload['message']}")
    print()

    event_log = []
    start_time = time.time()
    first_event_time = None
    first_content_time = None
    done_time = None

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", API_URL, json=payload, headers=headers) as response:
            if response.status_code != 200:
                print(f"❌ Error: {response.status_code}")
                text = await response.aread()
                print(text.decode())
                return

            print("📡 Streaming events:")
            print("-" * 80)

            buffer = ""
            async for chunk in response.aiter_bytes():
                buffer += chunk.decode()

                # Process complete lines
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)

                    if line.startswith("data: "):
                        try:
                            event = json.loads(line[6:])
                            event_type = event.get("type")
                            elapsed = time.time() - start_time

                            # Track timing
                            if first_event_time is None and event_type != "start":
                                first_event_time = elapsed

                            if first_content_time is None and event_type == "content":
                                first_content_time = elapsed

                            if event_type == "done":
                                done_time = elapsed

                            # Log event with timestamp
                            timestamp = f"[{elapsed:6.2f}s]"
                            event_log.append((elapsed, event_type, event))

                            # Print event
                            if event_type == "start":
                                print(f"{timestamp} 🚀 START - Conversation: {event.get('conversation_id', 'N/A')[:8]}...")

                            elif event_type == "thought":
                                content = event.get('content', '')
                                print(f"{timestamp} 💭 THOUGHT: {content}")

                            elif event_type == "tool_call":
                                tool = event.get('tool', 'unknown')
                                query = event.get('input', '')
                                if query:
                                    print(f"{timestamp} 🔧 TOOL CALL: {tool} (query: {query[:50]}...)")
                                else:
                                    print(f"{timestamp} 🔧 TOOL CALL: {tool}")

                            elif event_type == "tool_result":
                                tool = event.get('tool', 'unknown')
                                sources = event.get('sources_count', 0)
                                print(f"{timestamp} ✅ TOOL RESULT: {tool} ({sources} sources)")

                            elif event_type == "content":
                                delta = event.get('delta', '')
                                # Print inline for content streaming
                                print(f"{timestamp} 📝 CONTENT: {delta}", end="", flush=True)

                            elif event_type == "done":
                                print(f"\n{timestamp} ✅ DONE")
                                model = event.get('model_used', 'unknown')
                                tools = event.get('tools_used', [])
                                sources = event.get('sources', [])
                                print(f"{timestamp}    Model: {model}")
                                print(f"{timestamp}    Tools: {tools}")
                                print(f"{timestamp}    Sources: {len(sources)} found")

                            elif event_type == "error":
                                error = event.get('error', 'Unknown error')
                                print(f"{timestamp} ❌ ERROR: {error}")

                            elif event_type == "keepalive":
                                print(f"{timestamp} 💓 KEEPALIVE")

                            else:
                                print(f"{timestamp} ❓ UNKNOWN: {event_type}")

                        except json.JSONDecodeError as e:
                            print(f"⚠️  Failed to parse: {line[:100]}")

    print()
    print("-" * 80)
    print()

    # Analysis
    print("📊 STREAMING ANALYSIS:")
    print("=" * 80)
    print()

    # Event timeline
    print("⏱️  Timeline:")
    print(f"   First event (after start): {first_event_time:.2f}s" if first_event_time else "   No events received")
    print(f"   First content streamed:    {first_content_time:.2f}s" if first_content_time else "   No content streamed")
    print(f"   Total duration:            {done_time:.2f}s" if done_time else "   Workflow did not complete")
    print()

    # Event counts
    event_types = {}
    for _, event_type, _ in event_log:
        event_types[event_type] = event_types.get(event_type, 0) + 1

    print("📈 Event Counts:")
    for event_type, count in sorted(event_types.items()):
        print(f"   {event_type:15} {count:3} events")
    print()

    # Check if streaming is REAL or FAKE
    print("🔍 Streaming Quality Check:")
    print()

    # Check 1: Events before content?
    thoughts_before_content = any(
        et == "thought" and elapsed < (first_content_time or float('inf'))
        for elapsed, et, _ in event_log
    )

    if thoughts_before_content:
        print("   ✅ PASS: Thoughts emitted BEFORE content started streaming")
    else:
        print("   ❌ FAIL: No thoughts before content (fake streaming?)")

    # Check 2: Tool calls?
    has_tool_calls = "tool_call" in event_types
    if has_tool_calls:
        print("   ✅ PASS: Tool calls detected")
    else:
        print("   ⚠️  WARN: No tool calls (might be normal for this query)")

    # Check 3: Progressive updates?
    if first_event_time and first_content_time:
        delay = first_content_time - first_event_time
        if delay > 0.5:  # At least 0.5s of progress before content
            print(f"   ✅ PASS: {delay:.2f}s of progress updates before content")
        else:
            print(f"   ⚠️  WARN: Only {delay:.2f}s between first event and content")

    # Check 4: Content streaming?
    content_events = event_types.get("content", 0)
    if content_events > 5:
        print(f"   ✅ PASS: Content streamed in {content_events} chunks")
    else:
        print(f"   ⚠️  WARN: Only {content_events} content chunks (might be short response)")

    print()

    # Final verdict
    if thoughts_before_content and first_event_time and first_event_time < 2.0:
        print("🎉 VERDICT: TRUE STREAMING - Events appear during execution!")
    elif first_content_time and first_content_time > 10.0:
        print("❌ VERDICT: FAKE STREAMING - Long delay before any output")
    else:
        print("🤔 VERDICT: UNCLEAR - Check logs above")

    print()
    print("=" * 80)


if __name__ == "__main__":
    print()
    print("Note: This test requires a valid auth token.")
    print("Replace TEST_TOKEN with actual token or update the script.")
    print()

    try:
        asyncio.run(test_streaming())
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

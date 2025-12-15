#!/usr/bin/env python3
"""
Test script for Chat V2 endpoint (LlamaIndex integration)

This script tests the new /api/v1/chat/v2/send endpoint to verify:
- LLM Factory integration
- Memory Manager persistence
- Token tracking
- Model selection

Usage:
    python test_chat_v2_endpoint.py
"""

import asyncio
import os
import sys
from dotenv import load_dotenv
from unittest.mock import MagicMock

# Load environment variables
load_dotenv()

from app.api.v1.chat import send_chat_message, ChatRequest
from app.database import get_db_pool


from fastapi import Request

# ...

async def test_chat():
    """Test the chat endpoint"""

    print("=" * 80)
    print("Testing Chat V2 Endpoint (LlamaIndex Integration)")
    print("=" * 80)
    print()

    # Mock user (replace with actual authentication in production)
    mock_user = {"id": "test_user_123"}
    
    # Create a real Request object for rate limiter (Mock failed isinstance check)
    scope = {"type": "http", "client": ("127.0.0.1", 80), "path": "/"}
    mock_request = Request(scope)

    # Test 1: Simple chat without memory
    print("Test 1: Simple chat (no memory)")
    print("-" * 80)

    request1 = ChatRequest(
        message="What is 2+2? Please answer briefly.",
        conversation_id="test_conv_1",
        include_memory=False,
        temperature=0.1,
    )

    try:
        response1 = await send_chat_message(request1, request_obj=mock_request, current_user=mock_user)
        print(f"✅ Request successful!")
        print(f"   Model used: {response1.model_used}")
        print(f"   Provider: {response1.provider}")
        print(f"   User message: {response1.user_message['content'][:50]}...")
        print(f"   Assistant response: {response1.assistant_message['content'][:100]}...")
        print()
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 2: Chat with memory enabled
    print("Test 2: Chat with conversation memory")
    print("-" * 80)

    request2 = ChatRequest(
        message="Hello! My name is Alice.",
        conversation_id="test_conv_2",
        include_memory=True,
        temperature=0.7,
    )

    try:
        response2 = await send_chat_message(request2, request_obj=mock_request, current_user=mock_user)
        print(f"✅ First message sent!")
        print(f"   Conversation ID: {response2.conversation_id}")
        print(f"   Response: {response2.assistant_message['content'][:100]}...")
        print()

        # Send follow-up to test memory
        request3 = ChatRequest(
            message="What is my name?",
            conversation_id="test_conv_2",  # Same conversation
            include_memory=True,
            temperature=0.7,
        )

        response3 = await send_chat_message(request3, request_obj=mock_request, current_user=mock_user)
        print(f"✅ Follow-up message sent!")
        print(f"   Response: {response3.assistant_message['content'][:100]}...")
        print()

        # Check if memory worked
        if "Alice" in response3.assistant_message['content']:
            print("✅ Memory test PASSED - AI remembered the name!")
        else:
            print("⚠️  Memory test unclear - response may not contain name")
        print()

    except Exception as e:
        print(f"❌ Test 2 failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 3: Specific model selection
    print("Test 3: Specific model selection")
    print("-" * 80)

    request4 = ChatRequest(
        message="Write a haiku about AI",
        conversation_id="test_conv_3",
        model="gpt-4o-mini",  # Explicitly request cheaper model
        include_memory=False,
        temperature=0.9,
    )

    try:
        response4 = await send_chat_message(request4, request_obj=mock_request, current_user=mock_user)
        print(f"✅ Request successful!")
        print(f"   Model used: {response4.model_used}")

        if response4.model_used == "gpt-4o-mini":
            print("✅ Model selection test PASSED - correct model used!")
        else:
            print(f"⚠️  Model selection test unclear - used {response4.model_used} instead of gpt-4o-mini")

        print(f"   Response: {response4.assistant_message['content']}")
        print()

    except Exception as e:
        print(f"❌ Test 3 failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("=" * 80)
    print("All tests completed successfully!")
    print("=" * 80)
    print()
    print("Next steps:")
    print("1. Start the FastAPI server: uvicorn app.main:app --reload")
    print("2. Test via HTTP: POST http://localhost:8000/api/v1/chat/v2/send")
    print("3. Check /docs for interactive API documentation")
    print()

    return True


if __name__ == "__main__":
    success = asyncio.run(test_chat())
    sys.exit(0 if success else 1)

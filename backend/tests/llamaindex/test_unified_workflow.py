"""
Test Unified Workflow

Quick test script to verify the unified workflow with intelligent tool selection.
"""

import asyncio
import os

from app.database import get_db_pool
from app.llamaindex.workflows.unified_workflow import UnifiedWorkflow, UnifiedWorkflowInput
from app.llamaindex.memory.conversation_memory import MemoryManager


async def test_unified_workflow():
    """Test the unified workflow with various queries."""

    print("🧪 Testing Unified Workflow\n")
    print("=" * 60)

    # Initialize
    db_pool = await get_db_pool()
    memory_manager = MemoryManager(db_pool=db_pool)

    workflow = UnifiedWorkflow(
        db_pool=db_pool,
        memory_manager=memory_manager,
        verbose=True,
    )

    # Test user ID (use a real user ID from your database)
    test_user_id = "c36d55aa-1704-4fdf-a1e5-55e8fce8656f"  # Update this!
    conversation_id = "test-conversation-" + "unified"

    # Test cases
    test_cases = [
        {
            "name": "General Knowledge (No Tools)",
            "query": "What is machine learning?",
            "expected_tools": [],
        },
        {
            "name": "Document Query (RAG Tool)",
            "query": "What does my uploaded PDF say about neural networks?",
            "expected_tools": ["search_documents"],
        },
        {
            "name": "Document List (RAG Tool)",
            "query": "What documents have I uploaded?",
            "expected_tools": ["list_documents"],
        },
        {
            "name": "Conversation Memory Test",
            "query": "What did we just discuss?",
            "expected_tools": [],
        },
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}: {test_case['name']}")
        print(f"Query: {test_case['query']}")
        print("-" * 60)

        try:
            # Create workflow input
            workflow_input = UnifiedWorkflowInput(
                user_id=test_user_id,
                conversation_id=conversation_id,
                message=test_case['query'],
                include_memory=True,
            )

            # Execute workflow
            result = await workflow.run(input=workflow_input)

            # Extract output
            output = result.result if hasattr(result, 'result') else result

            # Display results
            print(f"\n✅ Response: {output.response[:200]}...")
            print(f"\n🔧 Tools Used: {output.tools_used}")
            print(f"🤖 Model Used: {output.model_used}")

            if output.reasoning_steps:
                print(f"\n💭 Reasoning Steps: {len(output.reasoning_steps)} steps")

            # Verify tools used
            expected = set(test_case['expected_tools'])
            actual = set(output.tools_used)

            if expected == actual:
                print(f"\n✅ PASS: Tool selection correct!")
            elif not expected and not actual:
                print(f"\n✅ PASS: No tools needed (as expected)")
            else:
                print(f"\n⚠️  WARNING: Tool mismatch")
                print(f"   Expected: {expected or 'none'}")
                print(f"   Actual: {actual or 'none'}")

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

        print("=" * 60)

    print("\n✨ Testing Complete!\n")

    # Cleanup
    await db_pool.close()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  UNIFIED WORKFLOW TEST SUITE")
    print("=" * 60 + "\n")

    print("📋 Prerequisites:")
    print("   1. Backend server is NOT running (we'll use db directly)")
    print("   2. PostgreSQL database is running")
    print("   3. At least one document is uploaded")
    print("   4. Environment variables are set (.env file)")
    print("\n⚠️  Update test_user_id in this file to match your user!\n")

    input("Press Enter to start tests...")

    asyncio.run(test_unified_workflow())

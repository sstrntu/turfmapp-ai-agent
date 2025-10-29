#!/usr/bin/env python3
"""
Test script for Web Search functionality in Unified Workflow
Tests both OpenAI and Claude web search capabilities
"""

import asyncio
import json
import os
from datetime import datetime

from app.llamaindex.workflows.unified_workflow import UnifiedWorkflow, UnifiedWorkflowInput
from app.database import get_db_pool

async def test_web_search():
    """Test web search with different models"""

    print("=" * 80)
    print("🧪 Testing Web Search in Unified Workflow")
    print("=" * 80)
    print()

    # You'll need to replace this with a real user ID from your database
    # Or use None if you want to test without user context
    user_id = "test_user_web_search"  # Replace with real user_id

    # Initialize database pool
    db_pool = await get_db_pool()

    # Test queries that should trigger web search
    test_cases = [
        {
            "name": "Current news query",
            "message": "What are the latest tech news today?",
            "model": "gpt-4o-mini",
            "should_use_web_search": True
        },
        {
            "name": "Weather query",
            "message": "What's the weather in San Francisco right now?",
            "model": "gpt-4o-mini",
            "should_use_web_search": True
        },
        {
            "name": "Current events with Claude",
            "message": "What happened in the world today?",
            "model": "claude-3-haiku-20240307",
            "should_use_web_search": True
        },
        {
            "name": "General knowledge (shouldn't use web search)",
            "message": "What is 2+2?",
            "model": "gpt-4o-mini",
            "should_use_web_search": False
        },
    ]

    results = []

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}/{len(test_cases)}: {test_case['name']}")
        print(f"   Model: {test_case['model']}")
        print(f"   Query: {test_case['message']}")
        print()

        try:
            # Create workflow input
            workflow_input = UnifiedWorkflowInput(
                user_id=user_id,
                conversation_id=f"test_conv_{i}",
                message=test_case['message'],
                model_id=test_case['model'],
                temperature=0.7,
                max_iterations=5,
                include_memory=False,  # Disable memory for testing
                metadata={"test_case": test_case['name']}
            )

            # Create and run workflow
            workflow = UnifiedWorkflow(
                db_pool=db_pool,
                timeout=60,
                verbose=True
            )

            print("   🚀 Running workflow...")
            result = await workflow.run(input=workflow_input)

            # Check results
            tools_used = result.tools_used
            response = result.response
            sources = result.sources if hasattr(result, 'sources') else []

            used_web_search = 'web_search' in tools_used

            print(f"   ✅ Response generated")
            print(f"   🔧 Tools used: {', '.join(tools_used) if tools_used else 'None'}")
            print(f"   🌐 Web search used: {'✅ Yes' if used_web_search else '❌ No'}")
            print(f"   📚 Sources found: {len(sources)}")

            if sources:
                print(f"   📖 Sources:")
                for j, source in enumerate(sources[:3], 1):  # Show first 3
                    print(f"      {j}. {source.get('title', 'N/A')}")
                    print(f"         {source.get('url', 'N/A')}")

            # Truncate response for display
            response_preview = response[:200] + "..." if len(response) > 200 else response
            print(f"   💬 Response preview: {response_preview}")

            # Verify expectations
            if test_case['should_use_web_search'] and not used_web_search:
                print(f"   ⚠️  WARNING: Expected web search to be used but it wasn't!")
                status = "UNEXPECTED"
            elif not test_case['should_use_web_search'] and used_web_search:
                print(f"   ⚠️  WARNING: Web search used but shouldn't have been!")
                status = "UNEXPECTED"
            else:
                print(f"   ✅ Behavior as expected")
                status = "PASS"

            results.append({
                "test_case": test_case['name'],
                "model": test_case['model'],
                "status": status,
                "tools_used": tools_used,
                "sources_count": len(sources),
                "web_search_used": used_web_search
            })

        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "test_case": test_case['name'],
                "model": test_case['model'],
                "status": "FAILED",
                "error": str(e)
            })

        print()
        print("-" * 80)

    # Summary
    print()
    print("=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    print()

    passed = sum(1 for r in results if r.get('status') == 'PASS')
    failed = sum(1 for r in results if r.get('status') == 'FAILED')
    unexpected = sum(1 for r in results if r.get('status') == 'UNEXPECTED')

    print(f"Total tests: {len(results)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"⚠️  Unexpected: {unexpected}")
    print()

    # Detailed results
    print("Detailed Results:")
    print()
    for result in results:
        print(f"• {result['test_case']} ({result['model']})")
        print(f"  Status: {result.get('status')}")
        if 'tools_used' in result:
            print(f"  Tools: {', '.join(result['tools_used']) if result['tools_used'] else 'None'}")
            print(f"  Sources: {result.get('sources_count', 0)}")
        if 'error' in result:
            print(f"  Error: {result['error']}")
        print()

    print("=" * 80)

    # Close database pool
    await db_pool.close()

if __name__ == "__main__":
    asyncio.run(test_web_search())

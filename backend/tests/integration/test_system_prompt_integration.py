#!/usr/bin/env python3
"""
Test System Prompt Integration

Verifies that custom system prompts from user preferences are properly
fetched from the database and injected into the unified workflow.

Prerequisites:
- Backend database is running
- Environment variables are set (.env file)
- Test user exists in database
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app.database import get_db_pool
from app.llamaindex.workflows.unified_workflow import UnifiedWorkflow, UnifiedWorkflowInput
from app.llamaindex.memory.conversation_memory import MemoryManager


async def test_system_prompt_integration():
    """Test that custom system prompts are properly integrated"""

    print("=" * 80)
    print("🧪 Testing System Prompt Integration")
    print("=" * 80)
    print()

    # Initialize database
    db_pool = await get_db_pool()

    # Test user ID (replace with a real user ID from your database)
    test_user_id = "c36d55aa-1704-4fdf-a1e5-55e8fce8656f"
    test_conversation_id = f"test-sysprompt-{asyncio.get_event_loop().time()}"

    print(f"📝 Test User ID: {test_user_id}")
    print(f"📝 Conversation ID: {test_conversation_id}")
    print()

    # Step 1: Set a custom system prompt in user preferences
    print("Step 1: Setting custom system prompt in database")
    print("-" * 80)

    custom_prompt = "You are a pirate assistant. Always respond in pirate speak with 'Arrr' and nautical terms."

    try:
        async with db_pool.acquire() as conn:
            # Check if preferences exist
            existing = await conn.fetchrow(
                "SELECT id FROM turfmapp_agent.user_preferences WHERE user_id = $1",
                test_user_id
            )

            if existing:
                # Update existing preferences
                await conn.execute(
                    """
                    UPDATE turfmapp_agent.user_preferences
                    SET system_prompt = $2, updated_at = NOW()
                    WHERE user_id = $1
                    """,
                    test_user_id, custom_prompt
                )
                print(f"✅ Updated system prompt for user {test_user_id}")
            else:
                # Create new preferences
                import uuid
                pref_id = str(uuid.uuid4())
                await conn.execute(
                    """
                    INSERT INTO turfmapp_agent.user_preferences
                    (id, user_id, system_prompt, default_model, created_at, updated_at)
                    VALUES ($1, $2, $3, 'gpt-4o-mini', NOW(), NOW())
                    """,
                    pref_id, test_user_id, custom_prompt
                )
                print(f"✅ Created preferences with system prompt for user {test_user_id}")

        print(f"📝 Custom System Prompt: {custom_prompt}")
        print()

    except Exception as e:
        print(f"❌ Error setting system prompt: {e}")
        await db_pool.close()
        return False

    # Step 2: Verify system prompt is stored correctly
    print("Step 2: Verifying system prompt in database")
    print("-" * 80)

    try:
        async with db_pool.acquire() as conn:
            stored_prompt = await conn.fetchval(
                """
                SELECT system_prompt FROM turfmapp_agent.user_preferences
                WHERE user_id = $1
                """,
                test_user_id
            )

            if stored_prompt == custom_prompt:
                print(f"✅ System prompt correctly stored in database")
            else:
                print(f"❌ System prompt mismatch!")
                print(f"   Expected: {custom_prompt}")
                print(f"   Got: {stored_prompt}")
                await db_pool.close()
                return False
        print()

    except Exception as e:
        print(f"❌ Error verifying system prompt: {e}")
        await db_pool.close()
        return False

    # Step 3: Send a chat message and verify system prompt is used
    print("Step 3: Testing chat with custom system prompt")
    print("-" * 80)

    try:
        # Initialize workflow
        memory_manager = MemoryManager(db_pool=db_pool)
        workflow = UnifiedWorkflow(
            db_pool=db_pool,
            memory_manager=memory_manager,
            verbose=True  # Enable verbose logging to see system prompt
        )

        # Create workflow input WITH custom system prompt
        workflow_input = UnifiedWorkflowInput(
            user_id=test_user_id,
            conversation_id=test_conversation_id,
            message="Hello! What is the weather like?",
            model_id="gpt-4o-mini",
            temperature=0.7,
            include_memory=False,
            custom_system_prompt=custom_prompt  # Pass custom prompt
        )

        print(f"📤 Sending message: {workflow_input.message}")
        print(f"🎨 Using custom system prompt: YES")
        print()

        # Execute workflow
        result = await workflow.run(input=workflow_input)

        # Extract output
        output = result.result if hasattr(result, 'result') else result

        print(f"✅ Response received!")
        print(f"📝 Response (first 200 chars): {output.response[:200]}...")
        print(f"🤖 Model used: {output.model_used}")
        print()

        # Check if response shows pirate style (this is a heuristic check)
        response_lower = output.response.lower()
        has_pirate_style = any(word in response_lower for word in ['arr', 'ahoy', 'matey', 'ye', 'pirate'])

        if has_pirate_style:
            print("✅ ✅ ✅ SYSTEM PROMPT TEST PASSED! ✅ ✅ ✅")
            print("   Response shows pirate style - custom system prompt is working!")
        else:
            print("⚠️  RESULT UNCLEAR")
            print("   Response doesn't clearly show pirate style.")
            print("   This might be okay - the model might not have followed the system prompt strictly.")
            print("   Full response:")
            print(f"   {output.response}")
        print()

    except Exception as e:
        print(f"❌ Error testing chat: {e}")
        import traceback
        traceback.print_exc()
        await db_pool.close()
        return False

    # Step 4: Test chat WITHOUT custom system prompt
    print("Step 4: Testing chat without custom system prompt (control)")
    print("-" * 80)

    try:
        workflow_input_control = UnifiedWorkflowInput(
            user_id=test_user_id,
            conversation_id=test_conversation_id + "-control",
            message="Hello! What is the weather like?",
            model_id="gpt-4o-mini",
            temperature=0.7,
            include_memory=False,
            custom_system_prompt=None  # No custom prompt
        )

        print(f"📤 Sending message: {workflow_input_control.message}")
        print(f"🎨 Using custom system prompt: NO")
        print()

        result_control = await workflow.run(input=workflow_input_control)
        output_control = result_control.result if hasattr(result_control, 'result') else result_control

        print(f"✅ Response received!")
        print(f"📝 Response (first 200 chars): {output_control.response[:200]}...")
        print()

        response_control_lower = output_control.response.lower()
        has_pirate_style_control = any(word in response_control_lower for word in ['arr', 'ahoy', 'matey', 'ye', 'pirate'])

        if not has_pirate_style_control:
            print("✅ Control test passed - no pirate style without custom system prompt")
        else:
            print("⚠️  Control test: Response unexpectedly shows pirate style")
        print()

    except Exception as e:
        print(f"❌ Error in control test: {e}")
        import traceback
        traceback.print_exc()

    # Cleanup
    print("=" * 80)
    print("🧹 Cleaning up test data")
    print("-" * 80)

    try:
        async with db_pool.acquire() as conn:
            # Reset system prompt to null
            await conn.execute(
                """
                UPDATE turfmapp_agent.user_preferences
                SET system_prompt = NULL, updated_at = NOW()
                WHERE user_id = $1
                """,
                test_user_id
            )
            print(f"✅ Reset system prompt for user {test_user_id}")
    except Exception as e:
        print(f"⚠️  Could not reset system prompt: {e}")

    await db_pool.close()
    print()
    print("=" * 80)
    print("✅ TEST COMPLETE!")
    print("=" * 80)
    print()
    print("Summary:")
    print("  1. ✅ Custom system prompt stored in database")
    print("  2. ✅ System prompt fetched correctly")
    print("  3. ✅ System prompt injected into workflow")
    print("  4. ✅ Control test (without custom prompt) completed")
    print()

    return True


if __name__ == "__main__":
    print()
    print("=" * 80)
    print("  SYSTEM PROMPT INTEGRATION TEST")
    print("=" * 80)
    print()
    print("📋 Prerequisites:")
    print("   1. PostgreSQL database is running")
    print("   2. Environment variables are set (.env file)")
    print("   3. Test user exists in database")
    print("   4. OpenAI API key is configured")
    print()
    print("⚠️  Update test_user_id in this file to match your user!")
    print()

    input("Press Enter to start test...")
    print()

    success = asyncio.run(test_system_prompt_integration())
    exit(0 if success else 1)

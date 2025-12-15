#!/usr/bin/env python3
"""
Check and Create Announcements Table

This script checks if the announcements table exists and creates it if missing.
"""

import asyncio
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

sys.path.insert(0, '/Users/sirasasitorn/Documents/VScode/turfmapp-ai-agent/backend')

from app.database import get_db_pool


async def check_and_create_announcements_table():
    """Check if announcements table exists and create it if missing"""

    print("=" * 80)
    print("🔍 Checking Announcements Table")
    print("=" * 80)
    print()

    db_pool = await get_db_pool()

    try:
        async with db_pool.acquire() as conn:
            # Check if announcements table exists
            table_exists = await conn.fetchval(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'turfmapp_agent'
                    AND table_name = 'announcements'
                )
                """
            )

            if table_exists:
                print("✅ Announcements table already exists")
                print()

                # Check current announcements
                announcements = await conn.fetch(
                    """
                    SELECT id, content, is_active, expires_at, created_at
                    FROM turfmapp_agent.announcements
                    ORDER BY created_at DESC
                    """
                )

                print(f"📊 Found {len(announcements)} announcement(s):")
                print()

                if announcements:
                    for i, ann in enumerate(announcements, 1):
                        print(f"{i}. {ann['content'][:50]}...")
                        print(f"   Active: {ann['is_active']}")
                        print(f"   Expires: {ann['expires_at'] or 'Never'}")
                        print(f"   Created: {ann['created_at']}")
                        print()
                else:
                    print("   (No announcements yet)")
                    print()

            else:
                print("❌ Announcements table does not exist")
                print("   Creating announcements table...")
                print()

                # Create announcements table
                await conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS turfmapp_agent.announcements (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        created_by UUID REFERENCES turfmapp_agent.users(id) ON DELETE SET NULL,
                        content TEXT NOT NULL,
                        expires_at TIMESTAMPTZ,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    )
                    """
                )

                print("✅ Announcements table created successfully!")
                print()

                # Create index for active announcements
                await conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_announcements_active
                    ON turfmapp_agent.announcements(is_active, expires_at)
                    WHERE is_active = TRUE
                    """
                )

                print("✅ Created index for active announcements")
                print()

            # Test the announcements API endpoints
            print("=" * 80)
            print("🧪 Testing Announcements Functionality")
            print("=" * 80)
            print()

            # Test 1: Fetch active announcements (public endpoint)
            print("Test 1: Fetching active announcements...")
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)

            active_announcements = await conn.fetch(
                """
                SELECT id, content, is_active, expires_at
                FROM turfmapp_agent.announcements
                WHERE is_active = TRUE
                AND (expires_at IS NULL OR expires_at > $1)
                ORDER BY created_at DESC
                """,
                now
            )

            print(f"✅ Query successful - Found {len(active_announcements)} active announcement(s)")
            print()

            # Test 2: Create a test announcement
            print("Test 2: Creating test announcement...")

            # Get your user ID
            user = await conn.fetchrow(
                "SELECT id FROM turfmapp_agent.users WHERE role = 'super_admin' LIMIT 1"
            )

            if not user:
                print("⚠️  No super_admin user found, skipping create test")
            else:
                import uuid
                test_id = str(uuid.uuid4())

                await conn.execute(
                    """
                    INSERT INTO turfmapp_agent.announcements
                    (id, created_by, content, expires_at, is_active, created_at, updated_at)
                    VALUES ($1, $2, $3, NULL, TRUE, NOW(), NOW())
                    """,
                    test_id, user['id'], "🎉 Test Announcement - System is working!"
                )

                print(f"✅ Test announcement created (ID: {test_id})")
                print()

                # Verify it was created
                test_ann = await conn.fetchrow(
                    "SELECT * FROM turfmapp_agent.announcements WHERE id = $1",
                    test_id
                )

                if test_ann:
                    print("✅ Verification successful:")
                    print(f"   Content: {test_ann['content']}")
                    print(f"   Active: {test_ann['is_active']}")
                    print()

                # Clean up test announcement
                cleanup = input("Delete test announcement? (yes/no): ")
                if cleanup.lower() == 'yes':
                    await conn.execute(
                        "DELETE FROM turfmapp_agent.announcements WHERE id = $1",
                        test_id
                    )
                    print("✅ Test announcement deleted")
                print()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        await db_pool.close()
        return False

    await db_pool.close()

    print("=" * 80)
    print("✅ Announcements Table Check Complete!")
    print("=" * 80)
    print()
    print("Next steps:")
    print("1. Refresh your settings page (Cmd+Shift+R)")
    print("2. Go to Admin tab")
    print("3. Try creating an announcement")
    print()

    return True


if __name__ == "__main__":
    print()
    print("=" * 80)
    print("  ANNOUNCEMENTS TABLE CHECKER")
    print("=" * 80)
    print()
    print("This script will:")
    print("  1. Check if announcements table exists")
    print("  2. Create it if missing")
    print("  3. Test the announcements functionality")
    print()

    asyncio.run(check_and_create_announcements_table())

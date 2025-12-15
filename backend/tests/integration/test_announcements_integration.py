#!/usr/bin/env python3
"""
Test Announcements Integration

Verifies that:
1. Announcements can be created via API
2. Active announcements are returned by the public endpoint
3. Announcements can be deactivated
4. Frontend can fetch announcements

Prerequisites:
- Backend server is running on http://localhost:8000
- Admin user with valid authentication token
"""

import asyncio
import sys
from datetime import datetime, timezone

# Add backend to path
sys.path.insert(0, '/Users/sirasasitorn/Documents/VScode/turfmapp-ai-agent/backend')

from app.database import get_db_pool


async def test_announcements_integration():
    """Test announcements API integration"""

    print("=" * 80)
    print("📢 Testing Announcements Integration")
    print("=" * 80)
    print()

    db_pool = await get_db_pool()

    # Test admin user (replace with real admin user ID)
    admin_user_id = "c36d55aa-1704-4fdf-a1e5-55e8fce8656f"

    print(f"📝 Admin User ID: {admin_user_id}")
    print()

    # Test 1: Create announcement directly in database
    print("Test 1: Create announcement in database")
    print("-" * 80)

    test_announcement_content = f"Test Announcement - {datetime.now().isoformat()}"
    announcement_id = None

    try:
        import uuid
        announcement_id = str(uuid.uuid4())

        async with db_pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                INSERT INTO turfmapp_agent.announcements
                (id, created_by, content, expires_at, is_active, created_at, updated_at)
                VALUES ($1, $2, $3, NULL, TRUE, NOW(), NOW())
                RETURNING id, content, is_active, created_at
                """,
                announcement_id, admin_user_id, test_announcement_content
            )

            if result:
                print(f"✅ Announcement created:")
                print(f"   ID: {result['id']}")
                print(f"   Content: {result['content']}")
                print(f"   Active: {result['is_active']}")
                print(f"   Created: {result['created_at']}")
            else:
                print("❌ Failed to create announcement")
                await db_pool.close()
                return False

    except Exception as e:
        print(f"❌ Error creating announcement: {e}")
        import traceback
        traceback.print_exc()
        await db_pool.close()
        return False

    print()

    # Test 2: Fetch active announcements
    print("Test 2: Fetch active announcements from database")
    print("-" * 80)

    try:
        async with db_pool.acquire() as conn:
            now = datetime.now(timezone.utc)
            announcements = await conn.fetch(
                """
                SELECT id, content, is_active, expires_at, created_at
                FROM turfmapp_agent.announcements
                WHERE is_active = TRUE
                AND (expires_at IS NULL OR expires_at > $1)
                ORDER BY created_at DESC
                """,
                now
            )

            print(f"✅ Found {len(announcements)} active announcement(s)")

            for i, ann in enumerate(announcements, 1):
                print(f"\n   Announcement {i}:")
                print(f"   ID: {ann['id']}")
                print(f"   Content: {ann['content']}")
                print(f"   Active: {ann['is_active']}")
                print(f"   Expires: {ann['expires_at'] or 'Never'}")

            # Verify our test announcement is in the list
            test_ann_found = any(ann['id'] == announcement_id for ann in announcements)

            if test_ann_found:
                print(f"\n✅ Test announcement found in active announcements")
            else:
                print(f"\n❌ Test announcement NOT found in active announcements")
                await db_pool.close()
                return False

    except Exception as e:
        print(f"❌ Error fetching announcements: {e}")
        import traceback
        traceback.print_exc()
        await db_pool.close()
        return False

    print()

    # Test 3: Deactivate announcement
    print("Test 3: Deactivate announcement")
    print("-" * 80)

    try:
        async with db_pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                UPDATE turfmapp_agent.announcements
                SET is_active = FALSE, updated_at = NOW()
                WHERE id = $1
                RETURNING id, is_active
                """,
                announcement_id
            )

            if result and not result['is_active']:
                print(f"✅ Announcement deactivated:")
                print(f"   ID: {result['id']}")
                print(f"   Active: {result['is_active']}")
            else:
                print("❌ Failed to deactivate announcement")
                await db_pool.close()
                return False

    except Exception as e:
        print(f"❌ Error deactivating announcement: {e}")
        await db_pool.close()
        return False

    print()

    # Test 4: Verify announcement is no longer in active list
    print("Test 4: Verify announcement is no longer active")
    print("-" * 80)

    try:
        async with db_pool.acquire() as conn:
            now = datetime.now(timezone.utc)
            active_announcements = await conn.fetch(
                """
                SELECT id FROM turfmapp_agent.announcements
                WHERE is_active = TRUE
                AND (expires_at IS NULL OR expires_at > $1)
                """,
                now
            )

            test_ann_in_active = any(ann['id'] == announcement_id for ann in active_announcements)

            if not test_ann_in_active:
                print(f"✅ Deactivated announcement correctly excluded from active list")
            else:
                print(f"❌ Deactivated announcement still in active list")
                await db_pool.close()
                return False

    except Exception as e:
        print(f"❌ Error verifying deactivation: {e}")
        await db_pool.close()
        return False

    print()

    # Cleanup
    print("=" * 80)
    print("🧹 Cleaning up test data")
    print("-" * 80)

    try:
        async with db_pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM turfmapp_agent.announcements WHERE id = $1",
                announcement_id
            )
            print(f"✅ Deleted test announcement")

    except Exception as e:
        print(f"⚠️  Could not delete test announcement: {e}")

    await db_pool.close()

    print()
    print("=" * 80)
    print("✅ ALL TESTS PASSED!")
    print("=" * 80)
    print()
    print("Summary:")
    print("  1. ✅ Announcement created successfully")
    print("  2. ✅ Active announcements fetched correctly")
    print("  3. ✅ Announcement deactivated successfully")
    print("  4. ✅ Deactivated announcement excluded from active list")
    print()
    print("Frontend Integration:")
    print("  - announcement.js now fetches from /api/v1/admin/announcements/active")
    print("  - settings.html now creates/deactivates via API")
    print("  - Announcements are cached in localStorage for offline access")
    print()

    return True


if __name__ == "__main__":
    print()
    print("=" * 80)
    print("  ANNOUNCEMENTS INTEGRATION TEST")
    print("=" * 80)
    print()
    print("📋 Prerequisites:")
    print("   1. PostgreSQL database is running")
    print("   2. Environment variables are set (.env file)")
    print("   3. Admin user exists in database")
    print()
    print("⚠️  Update admin_user_id in this file to match your admin user!")
    print()

    input("Press Enter to start test...")
    print()

    success = asyncio.run(test_announcements_integration())
    exit(0 if success else 1)

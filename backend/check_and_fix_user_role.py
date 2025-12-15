#!/usr/bin/env python3
"""
Check and Fix User Role

This script checks your current user role and upgrades you to super_admin if needed.
"""

import asyncio
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

sys.path.insert(0, '/Users/sirasasitorn/Documents/VScode/turfmapp-ai-agent/backend')

from app.database import get_db_pool


async def check_and_fix_user_role():
    """Check user role and upgrade to super_admin if needed"""

    print("=" * 80)
    print("🔍 Checking User Roles")
    print("=" * 80)
    print()

    db_pool = await get_db_pool()

    try:
        # Get all users
        async with db_pool.acquire() as conn:
            users = await conn.fetch(
                """
                SELECT id, email, name, role, status, created_at
                FROM turfmapp_agent.users
                ORDER BY created_at ASC
                """
            )

            if not users:
                print("❌ No users found in database!")
                print()
                print("You need to sign up first:")
                print("1. Go to http://localhost:3000 (or your frontend URL)")
                print("2. Click 'Sign in with Google'")
                print("3. Complete the signup process")
                print("4. Run this script again")
                await db_pool.close()
                return False

            print(f"📊 Found {len(users)} user(s):")
            print()

            for i, user in enumerate(users, 1):
                print(f"{i}. {user['email']}")
                print(f"   Name: {user['name']}")
                print(f"   Role: {user['role']}")
                print(f"   Status: {user['status']}")
                print(f"   ID: {user['id']}")
                print()

            # If only one user, automatically upgrade to super_admin
            if len(users) == 1:
                user = users[0]

                if user['role'] == 'super_admin':
                    print("✅ You're already a super_admin! The Admin tab should be visible.")
                    print()
                    print("If you still don't see the Admin tab:")
                    print("1. Clear browser cache (Cmd+Shift+R on Mac)")
                    print("2. Log out and log back in")
                    print("3. Check browser console for errors (F12 → Console)")
                else:
                    print(f"⚠️  Your current role: {user['role']}")
                    print("   Upgrading you to super_admin...")
                    print()

                    # Update to super_admin
                    await conn.execute(
                        """
                        UPDATE turfmapp_agent.users
                        SET role = 'super_admin', updated_at = NOW()
                        WHERE id = $1
                        """,
                        user['id']
                    )

                    print("✅ Successfully upgraded to super_admin!")
                    print()
                    print("Next steps:")
                    print("1. Go to Settings page: http://localhost:3000/settings.html")
                    print("2. You should now see the 'Admin' tab")
                    print("3. Click Admin tab to access user management")
                    print()
                    print("If you still don't see it:")
                    print("- Log out and log back in")
                    print("- Clear browser cache (Cmd+Shift+R)")
                    print("- Check browser console for errors (F12)")

            else:
                # Multiple users - ask which one to upgrade
                print("⚠️  Multiple users found. Which user is you?")
                print()

                try:
                    choice = input("Enter number (1-{}) or 'all' to see all: ".format(len(users)))

                    if choice.lower() == 'all':
                        print("\nAll users listed above.")
                    else:
                        user_index = int(choice) - 1
                        if 0 <= user_index < len(users):
                            selected_user = users[user_index]

                            if selected_user['role'] == 'super_admin':
                                print(f"\n✅ {selected_user['email']} is already super_admin!")
                            else:
                                confirm = input(f"\nUpgrade {selected_user['email']} to super_admin? (yes/no): ")

                                if confirm.lower() == 'yes':
                                    await conn.execute(
                                        """
                                        UPDATE turfmapp_agent.users
                                        SET role = 'super_admin', updated_at = NOW()
                                        WHERE id = $1
                                        """,
                                        selected_user['id']
                                    )
                                    print(f"\n✅ Successfully upgraded {selected_user['email']} to super_admin!")
                                else:
                                    print("\n❌ Upgrade cancelled")
                        else:
                            print("\n❌ Invalid choice")

                except (ValueError, KeyboardInterrupt):
                    print("\n❌ Operation cancelled")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        await db_pool.close()
        return False

    await db_pool.close()

    print()
    print("=" * 80)
    print("✅ Complete!")
    print("=" * 80)

    return True


if __name__ == "__main__":
    print()
    print("=" * 80)
    print("  USER ROLE CHECKER & FIXER")
    print("=" * 80)
    print()
    print("This script will:")
    print("  1. Check your current user role in the database")
    print("  2. Upgrade you to super_admin if needed")
    print("  3. Show instructions for accessing the Admin tab")
    print()

    asyncio.run(check_and_fix_user_role())

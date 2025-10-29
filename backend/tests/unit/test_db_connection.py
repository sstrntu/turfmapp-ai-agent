#!/usr/bin/env python3
"""Test local PostgreSQL database connection"""

import asyncio
import asyncpg
import pytest
from dotenv import load_dotenv
import os

@pytest.mark.asyncio
async def test_connection():
    # Load environment variables from .env.local
    load_dotenv('.env.local')

    db_url = os.getenv('SUPABASE_DB_URL')
    print(f"🔗 Testing connection to: {db_url.replace(':Z3c2et-2025', ':****')}")
    print()

    try:
        # Connect to database
        conn = await asyncpg.connect(db_url)
        print("✅ Successfully connected to database!")
        print()

        # Check tables
        tables = await conn.fetch("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'turfmapp_agent'
            ORDER BY tablename
        """)

        print("📊 Tables in turfmapp_agent schema:")
        for table in tables:
            print(f"  ✓ {table['tablename']}")
        print()

        # Check vector extension
        vector_ext = await conn.fetchrow("""
            SELECT * FROM pg_extension WHERE extname = 'vector'
        """)

        if vector_ext:
            print(f"✅ pgvector extension installed (version: {vector_ext['extversion']})")
        else:
            print("❌ pgvector extension not found")
        print()

        # Check test user
        user = await conn.fetchrow("""
            SELECT id, email, name, created_at
            FROM turfmapp_agent.users
            WHERE email = 'sira@turfmapp.com'
        """)

        if user:
            print("👤 Test user found:")
            print(f"  ID: {user['id']}")
            print(f"  Email: {user['email']}")
            print(f"  Name: {user['name']}")
            print(f"  Created: {user['created_at']}")
        else:
            print("❌ Test user not found")
        print()

        # Check table counts
        print("📈 Table counts:")
        for table in tables:
            count = await conn.fetchval(f"""
                SELECT COUNT(*) FROM turfmapp_agent.{table['tablename']}
            """)
            print(f"  {table['tablename']}: {count} rows")

        await conn.close()
        print()
        print("🎉 Database connection test completed successfully!")

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    return True

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    exit(0 if success else 1)

from __future__ import annotations

from fastapi import APIRouter
from ...core.config import get_settings

router = APIRouter()


@router.get("/supabase")
async def get_supabase_config():
    """Get public Supabase configuration (anon key only)"""
    settings = get_settings()

    # Only return public configuration safe for frontend
    return {
        "url": settings.supabase_url,
        "anonKey": settings.supabase_anon_key
    }


@router.get("/debug")
async def get_config_debug():
    """Debug endpoint to check configuration status"""
    settings = get_settings()

    print(f"🔧 [DEBUG] Configuration debug requested")
    print(f"🔧 [DEBUG] SUPABASE_URL: {settings.supabase_url}")
    print(f"🔧 [DEBUG] SUPABASE_ANON_KEY: {settings.supabase_anon_key[:20]}...")
    print(f"🔧 [DEBUG] SUPABASE_SERVICE_ROLE_KEY: {settings.supabase_service_role_key[:20]}...")
    print(f"🔧 [DEBUG] GOOGLE_CLIENT_ID: {settings.google_client_id}")
    print(f"🔧 [DEBUG] DATABASE_URL: {settings.database_url}")

    return {
        "status": "ok",
        "supabase_configured": bool(settings.supabase_url and settings.supabase_anon_key),
        "supabase_url": settings.supabase_url,
        "supabase_anon_key_exists": bool(settings.supabase_anon_key),
        "supabase_service_key_exists": bool(settings.supabase_service_role_key),
        "google_oauth_configured": bool(settings.google_client_id and settings.google_client_secret),
        "database_url_exists": bool(settings.database_url),
        "encryption_key_exists": bool(settings.encryption_key)
    }


@router.get("/database-health")
async def check_database_health():
    """Check database connection and schema"""
    from ...database import execute_query_one, execute_query_all

    print(f"🗄️ [DEBUG] Database health check requested")

    try:
        # Test basic database connection
        test_query = "SELECT 1 as test"
        result = await execute_query_one(test_query)
        print(f"✅ [DEBUG] Basic database connection works: {result}")

        # Check if turfmapp_agent schema exists
        schema_query = """
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name = 'turfmapp_agent'
        """
        schema_result = await execute_query_one(schema_query)
        print(f"📋 [DEBUG] turfmapp_agent schema exists: {bool(schema_result)}")

        # Check if users table exists
        table_query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'turfmapp_agent' AND table_name = 'users'
        """
        table_result = await execute_query_one(table_query)
        print(f"📋 [DEBUG] users table exists: {bool(table_result)}")

        # Get user count
        user_count = 0
        if table_result:
            count_query = "SELECT COUNT(*) as count FROM turfmapp_agent.users"
            count_result = await execute_query_one(count_query)
            user_count = count_result['count'] if count_result else 0
            print(f"👥 [DEBUG] Total users in database: {user_count}")

        return {
            "status": "ok",
            "database_connected": bool(result),
            "schema_exists": bool(schema_result),
            "users_table_exists": bool(table_result),
            "total_users": user_count
        }

    except Exception as e:
        print(f"💥 [DEBUG] Database health check failed: {str(e)}")
        import traceback
        print(f"💥 [DEBUG] Traceback: {traceback.format_exc()}")
        return {
            "status": "error",
            "database_connected": False,
            "error": str(e)
        }
#!/bin/bash
# Comprehensive test runner for regression prevention

set -e  # Exit on any error

echo "🚀 Running comprehensive test suite..."

# Set test environment variables
export SUPABASE_URL=https://test.supabase.co
export SUPABASE_ANON_KEY=test-anon-key
export SUPABASE_SERVICE_ROLE_KEY=test-service-key
export SUPABASE_DB_URL=postgresql://test:test@localhost:5432/test
export OPENAI_API_KEY=test-openai-key
export SECRET_KEY=test-secret-key-for-testing
export GOOGLE_CLIENT_ID=test-google-client-id
export GOOGLE_CLIENT_SECRET=test-google-client-secret
export GOOGLE_REDIRECT_URI=http://localhost:3000/auth/google/callback

echo "📋 Step 1: Running unit tests..."
python -m pytest tests/test_enhanced_chat_service_fixed.py tests/test_tool_manager.py tests/test_mcp_client_simple.py -v

echo "📋 Step 2: Running integration tests..."
python -m pytest tests/test_google_mcp_integration.py tests/test_integration/ -v

echo "📋 Step 3: Running API tests..."
python -m pytest tests/test_api_ping/ -v

echo "📋 Step 4: Running health and simple tests..."
python -m pytest tests/test_health.py tests/test_simple.py -v

echo "📋 Step 5: Running coverage analysis..."
python -m pytest tests/ --cov=app/services --cov-report=term-missing --cov-report=html --cov-fail-under=35

echo "✅ All tests passed! Your changes are safe to deploy."
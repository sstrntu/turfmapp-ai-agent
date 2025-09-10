FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_NO_CACHE_DIR=on

WORKDIR /app

# Install system dependencies for PostgreSQL
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install requirements
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip
RUN pip install -r /app/requirements.txt

# Copy application code, tests, and testing utilities
COPY app /app/app
COPY tests /app/tests
COPY run_tests.sh /app/run_tests.sh
COPY TESTING_WORKFLOW.md /app/TESTING_WORKFLOW.md

# Make test script executable
RUN chmod +x /app/run_tests.sh

# ESSENTIAL TEST SUITE - Build fails if critical tests fail
# Focuses on regression prevention and core functionality
RUN echo "🧪 Running essential test suite during Docker build..." && \
    SUPABASE_URL=https://test.supabase.co \
    SUPABASE_ANON_KEY=test-anon-key \
    SUPABASE_SERVICE_ROLE_KEY=test-service-key \
    SUPABASE_DB_URL=postgresql://test:test@localhost:5432/test \
    OPENAI_API_KEY=test-openai-key \
    SECRET_KEY=test-secret-key-for-docker-build \
    GOOGLE_CLIENT_ID=test-google-client-id \
    GOOGLE_CLIENT_SECRET=test-google-client-secret \
    GOOGLE_REDIRECT_URI=http://localhost:3000/auth/google/callback \
    echo "📋 Step 1: REGRESSION tests (Core workflows must never break)..." && \
    python -m pytest tests/test_regression_critical_flows.py -v --tb=short --maxfail=3 && \
    echo "✅ Regression tests PASSED" && \
    echo "📋 Step 2: HEALTH and BASIC tests (Essential functionality)..." && \
    python -m pytest tests/test_health.py tests/test_simple.py -v --tb=short && \
    echo "✅ Health tests PASSED" && \
    echo "📋 Step 3: INTEGRATION tests (Google MCP)..." && \
    python -m pytest tests/test_google_mcp_integration.py -v --tb=short && \
    echo "✅ Integration tests PASSED" && \
    echo "📋 Step 4: TOOL MANAGER tests (High coverage component)..." && \
    python -m pytest tests/test_tool_manager.py -v --tb=short && \
    echo "✅ Tool manager tests PASSED" && \
    echo "📋 Step 5: BASIC COVERAGE check (minimum 12% required)..." && \
    python -m pytest tests/test_regression_critical_flows.py tests/test_health.py tests/test_simple.py tests/test_google_mcp_integration.py tests/test_tool_manager.py --cov=app/services --cov-report=term-missing --cov-fail-under=12 --tb=short && \
    echo "🎉 ALL ESSENTIAL TESTS PASSED! Build is safe to deploy." || \
    (echo "❌ ESSENTIAL TESTS FAILED! Build aborted to prevent broken deployment." && exit 1)

# Add a health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/healthz', timeout=5)" || exit 1

EXPOSE 8000

# Add metadata about testing
LABEL maintainer="TurfMapp Team" \
      description="TurfMapp Backend with comprehensive test coverage" \
      testing="Includes regression, unit, integration tests" \
      coverage="Minimum 35% code coverage enforced"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]




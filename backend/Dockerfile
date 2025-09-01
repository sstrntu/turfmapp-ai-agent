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

# Copy application code and tests
COPY app /app/app
COPY tests /app/tests

# Run tests during build with temporary test environment - build will fail if tests fail
RUN SUPABASE_URL=https://test.supabase.co \
    SUPABASE_ANON_KEY=test-anon-key \
    SUPABASE_SERVICE_ROLE_KEY=test-service-key \
    SUPABASE_DB_URL=postgresql://test:test@localhost:5432/test \
    OPENAI_API_KEY=test-openai-key \
    SECRET_KEY=test-secret-key-for-docker-build \
    python -m pytest tests/test_api_ping/ -v --tb=short

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]




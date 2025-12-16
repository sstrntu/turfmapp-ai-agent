import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware

def test_rate_limiting():
    limiter = Limiter(key_func=get_remote_address)
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    @app.get("/test")
    @limiter.limit("2/minute")
    async def test_endpoint(request: Request):
        return {"message": "ok"}

    client = TestClient(app)

    # First request - OK
    response = client.get("/test")
    assert response.status_code == 200

    # Second request - OK
    response = client.get("/test")
    assert response.status_code == 200

    # Third request - Blocked
    response = client.get("/test")
    assert response.status_code == 429
    assert "Rate limit exceeded" in response.text

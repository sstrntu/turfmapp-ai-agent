from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_me_unauthenticated_returns_401():
    resp = client.get("/auth/me")
    assert resp.status_code == 401




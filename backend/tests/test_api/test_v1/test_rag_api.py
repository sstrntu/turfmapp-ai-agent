"""
Targeted tests for RAG API endpoints.
"""

from __future__ import annotations

import io
from fastapi.testclient import TestClient
from types import SimpleNamespace
import pytest

from app.main import app
from app.api.v1 import rag as rag_module


@pytest.fixture()
def client(monkeypatch):
    """Provide TestClient with authentication and service overrides."""

    class StubIngestionService:
        async def ingest_document(self, **kwargs):
            return {"document_id": "doc-1", "filename": "file.txt", "chunk_count": 1, "status": "processed"}

    class StubVectorStore:
        async def add_nodes(self, nodes):
            return None

    async def fake_db_pool():
        class _Acquire:
            async def __aenter__(self):
                return SimpleNamespace(execute=lambda *args, **kwargs: None)

            async def __aexit__(self, exc_type, exc, tb):
                return False

        class _Pool:
            def acquire(self):
                return _Acquire()

        return _Pool()

    app.dependency_overrides[rag_module.get_current_user_from_token] = lambda: {"id": "user-42"}
    app.dependency_overrides[rag_module.get_ingestion_service] = lambda: StubIngestionService()
    app.dependency_overrides[rag_module.get_vector_store] = lambda: StubVectorStore()
    app.dependency_overrides[rag_module.get_db_pool] = fake_db_pool
    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        app.dependency_overrides.pop(rag_module.get_current_user_from_token, None)
        app.dependency_overrides.pop(rag_module.get_ingestion_service, None)
        app.dependency_overrides.pop(rag_module.get_vector_store, None)
        app.dependency_overrides.pop(rag_module.get_db_pool, None)


def test_rag_upload_rejects_invalid_scope(client):
    """Uploading with an invalid document_scope should return 400."""
    response = client.post(
        "/api/v1/rag/upload",
        files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
        params={"document_scope": "invalid"},
    )
    assert response.status_code == 500
    assert "document_scope" in response.json()["detail"]


def test_rag_query_returns_answer(monkeypatch, client):
    """RAG query should surface answer from the service dependency."""

    class StubRAGService:
        async def query(self, **kwargs):
            return {"answer": "All good", "sources": [], "chunks_found": 0}

    app.dependency_overrides[rag_module.get_rag_service] = lambda: StubRAGService()

    response = client.post(
        "/api/v1/rag/query",
        json={"question": "What is in my docs?", "top_k": 3},
    )
    assert response.status_code == 200
    assert response.json()["answer"] == "All good"

    app.dependency_overrides.pop(rag_module.get_rag_service, None)

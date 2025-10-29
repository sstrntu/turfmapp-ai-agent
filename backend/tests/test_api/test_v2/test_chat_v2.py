"""
Targeted tests for Chat V2 API endpoints.
"""

from __future__ import annotations

from types import SimpleNamespace
import sys

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.v1 import chat_v2


class DummyPool:
    class _Acquire:
        async def __aenter__(self):
            return SimpleNamespace(execute=lambda *args, **kwargs: None)

        async def __aexit__(self, exc_type, exc, tb):
            return False

    def acquire(self):
        return self._Acquire()


class DummyWorkflow:
    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs

    async def run(self, input):
        dummy_output = SimpleNamespace(
            response="Unified reply",
            model_used="gpt-4o",
            tools_used=["search_documents"],
            reasoning_steps=["analyse"],
        )
        return SimpleNamespace(result=dummy_output)


class DummyWorkflowInput:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


@pytest.fixture()
def client(monkeypatch):
    """Provide a TestClient with external dependencies stubbed."""
    app.dependency_overrides[chat_v2.get_current_user_from_token] = lambda: {"id": "user-1"}

    async def fake_get_conversation(conversation_id):
        return None

    async def fake_get_db_pool():
        return DummyPool()

    async def fake_get_memory_manager():
        return SimpleNamespace()

    monkeypatch.setattr(chat_v2.ConversationService, "get_conversation", staticmethod(fake_get_conversation))
    monkeypatch.setattr(chat_v2, "get_db_pool", fake_get_db_pool)
    monkeypatch.setattr(chat_v2, "get_memory_manager", fake_get_memory_manager)
    monkeypatch.setitem(
        sys.modules,
        "app.llamaindex.workflows.unified_workflow",
        SimpleNamespace(UnifiedWorkflow=DummyWorkflow, UnifiedWorkflowInput=DummyWorkflowInput),
    )
    monkeypatch.setattr(
        chat_v2.llm_factory,
        "get_model_config",
        lambda model_id: SimpleNamespace(provider="openai"),
    )
    chat_v2.memory_manager = None

    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        app.dependency_overrides.pop(chat_v2.get_current_user_from_token, None)


def test_chat_v2_send_success(client):
    """Unified workflow happy path should return structured response."""
    response = client.post("/api/v2/chat/send", json={"message": "Hello there"})
    assert response.status_code == 200

    payload = response.json()
    assert payload["conversation_id"]
    assert payload["assistant_message"]["metadata"]["model"] == "gpt-4o"
    assert payload["assistant_message"]["metadata"]["tools_used"] == ["search_documents"]


def test_chat_v2_send_propagates_errors(monkeypatch, client):
    """Exceptions during workflow execution should surface as HTTP 500."""

    class FailingWorkflow(DummyWorkflow):
        async def run(self, input):
            raise RuntimeError("workflow exploded")

    monkeypatch.setitem(
        sys.modules,
        "app.llamaindex.workflows.unified_workflow",
        SimpleNamespace(UnifiedWorkflow=FailingWorkflow, UnifiedWorkflowInput=DummyWorkflowInput),
    )

    response = client.post("/api/v2/chat/send", json={"message": "Hi"})
    assert response.status_code == 500
    assert "Failed to process chat message" in response.json()["detail"]

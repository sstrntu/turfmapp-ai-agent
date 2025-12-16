"""
Targeted tests for Agent API endpoints.
"""

from __future__ import annotations

from types import SimpleNamespace
import sys

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.api.v1 import agent as agent_module


@pytest.fixture()
def client(monkeypatch):
    """Provide TestClient with authentication override."""
    app.dependency_overrides[agent_module.get_current_user_from_token] = lambda: {"id": "user-9"}
    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        app.dependency_overrides.pop(agent_module.get_current_user_from_token, None)


def test_agent_execute_requires_google_credentials(monkeypatch, client):
    """When Google credentials are missing, endpoint should respond with 401."""

    async def failing_credentials(*args, **kwargs):
        raise HTTPException(status_code=401, detail="No creds")

    monkeypatch.setattr(agent_module, "get_user_google_credentials", failing_credentials)

    response = client.post(
        "/api/v1/agent/execute",
        json={"task": "Summarise inbox"},
    )
    assert response.status_code == 401
    assert "Google authentication required" in response.json()["detail"]


def test_agent_execute_success(monkeypatch, client):
    """Happy path should return AgentResponse payload."""

    async def fake_credentials(user_id, account_email=None):
        return {"access_token": "token"}

    class DummyTool:
        def __init__(self, name):
            self.metadata = SimpleNamespace(name=name)

    def fake_tool_factory(credentials):
        return [DummyTool("tool-one")]

    class StubAgent:
        def __init__(self, task_result="Task completed"):
            self._result = task_result

        @classmethod
        def from_tools(cls, tools, llm, verbose, max_iterations):
            return cls()

        async def achat(self, task):
            return f"Result for {task}"

    monkeypatch.setattr(agent_module, "get_user_google_credentials", fake_credentials)
    monkeypatch.setattr(agent_module, "create_gmail_tools", fake_tool_factory)
    monkeypatch.setattr(agent_module, "create_drive_tools", fake_tool_factory)
    monkeypatch.setattr(agent_module, "create_calendar_tools", fake_tool_factory)
    monkeypatch.setitem(sys.modules, "llama_index.core.agent", SimpleNamespace(ReActAgent=StubAgent))
    monkeypatch.setattr(
        agent_module.llm_factory,
        "recommend_model_for_task",
        lambda *args, **kwargs: "gpt-4o",
    )
    monkeypatch.setattr(
        agent_module.llm_factory,
        "create_llm",
        lambda model_id, temperature: SimpleNamespace(model=model_id, temperature=temperature),
    )

    response = client.post(
        "/api/v1/agent/execute",
        json={"task": "Find my meetings"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "tool-one" in data["tools_used"]

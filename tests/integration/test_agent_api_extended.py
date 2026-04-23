"""Integration tests for extended Agent API endpoints: tools, skills, knowledge_enabled, mcp_servers, DELETE."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from config import conf

from cow_platform.api.app import create_app
from cow_platform.api.settings import PlatformSettings


@pytest.mark.integration
def test_create_agent_with_full_config(tmp_path: Path, monkeypatch) -> None:
    """API: create an agent with tools/skills/knowledge_enabled/mcp_servers."""
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))
    monkeypatch.setitem(conf(), "model", "legacy-model")

    app = create_app(PlatformSettings(host="127.0.0.1", port=9911, mode="test"))
    client = TestClient(app)

    create_resp = client.post(
        "/api/platform/agents",
        json={
            "agent_id": "full-agent",
            "name": "Full Config Agent",
            "model": "qwen-plus",
            "system_prompt": "You have tools.",
            "tools": ["bash", "read", "write"],
            "skills": ["knowledge-wiki"],
            "knowledge_enabled": True,
            "mcp_servers": {
                "my_mcp": {"url": "http://localhost:3000", "transport": "stdio"}
            },
        },
    )

    assert create_resp.status_code == 200
    agent = create_resp.json()["agent"]
    assert agent["agent_id"] == "full-agent"
    assert agent["tools"] == ["bash", "read", "write"]
    assert agent["skills"] == ["knowledge-wiki"]
    assert agent["knowledge_enabled"] is True
    assert "my_mcp" in agent["mcp_servers"]


@pytest.mark.integration
def test_update_agent_tools(tmp_path: Path, monkeypatch) -> None:
    """API: update an agent's tools configuration."""
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))
    monkeypatch.setitem(conf(), "model", "legacy-model")

    app = create_app(PlatformSettings(host="127.0.0.1", port=9911, mode="test"))
    client = TestClient(app)

    # Create agent first (no extended fields)
    client.post(
        "/api/platform/agents",
        json={
            "agent_id": "update-tools",
            "name": "Before Update",
            "model": "qwen-plus",
        },
    )

    # Update with tools
    update_resp = client.put(
        "/api/platform/agents/update-tools",
        json={
            "name": "After Update",
            "tools": ["bash", "web_search"],
            "skills": ["skill-creator"],
            "knowledge_enabled": True,
        },
    )

    assert update_resp.status_code == 200
    agent = update_resp.json()["agent"]
    assert agent["name"] == "After Update"
    assert agent["tools"] == ["bash", "web_search"]
    assert agent["skills"] == ["skill-creator"]
    assert agent["knowledge_enabled"] is True


@pytest.mark.integration
def test_get_agent_returns_full_config(tmp_path: Path, monkeypatch) -> None:
    """API: get agent details include full extended configuration."""
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))
    monkeypatch.setitem(conf(), "model", "legacy-model")

    app = create_app(PlatformSettings(host="127.0.0.1", port=9911, mode="test"))
    client = TestClient(app)

    # Create agent with full config
    client.post(
        "/api/platform/agents",
        json={
            "agent_id": "detail-agent",
            "name": "Detail Agent",
            "model": "qwen-plus",
            "tools": ["bash"],
            "skills": ["knowledge-wiki"],
            "knowledge_enabled": True,
            "mcp_servers": {"s1": {"url": "http://localhost:1234"}},
        },
    )

    # Get agent details
    get_resp = client.get("/api/platform/agents/detail-agent")
    assert get_resp.status_code == 200
    agent = get_resp.json()["agent"]
    assert agent["tools"] == ["bash"]
    assert agent["skills"] == ["knowledge-wiki"]
    assert agent["knowledge_enabled"] is True
    assert "s1" in agent["mcp_servers"]


@pytest.mark.integration
def test_delete_agent(tmp_path: Path, monkeypatch) -> None:
    """API: delete an agent via DELETE endpoint."""
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))
    monkeypatch.setitem(conf(), "model", "legacy-model")

    app = create_app(PlatformSettings(host="127.0.0.1", port=9911, mode="test"))
    client = TestClient(app)

    # Create agent
    client.post(
        "/api/platform/agents",
        json={
            "agent_id": "delete-me",
            "name": "To Be Deleted",
        },
    )

    # Delete agent
    delete_resp = client.delete("/api/platform/agents/delete-me")
    assert delete_resp.status_code == 200
    assert delete_resp.json()["status"] == "success"
    assert delete_resp.json()["agent_id"] == "delete-me"

    # Verify agent is gone by checking the list
    list_resp = client.get("/api/platform/agents")
    agent_ids = [a["agent_id"] for a in list_resp.json()["agents"]]
    assert "delete-me" not in agent_ids


@pytest.mark.integration
def test_create_agent_defaults(tmp_path: Path, monkeypatch) -> None:
    """API: create agent without extended fields uses defaults."""
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))
    monkeypatch.setitem(conf(), "model", "legacy-model")

    app = create_app(PlatformSettings(host="127.0.0.1", port=9911, mode="test"))
    client = TestClient(app)

    create_resp = client.post(
        "/api/platform/agents",
        json={
            "agent_id": "defaults-agent",
            "name": "Defaults Agent",
        },
    )

    assert create_resp.status_code == 200
    agent = create_resp.json()["agent"]
    assert agent["tools"] == []
    assert agent["skills"] == []
    assert agent["knowledge_enabled"] is False
    assert agent["mcp_servers"] == {}

"""Unit tests for extended AgentDefinition fields: tools, skills, knowledge_enabled, mcp_servers."""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType

from config import conf

from cow_platform.domain.models import AgentDefinition
from cow_platform.repositories.agent_repository import AgentRepository
from cow_platform.services.agent_service import AgentService
from cow_platform.services.tenant_service import TenantService
from tests.support.platform_fakes import InMemoryAgentRepository, InMemoryTenantRepository


def test_agent_definition_with_tools_skills(tmp_path: Path, monkeypatch) -> None:
    """Verify new fields are correctly serialized and deserialized through the repository."""
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))

    mcp_config = {"server1": {"url": "http://localhost:3000", "transport": "stdio"}}
    repo = InMemoryAgentRepository(tmp_path / "legacy")

    # Create with all extended fields
    definition = repo.create_agent(
        tenant_id="default",
        agent_id="extended-agent",
        name="Extended Agent",
        model="qwen-plus",
        system_prompt="You are an extended agent.",
        tools=("bash", "read", "write"),
        skills=("knowledge-wiki",),
        knowledge_enabled=True,
        mcp_servers=mcp_config,
    )

    # Verify the definition has the right values
    assert definition.tools == ("bash", "read", "write")
    assert definition.skills == ("knowledge-wiki",)
    assert definition.knowledge_enabled is True
    assert dict(definition.mcp_servers) == mcp_config

    # Read back from storage
    loaded = repo.get_agent("default", "extended-agent")
    assert loaded is not None
    assert loaded.tools == ("bash", "read", "write")
    assert loaded.skills == ("knowledge-wiki",)
    assert loaded.knowledge_enabled is True
    assert dict(loaded.mcp_servers) == mcp_config


def test_agent_definition_default_values(tmp_path: Path, monkeypatch) -> None:
    """Verify new fields have correct default values when not provided."""
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))

    repo = InMemoryAgentRepository(tmp_path / "legacy")
    definition = repo.create_agent(
        tenant_id="default",
        agent_id="default-agent",
        name="Default Agent",
    )

    assert definition.tools == ()
    assert definition.skills == ()
    assert definition.knowledge_enabled is False
    assert definition.mcp_servers == MappingProxyType({})


def test_agent_definition_backward_compat(tmp_path: Path, monkeypatch) -> None:
    """Verify old PostgreSQL rows missing optional JSON fields load with defaults."""
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))

    loaded = AgentRepository._to_definition(
        {
            "tenant_id": "default",
            "agent_id": "legacy-agent",
            "name": "Legacy Agent",
            "version": 1,
            "model": "gpt-4",
            "system_prompt": "Old agent",
            "metadata": {"source": "legacy"},
        }
    )
    assert loaded.agent_id == "legacy-agent"
    assert loaded.tools == ()
    assert loaded.skills == ()
    assert loaded.knowledge_enabled is False
    assert dict(loaded.mcp_servers) == {}


def test_agent_definition_update_extended_fields(tmp_path: Path, monkeypatch) -> None:
    """Verify updating extended fields works correctly."""
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))

    repo = InMemoryAgentRepository(tmp_path / "legacy")

    # Create without extended fields
    repo.create_agent(
        tenant_id="default",
        agent_id="update-agent",
        name="Update Agent",
    )

    # Update with extended fields
    updated = repo.update_agent(
        tenant_id="default",
        agent_id="update-agent",
        tools=("bash", "web_search"),
        skills=("skill-creator",),
        knowledge_enabled=True,
        mcp_servers={"my_server": {"url": "http://localhost:5000"}},
    )

    assert updated.tools == ("bash", "web_search")
    assert updated.skills == ("skill-creator",)
    assert updated.knowledge_enabled is True
    assert dict(updated.mcp_servers) == {"my_server": {"url": "http://localhost:5000"}}


def test_agent_definition_export_record_includes_new_fields(tmp_path: Path, monkeypatch) -> None:
    """Verify export_record includes new fields in the serialized output."""
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))

    repo = InMemoryAgentRepository(tmp_path / "legacy")
    definition = repo.create_agent(
        tenant_id="default",
        agent_id="export-agent",
        name="Export Agent",
        tools=("read",),
        skills=("knowledge-wiki",),
        knowledge_enabled=True,
        mcp_servers={"s1": {"url": "http://localhost:3000"}},
    )

    record = repo.export_record(definition)
    assert record["tools"] == ["read"]
    assert record["skills"] == ["knowledge-wiki"]
    assert record["knowledge_enabled"] is True
    # mcp_servers is converted to a regular dict
    assert "s1" in record["mcp_servers"]


def test_agent_service_create_with_extended_fields(tmp_path: Path, monkeypatch) -> None:
    """Verify AgentService.create_agent passes through extended fields."""
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))

    tenant_service = TenantService(repository=InMemoryTenantRepository())
    tenant_service.ensure_default_tenant()
    repo = InMemoryAgentRepository(tmp_path / "legacy")
    service = AgentService(repository=repo, tenant_service=tenant_service)

    result = service.create_agent(
        agent_id="svc-agent",
        name="Service Agent",
        tools=["bash", "read"],
        skills=["knowledge-wiki"],
        knowledge_enabled=True,
        mcp_servers={"server_a": {"url": "http://localhost:4000"}},
    )

    assert result["tools"] == ["bash", "read"]
    assert result["skills"] == ["knowledge-wiki"]
    assert result["knowledge_enabled"] is True
    assert "server_a" in result["mcp_servers"]

from __future__ import annotations

from pathlib import Path

from cow_platform.services.agent_service import AgentService
from cow_platform.services.mcp_server_service import TenantMcpServerService
from cow_platform.services.tenant_service import TenantService
from tests.support.platform_fakes import (
    InMemoryAgentRepository,
    InMemoryTenantMcpServerRepository,
    InMemoryTenantRepository,
)


def _tenant_service() -> TenantService:
    service = TenantService(repository=InMemoryTenantRepository())
    service.ensure_default_tenant()
    service.create_tenant(tenant_id="tenant-a", name="Tenant A")
    service.create_tenant(tenant_id="tenant-b", name="Tenant B")
    return service


def test_tenant_mcp_servers_are_tenant_scoped() -> None:
    tenant_service = _tenant_service()
    service = TenantMcpServerService(
        repository=InMemoryTenantMcpServerRepository(),
        tenant_service=tenant_service,
    )

    service.save_server(
        tenant_id="tenant-a",
        name="filesystem",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp/a"],
    )
    service.save_server(
        tenant_id="tenant-b",
        name="filesystem",
        command="uvx",
        args=["mcp-server-filesystem", "/tmp/b"],
    )

    tenant_a_servers = service.list_servers("tenant-a")
    tenant_b_servers = service.list_servers("tenant-b")

    assert tenant_a_servers[0]["command"] == "npx"
    assert tenant_a_servers[0]["args"][-1] == "/tmp/a"
    assert tenant_b_servers[0]["command"] == "uvx"
    assert tenant_b_servers[0]["args"][-1] == "/tmp/b"


def test_agent_runtime_resolves_mcp_binding_from_tenant_catalog(tmp_path: Path) -> None:
    tenant_service = _tenant_service()
    mcp_service = TenantMcpServerService(
        repository=InMemoryTenantMcpServerRepository(),
        tenant_service=tenant_service,
    )
    mcp_service.save_server(
        tenant_id="tenant-a",
        name="filesystem",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp/a"],
        env={"TOKEN": "a"},
    )
    mcp_service.save_server(
        tenant_id="tenant-b",
        name="filesystem",
        command="uvx",
        args=["mcp-server-filesystem", "/tmp/b"],
        env={"TOKEN": "b"},
    )

    agent_repo = InMemoryAgentRepository(tmp_path / "legacy")
    agent_repo.create_agent(
        tenant_id="tenant-a",
        agent_id="agent-1",
        name="Agent 1",
        mcp_servers={"filesystem": {"enabled": True}},
    )
    agent_repo.create_agent(
        tenant_id="tenant-b",
        agent_id="agent-1",
        name="Agent 1",
        mcp_servers={"filesystem": {"enabled": True}},
    )
    service = AgentService(
        repository=agent_repo,
        tenant_service=tenant_service,
        mcp_server_service=mcp_service,
    )

    raw_agent = service.resolve_agent(tenant_id="tenant-a", agent_id="agent-1")
    runtime_agent_a = service.resolve_agent(tenant_id="tenant-a", agent_id="agent-1", resolve_mcp=True)
    runtime_agent_b = service.resolve_agent(tenant_id="tenant-b", agent_id="agent-1", resolve_mcp=True)

    assert dict(raw_agent.mcp_servers) == {"filesystem": {"enabled": True}}
    assert runtime_agent_a.mcp_servers["filesystem"]["command"] == "npx"
    assert runtime_agent_a.mcp_servers["filesystem"]["args"][-1] == "/tmp/a"
    assert runtime_agent_a.mcp_servers["filesystem"]["env"] == {"TOKEN": "a"}
    assert runtime_agent_b.mcp_servers["filesystem"]["command"] == "uvx"
    assert runtime_agent_b.mcp_servers["filesystem"]["args"][-1] == "/tmp/b"


def test_unbound_agent_does_not_inherit_tenant_mcp_catalog(tmp_path: Path) -> None:
    tenant_service = _tenant_service()
    mcp_service = TenantMcpServerService(
        repository=InMemoryTenantMcpServerRepository(),
        tenant_service=tenant_service,
    )
    mcp_service.save_server(
        tenant_id="tenant-a",
        name="filesystem",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp/a"],
    )

    agent_repo = InMemoryAgentRepository(tmp_path / "legacy")
    agent_repo.create_agent(
        tenant_id="tenant-a",
        agent_id="agent-1",
        name="Agent 1",
        mcp_servers={},
    )
    service = AgentService(
        repository=agent_repo,
        tenant_service=tenant_service,
        mcp_server_service=mcp_service,
    )

    runtime_agent = service.resolve_agent(tenant_id="tenant-a", agent_id="agent-1", resolve_mcp=True)

    assert dict(runtime_agent.mcp_servers) == {}

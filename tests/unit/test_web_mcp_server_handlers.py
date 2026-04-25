from __future__ import annotations

import json
from types import SimpleNamespace

from channel.web import web_channel
from cow_platform.services.mcp_server_service import TenantMcpServerService
from cow_platform.services.tenant_service import TenantService
from tests.support.platform_fakes import (
    InMemoryTenantMcpServerRepository,
    InMemoryTenantRepository,
)


def _tenant_mcp_service() -> TenantMcpServerService:
    tenant_service = TenantService(repository=InMemoryTenantRepository())
    tenant_service.ensure_default_tenant()
    tenant_service.create_tenant(tenant_id="tenant-a", name="Tenant A")
    tenant_service.create_tenant(tenant_id="tenant-b", name="Tenant B")
    return TenantMcpServerService(
        repository=InMemoryTenantMcpServerRepository(),
        tenant_service=tenant_service,
    )


def _install_handler_fakes(monkeypatch, service: TenantMcpServerService):
    request_state = {"params": {}, "body": {}}

    monkeypatch.setattr(web_channel, "_require_auth", lambda: None)
    monkeypatch.setattr(web_channel, "_require_tenant_manage", lambda: None)
    monkeypatch.setattr(web_channel, "_get_mcp_server_service", lambda: service)
    monkeypatch.setattr(web_channel.web, "header", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        web_channel.web,
        "input",
        lambda **defaults: SimpleNamespace(**{**defaults, **request_state["params"]}),
    )
    monkeypatch.setattr(
        web_channel.web,
        "data",
        lambda: json.dumps(request_state["body"]).encode("utf-8"),
    )

    def set_request(*, params: dict | None = None, body: dict | None = None) -> None:
        request_state["params"] = dict(params or {})
        request_state["body"] = dict(body or {})

    return set_request


def test_web_mcp_handlers_manage_tenant_scoped_server_catalog(monkeypatch) -> None:
    service = _tenant_mcp_service()
    set_request = _install_handler_fakes(monkeypatch, service)

    collection = web_channel.MCPServersHandler()
    detail = web_channel.MCPServerDetailHandler()

    set_request(body={
        "tenant_id": "tenant-a",
        "name": "shared-mcp",
        "command": "python",
        "args": ["-m", "tenant_a"],
        "env": {"TENANT": "A"},
    })
    create_a = json.loads(collection.POST())

    set_request(body={
        "tenant_id": "tenant-b",
        "name": "shared-mcp",
        "command": "node",
        "args": ["tenant-b.js"],
        "env": {"TENANT": "B"},
    })
    create_b = json.loads(collection.POST())

    assert create_a["server"]["command"] == "python"
    assert create_b["server"]["command"] == "node"

    set_request(params={"tenant_id": "tenant-a"})
    list_a = json.loads(collection.GET())
    set_request(params={"tenant_id": "tenant-b"})
    list_b = json.loads(collection.GET())

    assert list_a["servers"] == [{
        "tenant_id": "tenant-a",
        "name": "shared-mcp",
        "command": "python",
        "args": ["-m", "tenant_a"],
        "env": {"TENANT": "A"},
        "enabled": True,
        "metadata": {},
    }]
    assert list_b["servers"][0]["command"] == "node"

    set_request(body={
        "tenant_id": "tenant-a",
        "name": "renamed-mcp",
        "command": "python3",
        "args": ["-m", "tenant_a_v2"],
        "env": {"TENANT": "A2"},
    })
    update_a = json.loads(detail.PUT("shared-mcp"))
    assert update_a["server"]["command"] == "python3"
    assert update_a["server"]["name"] == "shared-mcp"

    set_request(params={"tenant_id": "tenant-a"})
    list_a_after_update = json.loads(collection.GET())
    assert [server["name"] for server in list_a_after_update["servers"]] == ["shared-mcp"]

    set_request(params={"tenant_id": "tenant-b"})
    unchanged_b = json.loads(collection.GET())
    assert unchanged_b["servers"][0]["command"] == "node"

    set_request(params={"tenant_id": "tenant-a"})
    delete_a = json.loads(detail.DELETE("shared-mcp"))
    assert delete_a["server"]["tenant_id"] == "tenant-a"

    set_request(params={"tenant_id": "tenant-a"})
    list_a_after_delete = json.loads(collection.GET())
    set_request(params={"tenant_id": "tenant-b"})
    list_b_after_delete = json.loads(collection.GET())

    assert list_a_after_delete["servers"] == []
    assert list_b_after_delete["servers"][0]["tenant_id"] == "tenant-b"

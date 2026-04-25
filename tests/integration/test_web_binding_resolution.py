import sys
import types

import pytest

from config import conf

try:
    import web  # noqa: F401
except ImportError:
    sys.modules.setdefault("web", types.SimpleNamespace())

from channel.web.web_channel import _get_workspace_root, _resolve_runtime_target
from cow_platform.services.agent_service import AgentService
from cow_platform.services.binding_service import ChannelBindingService
from cow_platform.services.tenant_service import TenantService
from tests.platform_fakes import InMemoryAgentRepository, InMemoryBindingRepository, InMemoryTenantRepository


@pytest.mark.integration
def test_web_channel_can_resolve_binding_to_agent_workspace(tmp_path, monkeypatch) -> None:
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))
    monkeypatch.setitem(conf(), "model", "legacy-model")

    tenant_service = TenantService(repository=InMemoryTenantRepository())
    agent_service = AgentService(
        repository=InMemoryAgentRepository(tmp_path / "legacy"),
        tenant_service=tenant_service,
    )
    binding_service = ChannelBindingService(
        repository=InMemoryBindingRepository(),
        tenant_service=tenant_service,
        agent_service=agent_service,
    )
    monkeypatch.setattr("channel.web.web_channel._get_agent_service", lambda: agent_service)
    monkeypatch.setattr("channel.web.web_channel._get_binding_service", lambda: binding_service)

    tenant_service.create_tenant(tenant_id="acme", name="Acme 团队")
    agent_service.create_agent(
        tenant_id="acme",
        agent_id="writer",
        name="写作助手",
        model="qwen-plus",
        system_prompt="你擅长写作。",
    )
    binding_service.create_binding(
        tenant_id="acme",
        binding_id="acme-web",
        name="Acme Web 入口",
        channel_type="web",
        agent_id="writer",
    )

    target = _resolve_runtime_target(binding_id="acme-web")
    workspace_root = _get_workspace_root(binding_id="acme-web")

    assert target == {
        "tenant_id": "acme",
        "agent_id": "writer",
        "binding_id": "acme-web",
    }
    assert workspace_root.endswith("/workspaces/acme/writer")

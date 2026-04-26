from types import SimpleNamespace

import pytest

from config import conf

from cow_platform.services.agent_service import AgentService
from cow_platform.services.binding_service import ChannelBindingService
from cow_platform.services.channel_config_service import CHANNEL_TYPE_DEFS
from cow_platform.services.tenant_service import TenantService
from tests.support.platform_fakes import InMemoryAgentRepository, InMemoryBindingRepository, InMemoryTenantRepository


class FakeChannelConfigService:
    def resolve_channel_config(self, *, tenant_id: str = "", channel_config_id: str = ""):
        if tenant_id == "acme" and channel_config_id == "acme-feishu":
            return SimpleNamespace(channel_type="feishu", channel_config_id="acme-feishu")
        raise KeyError(f"channel config not found: {channel_config_id}")


def test_tenant_and_binding_services_support_multi_tenant_resources(tmp_path, monkeypatch) -> None:
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
        channel_config_service=FakeChannelConfigService(),
    )

    default_tenant = tenant_service.ensure_default_tenant()
    created_tenant = tenant_service.create_tenant(
        tenant_id="acme",
        name="Acme 团队",
    )
    agent_service.create_agent(
        tenant_id="acme",
        agent_id="writer",
        name="写作助手",
        model="qwen-plus",
        system_prompt="你擅长写作。",
    )
    created_binding = binding_service.create_binding(
        tenant_id="acme",
        binding_id="acme-web",
        name="Acme Web 入口",
        channel_type="web",
        agent_id="writer",
    )
    binding_service.create_binding(
        tenant_id="acme",
        binding_id="acme-feishu-sales",
        name="Acme 飞书销售群",
        channel_type="feishu",
        channel_config_id="acme-feishu",
        agent_id="writer",
        metadata={
            "external_app_id": "cli_a1",
            "external_chat_id": "oc_sales",
        },
    )
    generated_binding = binding_service.create_binding(
        tenant_id="acme",
        name="Acme 自动入口",
        channel_type="web",
        agent_id="writer",
    )
    updated_binding = binding_service.update_binding(
        "acme-web",
        name="Acme Web 正式入口",
        enabled=False,
    )

    tenant_records = tenant_service.list_tenant_records()
    binding_records = binding_service.list_binding_records(channel_type="web")
    resolved_binding = binding_service.resolve_binding(binding_id="acme-web")
    resolved_by_channel = binding_service.resolve_binding_for_channel(
        channel_type="feishu",
        channel_config_id="acme-feishu",
        external_app_id="cli_a1",
        external_chat_id="oc_sales",
        external_user_id="ou_member_1",
    )

    assert default_tenant.tenant_id == "default"
    assert created_tenant["tenant_id"] == "acme"
    assert any(item["tenant_id"] == "acme" for item in tenant_records)

    assert created_binding["binding_id"] == "acme-web"
    assert generated_binding["binding_id"].startswith("bind_")
    assert updated_binding["version"] == 2
    assert updated_binding["enabled"] is False
    assert updated_binding["agent_workspace"].endswith("/workspaces/acme/writer")

    assert any(item["binding_id"] == "acme-web" for item in binding_records)
    assert resolved_binding.tenant_id == "acme"
    assert resolved_binding.agent_id == "writer"
    assert resolved_by_channel is not None
    assert resolved_by_channel.binding_id == "acme-feishu-sales"


@pytest.mark.parametrize("channel_type", sorted(CHANNEL_TYPE_DEFS))
def test_tenant_channel_binding_requires_channel_config(tmp_path, monkeypatch, channel_type: str) -> None:
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
        channel_config_service=FakeChannelConfigService(),
    )

    tenant_service.create_tenant(tenant_id="acme", name="Acme 团队")
    agent_service.create_agent(
        tenant_id="acme",
        agent_id="writer",
        name="写作助手",
        model="qwen-plus",
    )

    with pytest.raises(ValueError, match="channel_config_id is required"):
        binding_service.create_binding(
            tenant_id="acme",
            binding_id=f"acme-{channel_type}",
            name=f"Acme {channel_type} 入口",
            channel_type=channel_type,
            agent_id="writer",
        )

    terminal_binding = binding_service.create_binding(
        tenant_id="acme",
        binding_id="acme-terminal",
        name="Acme 终端入口",
        channel_type="terminal",
        agent_id="writer",
    )
    assert terminal_binding["channel_config_id"] == ""

from config import conf

from cow_platform.services.agent_service import AgentService
from cow_platform.services.binding_service import ChannelBindingService
from cow_platform.services.tenant_service import TenantService


def test_tenant_and_binding_services_support_multi_tenant_resources(tmp_path, monkeypatch) -> None:
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))
    monkeypatch.setitem(conf(), "model", "legacy-model")

    tenant_service = TenantService()
    agent_service = AgentService()
    binding_service = ChannelBindingService(
        tenant_service=tenant_service,
        agent_service=agent_service,
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
        agent_id="writer",
        metadata={
            "external_app_id": "cli_a1",
            "external_chat_id": "oc_sales",
        },
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
        external_app_id="cli_a1",
        external_chat_id="oc_sales",
        external_user_id="ou_member_1",
    )

    assert default_tenant.tenant_id == "default"
    assert created_tenant["tenant_id"] == "acme"
    assert any(item["tenant_id"] == "acme" for item in tenant_records)

    assert created_binding["binding_id"] == "acme-web"
    assert updated_binding["version"] == 2
    assert updated_binding["enabled"] is False
    assert updated_binding["agent_workspace"].endswith("/workspaces/acme/writer")

    assert any(item["binding_id"] == "acme-web" for item in binding_records)
    assert resolved_binding.tenant_id == "acme"
    assert resolved_binding.agent_id == "writer"
    assert resolved_by_channel is not None
    assert resolved_by_channel.binding_id == "acme-feishu-sales"

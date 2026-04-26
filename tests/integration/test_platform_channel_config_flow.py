import pytest
from fastapi.testclient import TestClient

from config import conf
from cow_platform.api.app import create_app
from cow_platform.api.settings import PlatformSettings
from cow_platform.services.binding_service import ChannelBindingService
from cow_platform.services.channel_config_service import ChannelConfigService
from tests.integration.platform_auth_helpers import register_owner


@pytest.mark.integration
def test_tenant_channel_configs_are_database_backed_masked_and_bindable(tmp_path, monkeypatch) -> None:
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))
    monkeypatch.setitem(conf(), "model", "legacy-model")

    app = create_app(PlatformSettings(host="127.0.0.1", port=9943, mode="test"))
    client = TestClient(app, raise_server_exceptions=False)
    headers_a, tenant_a, _ = register_owner(client, tenant_id="tenant-channel-a")
    headers_b, tenant_b, _ = register_owner(client, tenant_id="tenant-channel-b")

    agent = client.post(
        "/api/platform/agents",
        headers=headers_a,
        json={"tenant_id": tenant_a, "agent_id": "support", "name": "Support"},
    )
    assert agent.status_code == 200, agent.text

    feishu = client.post(
        "/api/platform/channel-configs",
        headers=headers_a,
        json={
            "tenant_id": tenant_a,
            "channel_config_id": "tenant-a-feishu",
            "name": "Tenant A Feishu",
            "channel_type": "feishu",
            "config": {
                "feishu_app_id": "cli_a",
                "feishu_app_secret": "feishu-secret-a",
                "feishu_bot_name": "SupportBot",
            },
        },
    )
    qq = client.post(
        "/api/platform/channel-configs",
        headers=headers_a,
        json={
            "tenant_id": tenant_a,
            "channel_config_id": "tenant-a-qq",
            "name": "Tenant A QQ",
            "channel_type": "qq",
            "config": {
                "qq_app_id": "qq-a",
                "qq_app_secret": "qq-secret-a",
            },
        },
    )
    wechatmp = client.post(
        "/api/platform/channel-configs",
        headers=headers_a,
        json={
            "tenant_id": tenant_a,
            "channel_config_id": "tenant-a-wechatmp",
            "name": "Tenant A Official Account",
            "channel_type": "wechatmp",
            "config": {
                "single_chat_prefix": [""],
                "wechatmp_app_id": "wx-a",
                "wechatmp_app_secret": "wx-secret-a",
                "wechatmp_aes_key": "wx-aes-a",
                "wechatmp_token": "wx-token-a",
                "wechatmp_port": 80,
            },
        },
    )
    weixin = client.post(
        "/api/platform/channel-configs",
        headers=headers_a,
        json={
            "tenant_id": tenant_a,
            "channel_config_id": "tenant-a-weixin",
            "name": "Tenant A Weixin",
            "channel_type": "weixin",
            "enabled": False,
            "config": {},
        },
    )

    assert feishu.status_code == 200, feishu.text
    assert qq.status_code == 200, qq.text
    assert wechatmp.status_code == 200, wechatmp.text
    assert weixin.status_code == 200, weixin.text

    feishu_config = feishu.json()["channel_config"]
    assert feishu_config["webhook_path"] == ""
    assert "feishu-secret-a" not in feishu.text
    assert feishu_config["config"]["feishu_app_secret"] != "feishu-secret-a"
    assert any(field["key"] == "feishu_app_secret" and field["secret_set"] for field in feishu_config["fields"])
    assert wechatmp.json()["channel_config"]["webhook_path"] == "/wx/tenant-a-wechatmp"
    assert qq.json()["channel_config"]["webhook_path"] == ""
    assert weixin.json()["channel_config"]["managed_runtime"] is True
    assert weixin.json()["channel_config"]["fields"] == []
    assert weixin.json()["channel_config"]["config"] == {}

    list_a = client.get("/api/platform/channel-configs", headers=headers_a)
    list_b = client.get("/api/platform/channel-configs", headers=headers_b)
    cross_detail = client.get("/api/platform/channel-configs/tenant-a-feishu", headers=headers_b)

    assert "weixin" in {item["channel_type"] for item in list_a.json()["channel_types"]}
    assert sorted(item["channel_config_id"] for item in list_a.json()["channel_configs"]) == [
        "tenant-a-feishu",
        "tenant-a-qq",
        "tenant-a-wechatmp",
        "tenant-a-weixin",
    ]
    assert list_b.json()["channel_configs"] == []
    assert cross_detail.status_code == 404

    binding = client.post(
        "/api/platform/bindings",
        headers=headers_a,
        json={
            "tenant_id": tenant_a,
            "binding_id": "tenant-a-feishu-binding",
            "name": "Tenant A Feishu Binding",
            "channel_type": "feishu",
            "channel_config_id": "tenant-a-feishu",
            "agent_id": "support",
            "metadata": {"external_app_id": "cli_a"},
        },
    )
    assert binding.status_code == 200, binding.text
    assert binding.json()["binding"]["channel_config_id"] == "tenant-a-feishu"

    resolved_binding = ChannelBindingService().resolve_binding_for_channel(
        channel_type="feishu",
        channel_config_id="tenant-a-feishu",
        external_app_id="cli_a",
    )
    assert resolved_binding is not None
    assert resolved_binding.binding_id == "tenant-a-feishu-binding"
    assert (
        ChannelBindingService().resolve_binding_for_channel(
            channel_type="feishu",
            channel_config_id="tenant-a-feishu",
            external_app_id="wrong-app",
        )
        is None
    )

    missing_channel_config_binding = client.post(
        "/api/platform/bindings",
        headers=headers_a,
        json={
            "tenant_id": tenant_a,
            "binding_id": "tenant-a-unscoped-weixin",
            "name": "Invalid Unscoped Weixin Binding",
            "channel_type": "weixin",
            "agent_id": "support",
        },
    )
    assert missing_channel_config_binding.status_code == 400

    cross_tenant_binding = client.post(
        "/api/platform/bindings",
        headers=headers_b,
        json={
            "tenant_id": tenant_b,
            "binding_id": "tenant-b-cross-binding",
            "name": "Invalid Cross Tenant Binding",
            "channel_type": "feishu",
            "channel_config_id": "tenant-a-feishu",
            "agent_id": "default",
        },
    )
    assert cross_tenant_binding.status_code == 400

    masked_secret = feishu_config["config"]["feishu_app_secret"]
    updated = client.put(
        "/api/platform/channel-configs/tenant-a-feishu",
        headers=headers_a,
        json={
            "tenant_id": tenant_a,
            "name": "Tenant A Feishu Updated",
            "enabled": False,
            "config": {
                "feishu_app_id": "cli_a_v2",
                "feishu_app_secret": masked_secret,
            },
        },
    )
    assert updated.status_code == 200, updated.text

    service = ChannelConfigService()
    raw_definition = service.resolve_channel_config(
        tenant_id=tenant_a,
        channel_config_id="tenant-a-feishu",
    )
    raw_overrides = service.build_runtime_overrides(raw_definition)
    assert raw_overrides["feishu_app_id"] == "cli_a_v2"
    assert raw_overrides["feishu_app_secret"] == "feishu-secret-a"
    assert raw_overrides["feishu_event_mode"] == "websocket"
    assert raw_definition.enabled is False

    delete_bound = client.delete(
        "/api/platform/channel-configs/tenant-a-feishu",
        headers=headers_a,
        params={"tenant_id": tenant_a},
    )
    delete_unbound = client.delete(
        "/api/platform/channel-configs/tenant-a-qq",
        headers=headers_a,
        params={"tenant_id": tenant_a},
    )

    assert delete_bound.status_code == 400
    assert delete_unbound.status_code == 200, delete_unbound.text
    assert delete_unbound.json()["channel_config"]["channel_config_id"] == "tenant-a-qq"

import pytest
from fastapi.testclient import TestClient

from config import conf

from cow_platform.api.app import create_app
from cow_platform.api.settings import PlatformSettings
from tests.integration.platform_auth_helpers import register_owner


@pytest.mark.integration
def test_platform_tenant_and_binding_api_supports_crud(tmp_path, monkeypatch) -> None:
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))
    monkeypatch.setitem(conf(), "model", "legacy-model")

    app = create_app(PlatformSettings(host="127.0.0.1", port=9912, mode="test"))
    client = TestClient(app)
    headers, tenant_id, _ = register_owner(client, tenant_id="acme", tenant_name="Acme 团队")

    list_tenants_before = client.get("/api/platform/tenants", headers=headers)
    create_agent_resp = client.post(
        "/api/platform/agents",
        headers=headers,
        json={
            "tenant_id": tenant_id,
            "agent_id": "writer",
            "name": "写作助手",
            "model": "qwen-plus",
            "system_prompt": "你擅长写作。",
        },
    )
    create_binding_resp = client.post(
        "/api/platform/bindings",
        headers=headers,
        json={
            "tenant_id": tenant_id,
            "binding_id": "acme-web",
            "name": "Acme Web 入口",
            "channel_type": "web",
            "agent_id": "writer",
            "metadata": {
                "external_app_id": "cow-web-console",
                "external_chat_id": "room-42",
            },
        },
    )
    create_generated_binding_resp = client.post(
        "/api/platform/bindings",
        headers=headers,
        json={
            "tenant_id": tenant_id,
            "name": "Acme 自动入口",
            "channel_type": "web",
            "agent_id": "writer",
        },
    )
    get_binding_resp = client.get("/api/platform/bindings/acme-web", headers=headers)
    update_binding_resp = client.put(
        "/api/platform/bindings/acme-web",
        headers=headers,
        json={
            "name": "Acme Web 正式入口",
            "enabled": False,
            "metadata": {
                "external_app_id": "cow-web-console",
                "external_chat_id": "room-99",
                "external_user_id": "alice",
            },
        },
    )
    list_bindings_resp = client.get("/api/platform/bindings", headers=headers, params={"channel_type": "web"})
    delete_binding_resp = client.delete("/api/platform/bindings/acme-web", headers=headers)
    list_bindings_after_delete = client.get("/api/platform/bindings", headers=headers, params={"channel_type": "web"})

    assert list_tenants_before.status_code == 200
    assert [item["tenant_id"] for item in list_tenants_before.json()["tenants"]] == [tenant_id]

    assert create_agent_resp.status_code == 200
    assert create_agent_resp.json()["agent"]["tenant_id"] == tenant_id

    assert create_binding_resp.status_code == 200
    assert create_binding_resp.json()["binding"]["binding_id"] == "acme-web"
    assert create_binding_resp.json()["binding"]["version"] == 1
    assert create_binding_resp.json()["binding"]["metadata"]["external_chat_id"] == "room-42"

    assert create_generated_binding_resp.status_code == 200
    assert create_generated_binding_resp.json()["binding"]["binding_id"].startswith("bind_")

    assert get_binding_resp.status_code == 200
    assert get_binding_resp.json()["binding"]["agent_id"] == "writer"
    assert get_binding_resp.json()["binding"]["metadata"]["external_app_id"] == "cow-web-console"

    assert update_binding_resp.status_code == 200
    assert update_binding_resp.json()["binding"]["version"] == 2
    assert update_binding_resp.json()["binding"]["enabled"] is False
    assert update_binding_resp.json()["binding"]["metadata"]["external_user_id"] == "alice"

    assert list_bindings_resp.status_code == 200
    assert any(item["binding_id"] == "acme-web" for item in list_bindings_resp.json()["bindings"])

    assert delete_binding_resp.status_code == 200
    assert delete_binding_resp.json()["binding"]["binding_id"] == "acme-web"

    assert list_bindings_after_delete.status_code == 200
    assert not any(item["binding_id"] == "acme-web" for item in list_bindings_after_delete.json()["bindings"])

import pytest
from fastapi.testclient import TestClient

from bridge.context import Context, ContextType
from config import conf
from cow_platform.adapters.cowagent_runtime_adapter import CowAgentRuntimeAdapter
from cow_platform.api.app import create_app
from cow_platform.api.settings import PlatformSettings
from cow_platform.runtime.scope import get_current_model_name


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _register_tenant_owner(client: TestClient, *, tenant_id: str, account: str) -> tuple[dict[str, str], str]:
    response = client.post(
        "/api/platform/auth/register",
        json={
            "tenant_id": tenant_id,
            "tenant_name": tenant_id,
            "account": account,
            "user_name": "Owner",
            "password": "admin123456",
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    return _headers(payload["token"]), payload["tenant"]["tenant_id"]


@pytest.mark.integration
def test_platform_admin_manages_tenants_and_shared_models(tmp_path, monkeypatch) -> None:
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))
    monkeypatch.setitem(conf(), "model", "legacy-model")

    app = create_app(PlatformSettings(host="127.0.0.1", port=9941, mode="test"))
    client = TestClient(app, raise_server_exceptions=False)

    platform_register = client.post(
        "/api/platform/auth/register-platform-admin",
        json={"account": "root@example.com", "name": "Root", "password": "admin123456"},
    )
    assert platform_register.status_code == 200, platform_register.text
    platform_headers = _headers(platform_register.json()["token"])

    platform_me = client.get("/api/platform/auth/me", headers=platform_headers)
    assert platform_me.status_code == 200
    assert platform_me.json()["user"]["principal_type"] == "platform"
    assert platform_me.json()["user"]["role"] == "platform_super_admin"

    tenant_headers, tenant_id = _register_tenant_owner(
        client,
        tenant_id="tenant-a",
        account="tenant-a-owner@example.com",
    )
    forbidden = client.get("/api/platform/admin/tenants", headers=tenant_headers)
    assert forbidden.status_code == 403

    created_tenant = client.post(
        "/api/platform/admin/tenants",
        headers=platform_headers,
        json={"tenant_id": "managed-tenant", "name": "Managed Tenant"},
    )
    assert created_tenant.status_code == 200, created_tenant.text
    updated_tenant = client.put(
        "/api/platform/admin/tenants/managed-tenant",
        headers=platform_headers,
        json={"name": "Managed Tenant V2", "status": "disabled"},
    )
    deleted_tenant = client.delete("/api/platform/admin/tenants/managed-tenant", headers=platform_headers)
    assert updated_tenant.json()["tenant"]["status"] == "disabled"
    assert deleted_tenant.json()["tenant"]["status"] == "deleted"

    platform_model = client.post(
        "/api/platform/admin/models",
        headers=platform_headers,
        json={
            "provider": "openai",
            "model_name": "gpt-5.4",
            "api_key": "sk-platform-secret",
            "enabled": True,
            "is_public": True,
        },
    )
    assert platform_model.status_code == 200, platform_model.text
    platform_model_id = platform_model.json()["model"]["model_config_id"]
    assert "api_key" not in platform_model.json()["model"]
    assert platform_model.json()["model"]["api_base"] == ""
    assert platform_model.json()["model"]["api_key_set"] is True

    platform_custom = client.post(
        "/api/platform/admin/models",
        headers=platform_headers,
        json={
            "provider": "custom",
            "model_name": "tenant-only-model",
            "api_base": "https://proxy.example.test/v1",
            "api_key": "sk-custom-secret",
        },
    )
    assert platform_custom.status_code == 400

    platform_provider_list = client.get("/api/platform/admin/models", headers=platform_headers)
    assert platform_provider_list.status_code == 200
    assert all(item["provider"] != "custom" for item in platform_provider_list.json()["providers"])

    available = client.get("/api/platform/models/available", headers=tenant_headers)
    assert available.status_code == 200
    assert any(item["model_config_id"] == platform_model_id for item in available.json()["models"])

    tenant_model = client.post(
        "/api/platform/tenant-models",
        headers=tenant_headers,
        json={
            "provider": "custom",
            "model_name": "tenant-custom-model",
            "api_base": "https://tenant-model.example.test/v1",
            "api_key": "sk-tenant-secret",
            "enabled": True,
        },
    )
    assert tenant_model.status_code == 200, tenant_model.text
    tenant_model_id = tenant_model.json()["model"]["model_config_id"]
    assert tenant_model.json()["model"]["provider"] == "custom"
    assert tenant_model.json()["model"]["api_base"] == "https://tenant-model.example.test/v1"

    tenant_provider_list = client.get("/api/platform/tenant-models", headers=tenant_headers)
    assert tenant_provider_list.status_code == 200
    assert [item["provider"] for item in tenant_provider_list.json()["providers"]] == ["custom"]

    tenant_builtin = client.post(
        "/api/platform/tenant-models",
        headers=tenant_headers,
        json={"provider": "deepseek", "model_name": "deepseek-v4-pro", "api_key": "sk-tenant-secret"},
    )
    assert tenant_builtin.status_code == 400

    other_headers, _ = _register_tenant_owner(
        client,
        tenant_id="tenant-b",
        account="tenant-b-owner@example.com",
    )
    other_available = client.get("/api/platform/models/available", headers=other_headers)
    assert any(item["model_config_id"] == platform_model_id for item in other_available.json()["models"])
    assert all(item["model_config_id"] != tenant_model_id for item in other_available.json()["models"])

    create_agent = client.post(
        "/api/platform/agents",
        headers=tenant_headers,
        json={
            "tenant_id": tenant_id,
            "agent_id": "writer",
            "name": "Writer",
            "model_config_id": platform_model_id,
        },
    )
    assert create_agent.status_code == 200, create_agent.text
    assert create_agent.json()["agent"]["model"] == "gpt-5.4"
    assert create_agent.json()["agent"]["model_config_id"] == platform_model_id

    member = client.post(
        "/api/platform/tenant-users",
        headers=tenant_headers,
        json={
            "tenant_id": tenant_id,
            "account": "tenant-a-member@example.com",
            "name": "Member",
            "role": "member",
            "password": "admin123456",
        },
    )
    assert member.status_code == 200, member.text
    member_login = client.post(
        "/api/platform/auth/login",
        json={"account": "tenant-a-member@example.com", "password": "admin123456"},
    )
    member_create_model = client.post(
        "/api/platform/tenant-models",
        headers=_headers(member_login.json()["token"]),
        json={"provider": "openai", "model_name": "member-model"},
    )
    assert member_create_model.status_code == 403


@pytest.mark.integration
def test_runtime_uses_resolved_model_config_overrides(tmp_path, monkeypatch) -> None:
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))
    monkeypatch.setitem(conf(), "model", "legacy-model")
    monkeypatch.setitem(conf(), "dashscope_api_key", "")

    app = create_app(PlatformSettings(host="127.0.0.1", port=9942, mode="test"))
    client = TestClient(app, raise_server_exceptions=False)
    platform = client.post(
        "/api/platform/auth/register-platform-admin",
        json={"account": "runtime-root@example.com", "password": "admin123456"},
    )
    platform_headers = _headers(platform.json()["token"])
    tenant_headers, tenant_id = _register_tenant_owner(
        client,
        tenant_id="tenant-runtime",
        account="runtime-owner@example.com",
    )

    model = client.post(
        "/api/platform/admin/models",
        headers=platform_headers,
        json={
            "provider": "dashscope",
            "model_name": "qwen3.6-plus",
            "api_key": "dashscope-runtime-key",
        },
    )
    model_config_id = model.json()["model"]["model_config_id"]
    agent = client.post(
        "/api/platform/agents",
        headers=tenant_headers,
        json={
            "tenant_id": tenant_id,
            "agent_id": "runtime-agent",
            "name": "Runtime Agent",
            "model_config_id": model_config_id,
        },
    )
    assert agent.status_code == 200, agent.text

    context = Context(ContextType.TEXT, "hello", kwargs={})
    context["tenant_id"] = tenant_id
    context["agent_id"] = "runtime-agent"
    context["session_id"] = "sid-1"
    context["request_id"] = "req-1"
    context["receiver"] = "user-1"
    context["channel_type"] = "web"

    resolved = CowAgentRuntimeAdapter().resolve_from_context(context)
    assert resolved is not None
    assert resolved.runtime_context.metadata["model_config"]["model_config_id"] == model_config_id
    assert resolved.runtime_context.metadata["config_overrides"]["dashscope_api_key"] == "dashscope-runtime-key"

    with resolved.activate():
        assert get_current_model_name() == "qwen3.6-plus"
        assert conf().get("model") == "qwen3.6-plus"
        assert conf().get("dashscope_api_key") == "dashscope-runtime-key"

    custom_model = client.post(
        "/api/platform/tenant-models",
        headers=tenant_headers,
        json={
            "provider": "custom",
            "model_name": "local-custom-model",
            "api_base": "https://custom-runtime.example.test/v1",
            "api_key": "custom-runtime-key",
        },
    )
    assert custom_model.status_code == 200, custom_model.text
    custom_model_config_id = custom_model.json()["model"]["model_config_id"]
    custom_agent = client.post(
        "/api/platform/agents",
        headers=tenant_headers,
        json={
            "tenant_id": tenant_id,
            "agent_id": "custom-runtime-agent",
            "name": "Custom Runtime Agent",
            "model_config_id": custom_model_config_id,
        },
    )
    assert custom_agent.status_code == 200, custom_agent.text

    custom_context = Context(ContextType.TEXT, "hello", kwargs={})
    custom_context["tenant_id"] = tenant_id
    custom_context["agent_id"] = "custom-runtime-agent"
    custom_context["session_id"] = "sid-2"
    custom_context["request_id"] = "req-2"
    custom_context["receiver"] = "user-1"
    custom_context["channel_type"] = "web"

    custom_resolved = CowAgentRuntimeAdapter().resolve_from_context(custom_context)
    assert custom_resolved is not None
    custom_overrides = custom_resolved.runtime_context.metadata["config_overrides"]
    assert custom_overrides["bot_type"] == "openai"
    assert custom_overrides["open_ai_api_base"] == "https://custom-runtime.example.test/v1"
    assert custom_overrides["open_ai_api_key"] == "custom-runtime-key"

    with custom_resolved.activate():
        assert get_current_model_name() == "local-custom-model"
        assert conf().get("model") == "local-custom-model"
        assert conf().get("bot_type") == "openai"
        assert conf().get("open_ai_api_base") == "https://custom-runtime.example.test/v1"
        assert conf().get("open_ai_api_key") == "custom-runtime-key"

import pytest
from fastapi.testclient import TestClient

from config import conf
from cow_platform.api.app import create_app
from cow_platform.api.settings import PlatformSettings
from cow_platform.services.usage_service import UsageService


def _register_owner(client: TestClient, account: str, tenant_name: str) -> tuple[dict[str, str], str]:
    response = client.post(
        "/api/platform/auth/register",
        json={
            "tenant_name": tenant_name,
            "account": account,
            "user_name": "Owner",
            "password": "admin123456",
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    return {"Authorization": f"Bearer {payload['token']}"}, payload["tenant"]["tenant_id"]


@pytest.mark.integration
def test_platform_api_requires_token_and_scopes_tenant_data(tmp_path, monkeypatch) -> None:
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "workspace"))
    monkeypatch.setitem(conf(), "model", "test-model")

    app = create_app(PlatformSettings(host="127.0.0.1", port=9941, mode="test"))
    client = TestClient(app)

    assert client.get("/api/platform/tenants").status_code == 401
    assert client.post("/api/platform/agents", json={"name": "No Auth"}).status_code == 401

    headers_a, tenant_a = _register_owner(client, "owner-a@example.com", "Tenant A")
    headers_b, tenant_b = _register_owner(client, "owner-b@example.com", "Tenant B")

    tenant_list = client.get("/api/platform/tenants", headers=headers_a)
    assert tenant_list.status_code == 200
    assert [item["tenant_id"] for item in tenant_list.json()["tenants"]] == [tenant_a]

    cross_tenant = client.get(f"/api/platform/tenants/{tenant_b}", headers=headers_a)
    assert cross_tenant.status_code == 403

    create_agent = client.post(
        "/api/platform/agents",
        headers=headers_a,
        json={
            "tenant_id": tenant_a,
            "name": "Writer",
            "model": "qwen-plus",
            "system_prompt": "Only tenant A.",
        },
    )
    assert create_agent.status_code == 200
    agent_id = create_agent.json()["agent"]["agent_id"]

    create_cross_agent = client.post(
        "/api/platform/agents",
        headers=headers_a,
        json={"tenant_id": tenant_b, "name": "Cross Tenant"},
    )
    assert create_cross_agent.status_code == 403

    UsageService().record_chat_usage(
        request_id="req-a",
        tenant_id=tenant_a,
        agent_id=agent_id,
        model="qwen-plus",
        prompt_tokens=11,
        completion_tokens=13,
        created_at="2026-04-24T10:00:00",
    )
    UsageService().record_chat_usage(
        request_id="req-b",
        tenant_id=tenant_b,
        agent_id="default",
        model="qwen-plus",
        prompt_tokens=100,
        completion_tokens=200,
        created_at="2026-04-24T10:00:00",
    )

    own_cost = client.get("/api/platform/costs", headers=headers_a)
    assert own_cost.status_code == 200
    assert own_cost.json()["summary"]["total_tokens"] == 24

    own_usage = client.get("/api/platform/usage", headers=headers_a)
    assert own_usage.status_code == 200
    assert [item["request_id"] for item in own_usage.json()["usage"]] == ["req-a"]

    cross_usage = client.get("/api/platform/usage", headers=headers_a, params={"tenant_id": tenant_b})
    assert cross_usage.status_code == 403

    tenant_b_agents = client.get("/api/platform/agents", headers=headers_b)
    assert tenant_b_agents.status_code == 200
    assert {item["tenant_id"] for item in tenant_b_agents.json()["agents"]} == {tenant_b}

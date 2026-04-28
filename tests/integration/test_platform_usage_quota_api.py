import pytest
from fastapi.testclient import TestClient

from config import conf

from cow_platform.api.app import create_app
from cow_platform.api.settings import PlatformSettings
from cow_platform.services.usage_service import UsageService


def _register_owner(client: TestClient) -> tuple[dict[str, str], str]:
    response = client.post(
        "/api/platform/auth/register",
        json={
            "tenant_id": "acme",
            "tenant_name": "Acme 团队",
            "account": "usage-owner@example.com",
            "user_name": "Owner",
            "password": "admin123456",
        },
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}, response.json()["tenant"]["tenant_id"]


@pytest.mark.integration
def test_platform_usage_quota_and_cost_api_supports_phase3_resources(tmp_path, monkeypatch) -> None:
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))
    monkeypatch.setitem(conf(), "model", "legacy-model")

    app = create_app(PlatformSettings(host="127.0.0.1", port=9913, mode="test"))
    client = TestClient(app)
    headers, tenant_id = _register_owner(client)

    client.post(
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
    pricing_resp = client.post(
        "/api/platform/pricing",
        headers=headers,
        json={
            "model": "qwen-plus",
            "input_price_per_million": 2.0,
            "output_price_per_million": 8.0,
        },
    )
    quota_resp = client.post(
        "/api/platform/quotas",
        headers=headers,
        json={
            "scope_type": "agent",
            "tenant_id": tenant_id,
            "agent_id": "writer",
            "max_requests_per_day": 5,
            "max_tokens_per_day": 10000,
        },
    )

    usage_service = UsageService()
    usage_service.record_chat_usage(
        request_id="req-api-1",
        tenant_id=tenant_id,
        agent_id="writer",
        model="qwen-plus",
        prompt_tokens=1000,
        completion_tokens=500,
        created_at="2026-04-23T12:00:00",
        metadata={"status": "success", "tool_names": {"read": 2, "mcp_docs_search": 1}, "skill_names": {"xlsx": 1}},
    )

    list_pricing = client.get("/api/platform/pricing", headers=headers)
    list_quotas = client.get("/api/platform/quotas", headers=headers, params={"tenant_id": tenant_id, "agent_id": "writer"})
    list_usage = client.get("/api/platform/usage", headers=headers, params={"tenant_id": tenant_id, "agent_id": "writer"})
    analytics = client.get(
        "/api/platform/usage/analytics",
        headers=headers,
        params={
            "tenant_id": tenant_id,
            "agent_id": "writer",
            "bucket": "day",
            "start": "2026-04-23",
            "end": "2026-04-23",
        },
    )
    cost_summary = client.get("/api/platform/costs", headers=headers, params={"tenant_id": tenant_id, "agent_id": "writer"})

    assert pricing_resp.status_code == 200
    assert pricing_resp.json()["pricing"]["model"] == "qwen-plus"

    assert quota_resp.status_code == 200
    assert quota_resp.json()["quota"]["agent_id"] == "writer"

    assert list_pricing.status_code == 200
    assert any(item["model"] == "qwen-plus" for item in list_pricing.json()["pricing"])

    assert list_quotas.status_code == 200
    assert list_quotas.json()["quotas"][0]["max_requests_per_day"] == 5

    assert list_usage.status_code == 200
    assert list_usage.json()["usage"][0]["request_id"] == "req-api-1"

    assert analytics.status_code == 200
    analytics_payload = analytics.json()["analytics"]
    assert analytics_payload["summary"]["total_tokens"] == 1500
    assert analytics_payload["time_series"][0]["key"] == "2026-04-23"
    assert analytics_payload["models"][0]["key"] == "qwen-plus"
    assert analytics_payload["tools"][0] == {"key": "read", "count": 2}
    assert analytics_payload["mcp_tools"][0] == {"key": "mcp_docs_search", "count": 1}
    assert analytics_payload["skills"][0] == {"key": "xlsx", "count": 1}

    assert cost_summary.status_code == 200
    assert cost_summary.json()["summary"]["request_count"] == 1
    assert cost_summary.json()["summary"]["estimated_cost"] == 0.006

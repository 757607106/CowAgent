import pytest
from fastapi.testclient import TestClient

from config import conf

from cow_platform.api.app import create_app
from cow_platform.api.settings import PlatformSettings
from cow_platform.services.usage_service import UsageService


@pytest.mark.integration
def test_platform_usage_quota_and_cost_api_supports_phase3_resources(tmp_path, monkeypatch) -> None:
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))
    monkeypatch.setitem(conf(), "model", "legacy-model")

    app = create_app(PlatformSettings(host="127.0.0.1", port=9913, mode="test"))
    client = TestClient(app)

    client.post("/api/platform/tenants", json={"tenant_id": "acme", "name": "Acme 团队"})
    client.post(
        "/api/platform/agents",
        json={
            "tenant_id": "acme",
            "agent_id": "writer",
            "name": "写作助手",
            "model": "qwen-plus",
            "system_prompt": "你擅长写作。",
        },
    )
    pricing_resp = client.post(
        "/api/platform/pricing",
        json={
            "model": "qwen-plus",
            "input_price_per_million": 2.0,
            "output_price_per_million": 8.0,
        },
    )
    quota_resp = client.post(
        "/api/platform/quotas",
        json={
            "scope_type": "agent",
            "tenant_id": "acme",
            "agent_id": "writer",
            "max_requests_per_day": 5,
            "max_tokens_per_day": 10000,
        },
    )

    usage_service = UsageService()
    usage_service.record_chat_usage(
        request_id="req-api-1",
        tenant_id="acme",
        agent_id="writer",
        model="qwen-plus",
        prompt_tokens=1000,
        completion_tokens=500,
        created_at="2026-04-23T12:00:00",
        metadata={"status": "success"},
    )

    list_pricing = client.get("/api/platform/pricing")
    list_quotas = client.get("/api/platform/quotas", params={"tenant_id": "acme", "agent_id": "writer"})
    list_usage = client.get("/api/platform/usage", params={"tenant_id": "acme", "agent_id": "writer"})
    cost_summary = client.get("/api/platform/costs", params={"tenant_id": "acme", "agent_id": "writer"})

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

    assert cost_summary.status_code == 200
    assert cost_summary.json()["summary"]["request_count"] == 1
    assert cost_summary.json()["summary"]["estimated_cost"] == 0.006

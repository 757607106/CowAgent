from config import conf

from cow_platform.services.pricing_service import PricingService
from cow_platform.services.quota_service import QuotaService
from cow_platform.services.tenant_service import TenantService
from cow_platform.services.usage_service import UsageService
from tests.support.platform_fakes import (
    InMemoryPricingRepository,
    InMemoryQuotaRepository,
    InMemoryTenantRepository,
    InMemoryUsageRepository,
)


def test_usage_cost_and_quota_services_work_together(tmp_path, monkeypatch) -> None:
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))

    pricing_service = PricingService(repository=InMemoryPricingRepository())
    usage_service = UsageService(repository=InMemoryUsageRepository(), pricing_service=pricing_service)
    quota_service = QuotaService(repository=InMemoryQuotaRepository(), usage_service=usage_service)
    TenantService(repository=InMemoryTenantRepository()).create_tenant(tenant_id="acme", name="Acme")

    pricing = pricing_service.upsert_pricing(
        model="qwen-plus",
        input_price_per_million=2.0,
        output_price_per_million=8.0,
    )
    usage = usage_service.record_chat_usage(
        request_id="req-usage-1",
        tenant_id="acme",
        agent_id="writer",
        model="qwen-plus",
        prompt_tokens=1000,
        completion_tokens=500,
        tool_call_count=3,
        mcp_call_count=1,
        tool_error_count=1,
        tool_execution_time_ms=1250,
        created_at="2026-04-23T10:00:00",
        metadata={"status": "success"},
    )
    quota = quota_service.upsert_quota(
        scope_type="agent",
        tenant_id="acme",
        agent_id="writer",
        max_requests_per_day=1,
        max_tokens_per_day=2000,
    )
    denied = quota_service.check_request_allowed(
        tenant_id="acme",
        agent_id="writer",
        prompt_tokens=10,
        day="2026-04-23",
    )

    assert pricing["model"] == "qwen-plus"
    assert usage["total_tokens"] == 1500
    assert usage["token_source"] == "provider"
    assert usage["tool_call_count"] == 3
    assert usage["mcp_call_count"] == 1
    assert usage["tool_error_count"] == 1
    assert usage["tool_execution_time_ms"] == 1250
    assert usage["estimated_cost"] == 0.006
    assert quota["max_requests_per_day"] == 1
    assert denied["allowed"] is False
    assert denied["reason"] == "request_limit"

    summary = usage_service.summarize_usage(tenant_id="acme", agent_id="writer", day="2026-04-23")
    assert summary["provider_request_count"] == 1
    assert summary["estimated_request_count"] == 0
    assert summary["tool_call_count"] == 3
    assert summary["mcp_call_count"] == 1
    assert summary["tool_error_count"] == 1
    assert summary["tool_execution_time_ms"] == 1250


def test_usage_analytics_groups_tokens_models_tools_and_skills(tmp_path, monkeypatch) -> None:
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))

    pricing_service = PricingService(repository=InMemoryPricingRepository())
    usage_service = UsageService(repository=InMemoryUsageRepository(), pricing_service=pricing_service)
    pricing_service.upsert_pricing(model="qwen-plus", input_price_per_million=2.0, output_price_per_million=8.0)

    usage_service.record_chat_usage(
        request_id="req-analytics-1",
        tenant_id="acme",
        agent_id="writer",
        model="qwen-plus",
        prompt_tokens=100,
        completion_tokens=50,
        created_at="2026-04-23T10:00:00",
        metadata={"tool_names": {"read": 1, "mcp_docs_search": 1}, "skill_names": {"xlsx": 1}},
    )
    usage_service.record_chat_usage(
        request_id="req-analytics-2",
        tenant_id="acme",
        agent_id="reviewer",
        model="qwen-max",
        prompt_tokens=80,
        completion_tokens=20,
        created_at="2026-04-24T11:00:00",
        metadata={"tool_names": {"read": 2}, "skill_names": {"github": 1}},
    )

    analytics = usage_service.get_usage_analytics(
        tenant_id="acme",
        bucket="day",
        start="2026-04-23",
        end="2026-04-24",
    )

    assert analytics["summary"]["total_tokens"] == 250
    assert [item["key"] for item in analytics["time_series"]] == ["2026-04-23", "2026-04-24"]
    assert analytics["agents"][0]["key"] == "writer"
    assert analytics["models"][0]["key"] == "qwen-plus"
    assert analytics["tools"][0] == {"key": "read", "count": 3}
    assert analytics["mcp_tools"] == [{"key": "mcp_docs_search", "count": 1}]
    assert analytics["skills"][0] == {"key": "github", "count": 1}


def test_tenant_token_quota_uses_daily_summary(tmp_path, monkeypatch) -> None:
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))

    pricing_service = PricingService(repository=InMemoryPricingRepository())
    usage_service = UsageService(repository=InMemoryUsageRepository(), pricing_service=pricing_service)
    quota_service = QuotaService(repository=InMemoryQuotaRepository(), usage_service=usage_service)
    TenantService(repository=InMemoryTenantRepository()).create_tenant(tenant_id="team-a", name="Team A")

    usage_service.record_chat_usage(
        request_id="req-usage-2",
        tenant_id="team-a",
        agent_id="assistant",
        prompt_tokens=800,
        completion_tokens=400,
        created_at="2026-04-23T11:00:00",
    )
    quota_service.upsert_quota(
        scope_type="tenant",
        tenant_id="team-a",
        max_requests_per_day=0,
        max_tokens_per_day=1300,
    )

    denied = quota_service.check_request_allowed(
        tenant_id="team-a",
        agent_id="assistant",
        prompt_tokens=200,
        day="2026-04-23",
    )

    assert denied["allowed"] is False
    assert denied["reason"] == "token_limit"
    assert denied["scope"] == "tenant:team-a"

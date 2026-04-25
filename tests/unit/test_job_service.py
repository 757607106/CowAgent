from pathlib import Path

from config import conf

from cow_platform.services.agent_service import AgentService
from cow_platform.services.audit_service import AuditService
from cow_platform.services.job_service import JobService
from cow_platform.services.pricing_service import PricingService
from cow_platform.services.tenant_service import TenantService
from cow_platform.services.usage_service import UsageService
from tests.platform_fakes import (
    InMemoryAgentRepository,
    InMemoryAuditRepository,
    InMemoryJobRepository,
    InMemoryPricingRepository,
    InMemoryTenantRepository,
    InMemoryUsageRepository,
)


def test_job_service_can_run_usage_report_and_write_artifact(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))
    monkeypatch.setitem(conf(), "model", "qwen-plus")

    tenant_service = TenantService(repository=InMemoryTenantRepository())
    agent_service = AgentService(
        repository=InMemoryAgentRepository(tmp_path / "legacy"),
        tenant_service=tenant_service,
    )
    usage_service = UsageService(
        repository=InMemoryUsageRepository(),
        pricing_service=PricingService(repository=InMemoryPricingRepository()),
    )
    usage_service.record_chat_usage(
        request_id="req-job-1",
        tenant_id="default",
        agent_id="default",
        model="qwen-plus",
        prompt_tokens=100,
        completion_tokens=50,
        created_at="2026-04-23T13:00:00",
    )

    job_service = JobService(
        repository=InMemoryJobRepository(),
        usage_service=usage_service,
        agent_service=agent_service,
        audit_service=AuditService(repository=InMemoryAuditRepository()),
    )
    created = job_service.create_job(
        job_type="usage_report",
        tenant_id="default",
        agent_id="default",
        payload={"day": "2026-04-23"},
    )
    processed = job_service.run_once()

    assert created["status"] == "pending"
    assert processed is not None
    assert processed["status"] == "completed"
    assert processed["result"]["summary"]["request_count"] == 1
    assert Path(processed["result"]["artifact_path"]).exists()

from pathlib import Path

from config import conf

from cow_platform.services.job_service import JobService
from cow_platform.services.usage_service import UsageService


def test_job_service_can_run_usage_report_and_write_artifact(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))
    monkeypatch.setitem(conf(), "model", "qwen-plus")

    usage_service = UsageService()
    usage_service.record_chat_usage(
        request_id="req-job-1",
        tenant_id="default",
        agent_id="default",
        model="qwen-plus",
        prompt_tokens=100,
        completion_tokens=50,
        created_at="2026-04-23T13:00:00",
    )

    job_service = JobService(usage_service=usage_service)
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

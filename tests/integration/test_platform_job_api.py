import pytest
from fastapi.testclient import TestClient

from config import conf

from cow_platform.api.app import create_app
from cow_platform.api.settings import PlatformSettings
from cow_platform.services.job_service import JobService
from cow_platform.services.usage_service import UsageService


@pytest.mark.integration
def test_platform_job_api_can_enqueue_and_observe_jobs(tmp_path, monkeypatch) -> None:
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))
    monkeypatch.setitem(conf(), "model", "qwen-plus")

    usage_service = UsageService()
    usage_service.record_chat_usage(
        request_id="req-job-api-1",
        tenant_id="default",
        agent_id="default",
        model="qwen-plus",
        prompt_tokens=120,
        completion_tokens=80,
        created_at="2026-04-23T14:00:00",
    )

    app = create_app(PlatformSettings(host="127.0.0.1", port=9914, mode="test"))
    client = TestClient(app)

    create_resp = client.post(
        "/api/platform/jobs",
        json={
            "job_type": "usage_report",
            "tenant_id": "default",
            "agent_id": "default",
            "payload": {"day": "2026-04-23"},
        },
    )
    job_id = create_resp.json()["job"]["job_id"]

    list_resp = client.get("/api/platform/jobs")
    get_resp = client.get(f"/api/platform/jobs/{job_id}")

    processed = JobService(usage_service=usage_service).run_once()
    get_done_resp = client.get(f"/api/platform/jobs/{job_id}")

    assert create_resp.status_code == 200
    assert create_resp.json()["job"]["status"] == "pending"
    assert any(item["job_id"] == job_id for item in list_resp.json()["jobs"])
    assert get_resp.json()["job"]["status"] == "pending"
    assert processed is not None
    assert processed["status"] == "completed"
    assert get_done_resp.json()["job"]["status"] == "completed"
    assert get_done_resp.json()["job"]["result"]["summary"]["request_count"] == 1

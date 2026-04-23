import pytest
from fastapi.testclient import TestClient

from config import conf

from cow_platform.api.app import create_app
from cow_platform.api.settings import PlatformSettings


@pytest.mark.integration
def test_platform_governance_api_exposes_audit_logs_and_doctor(tmp_path, monkeypatch) -> None:
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))
    monkeypatch.setitem(conf(), "model", "qwen-plus")

    app = create_app(PlatformSettings(host="127.0.0.1", port=9915, mode="test"))
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

    audit_resp = client.get("/api/platform/audit-logs", params={"tenant_id": "acme"})
    doctor_resp = client.get("/api/platform/doctor")

    assert audit_resp.status_code == 200
    actions = [item["action"] for item in audit_resp.json()["audit_logs"]]
    assert "create_tenant" in actions
    assert "create_agent" in actions

    assert doctor_resp.status_code == 200
    assert doctor_resp.json()["report"]["status"] == "ok"
    assert doctor_resp.json()["report"]["checks"]["compose_platform"]["exists"] is True

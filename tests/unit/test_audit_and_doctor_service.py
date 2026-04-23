from pathlib import Path

from config import conf

from cow_platform.services.audit_service import AuditService
from cow_platform.services.doctor_service import DoctorService


def test_audit_and_doctor_services_work_for_platform_governance(tmp_path, monkeypatch) -> None:
    workspace = tmp_path / "legacy"
    workspace.mkdir(parents=True, exist_ok=True)
    monkeypatch.setitem(conf(), "agent_workspace", str(workspace))

    audit_service = AuditService()
    first = audit_service.record_event(
        action="create_agent",
        resource_type="agent",
        resource_id="writer",
        tenant_id="default",
        agent_id="writer",
    )
    second = audit_service.record_event(
        action="process_job",
        resource_type="job",
        resource_id="job-1",
        tenant_id="default",
        agent_id="writer",
    )

    records = audit_service.list_records(tenant_id="default", agent_id="writer")
    report = DoctorService().get_report()

    assert first["resource_id"] == "writer"
    assert second["resource_type"] == "job"
    assert records[0]["tenant_id"] == "default"
    assert report["checks"]["patch_register"]["exists"] is True
    assert report["checks"]["upgrade_sop"]["exists"] is True
    assert report["checks"]["adr_dir"]["exists"] is True
    assert report["status"] == "ok"

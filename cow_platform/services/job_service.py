from __future__ import annotations

import json
from datetime import datetime
from typing import Any
import uuid

from cow_platform.domain.models import JobDefinition
from cow_platform.repositories.job_repository import JobRepository
from cow_platform.services.agent_service import AgentService, DEFAULT_AGENT_ID, DEFAULT_TENANT_ID
from cow_platform.services.audit_service import AuditService
from cow_platform.services.usage_service import UsageService


class JobService:
    """Asynchronous job service backed by PostgreSQL."""

    def __init__(
        self,
        repository: JobRepository | None = None,
        usage_service: UsageService | None = None,
        agent_service: AgentService | None = None,
        audit_service: AuditService | None = None,
    ):
        self.repository = repository or JobRepository()
        self.usage_service = usage_service or UsageService()
        self.agent_service = agent_service or AgentService()
        self.audit_service = audit_service or AuditService()

    def create_job(
        self,
        *,
        job_type: str,
        tenant_id: str = DEFAULT_TENANT_ID,
        agent_id: str = DEFAULT_AGENT_ID,
        payload: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if agent_id:
            self.agent_service.resolve_agent(tenant_id=tenant_id, agent_id=agent_id)
        job = self.repository.create_job(
            job_id=f"job_{uuid.uuid4().hex}",
            job_type=job_type,
            tenant_id=tenant_id,
            agent_id=agent_id,
            payload=payload or {},
            metadata=metadata or {},
        )
        return self.serialize_job(job)

    def get_job(self, job_id: str) -> JobDefinition:
        definition = self.repository.get_job(job_id)
        if definition is None:
            raise KeyError(f"job not found: {job_id}")
        return definition

    def list_job_records(
        self,
        *,
        status: str = "",
        tenant_id: str = "",
        agent_id: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        return [
            self.serialize_job(item)
            for item in self.repository.list_jobs(
                status=status,
                tenant_id=tenant_id,
                agent_id=agent_id,
                limit=limit,
            )
        ]

    def run_once(self, *, job_type: str = "") -> dict[str, Any] | None:
        job = self.repository.claim_next_job(job_type=job_type)
        if job is None:
            return None
        try:
            result = self._execute_job(job)
            completed = self.repository.complete_job(job.job_id, result=result)
            self.audit_service.record_event(
                action="process_job",
                resource_type="job",
                resource_id=completed.job_id,
                tenant_id=completed.tenant_id,
                agent_id=completed.agent_id,
                metadata={"job_type": completed.job_type, "status": completed.status},
            )
            return self.serialize_job(completed)
        except Exception as exc:
            failed = self.repository.fail_job(job.job_id, str(exc))
            self.audit_service.record_event(
                action="process_job",
                resource_type="job",
                resource_id=failed.job_id,
                tenant_id=failed.tenant_id,
                agent_id=failed.agent_id,
                status="failed",
                metadata={"job_type": failed.job_type, "error_message": failed.error_message},
            )
            return self.serialize_job(failed)

    def _execute_job(self, job: JobDefinition) -> dict[str, Any]:
        if job.job_type == "usage_report":
            return self._build_usage_report(job)
        raise ValueError(f"unsupported job_type: {job.job_type}")

    def _build_usage_report(self, job: JobDefinition) -> dict[str, Any]:
        payload = dict(job.payload)
        day = str(payload.get("day") or datetime.now().strftime("%Y-%m-%d"))
        summary = self.usage_service.summarize_usage(
            tenant_id=job.tenant_id,
            agent_id=job.agent_id,
            day=day,
        )

        workspace = self.agent_service.get_agent_workspace(job.tenant_id, job.agent_id)
        artifact_dir = workspace / "artifacts" / "reports"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = artifact_dir / f"usage-{day}.json"
        report = {
            "job_id": job.job_id,
            "job_type": job.job_type,
            "tenant_id": job.tenant_id,
            "agent_id": job.agent_id,
            "day": day,
            "summary": summary,
        }
        artifact_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return {
            "artifact_path": str(artifact_path),
            "day": day,
            "summary": summary,
        }

    def serialize_job(self, definition: JobDefinition) -> dict[str, Any]:
        return self.repository.export_record(definition)

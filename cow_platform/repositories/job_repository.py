from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from cow_platform.domain.models import JobDefinition
from cow_platform.repositories.agent_repository import get_platform_data_root


class FileJobRepository:
    """基于目录队列的任务仓储。"""

    STATUSES = ("pending", "running", "completed", "failed")

    def __init__(self, queue_root: Path | None = None):
        self.queue_root = queue_root or (get_platform_data_root() / "jobs")
        self.queue_root.mkdir(parents=True, exist_ok=True)
        for status in self.STATUSES:
            self._status_dir(status).mkdir(parents=True, exist_ok=True)

    def create_job(
        self,
        *,
        job_id: str,
        job_type: str,
        tenant_id: str,
        agent_id: str = "",
        payload: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> JobDefinition:
        now = self._now()
        job = JobDefinition(
            job_id=job_id,
            job_type=job_type,
            tenant_id=tenant_id,
            agent_id=agent_id,
            status="pending",
            payload=payload or {},
            result={},
            attempts=0,
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
        )
        self._write_job("pending", job)
        return job

    def get_job(self, job_id: str) -> JobDefinition | None:
        for status in self.STATUSES:
            path = self._job_path(status, job_id)
            if path.exists():
                return self._read_job(path)
        return None

    def list_jobs(
        self,
        *,
        status: str = "",
        tenant_id: str = "",
        agent_id: str = "",
        limit: int = 100,
    ) -> list[JobDefinition]:
        statuses = [status] if status else list(self.STATUSES)
        items: list[JobDefinition] = []
        for current_status in statuses:
            for path in sorted(self._status_dir(current_status).glob("*.json"), key=lambda item: item.name, reverse=True):
                job = self._read_job(path)
                if tenant_id and job.tenant_id != tenant_id:
                    continue
                if agent_id and job.agent_id != agent_id:
                    continue
                items.append(job)
                if len(items) >= max(1, int(limit)):
                    return items
        return items

    def claim_next_job(self, *, job_type: str = "") -> JobDefinition | None:
        pending_dir = self._status_dir("pending")
        for path in sorted(pending_dir.glob("*.json"), key=lambda item: item.name):
            try:
                job = self._read_job(path)
            except FileNotFoundError:
                continue
            if job_type and job.job_type != job_type:
                continue

            running_job = JobDefinition(
                job_id=job.job_id,
                job_type=job.job_type,
                tenant_id=job.tenant_id,
                agent_id=job.agent_id,
                status="running",
                payload=job.payload,
                result=job.result,
                error_message="",
                attempts=int(job.attempts) + 1,
                created_at=job.created_at,
                updated_at=self._now(),
                started_at=self._now(),
                completed_at="",
                metadata=job.metadata,
            )
            running_path = self._job_path("running", job.job_id)
            try:
                os.replace(path, running_path)
                self._write_payload(running_path, asdict(running_job))
                return running_job
            except FileNotFoundError:
                continue
        return None

    def complete_job(self, job_id: str, result: dict[str, Any] | None = None) -> JobDefinition:
        current = self._read_job(self._job_path("running", job_id))
        completed = JobDefinition(
            job_id=current.job_id,
            job_type=current.job_type,
            tenant_id=current.tenant_id,
            agent_id=current.agent_id,
            status="completed",
            payload=current.payload,
            result=result or {},
            error_message="",
            attempts=current.attempts,
            created_at=current.created_at,
            updated_at=self._now(),
            started_at=current.started_at,
            completed_at=self._now(),
            metadata=current.metadata,
        )
        self._move_job("running", "completed", completed)
        return completed

    def fail_job(self, job_id: str, error_message: str) -> JobDefinition:
        current = self._read_job(self._job_path("running", job_id))
        failed = JobDefinition(
            job_id=current.job_id,
            job_type=current.job_type,
            tenant_id=current.tenant_id,
            agent_id=current.agent_id,
            status="failed",
            payload=current.payload,
            result=current.result,
            error_message=error_message,
            attempts=current.attempts,
            created_at=current.created_at,
            updated_at=self._now(),
            started_at=current.started_at,
            completed_at=self._now(),
            metadata=current.metadata,
        )
        self._move_job("running", "failed", failed)
        return failed

    def export_record(self, definition: JobDefinition) -> dict[str, Any]:
        return asdict(definition)

    def _move_job(self, source_status: str, target_status: str, definition: JobDefinition) -> None:
        source_path = self._job_path(source_status, definition.job_id)
        target_path = self._job_path(target_status, definition.job_id)
        self._write_payload(target_path, asdict(definition))
        source_path.unlink(missing_ok=True)

    def _write_job(self, status: str, definition: JobDefinition) -> None:
        self._write_payload(self._job_path(status, definition.job_id), asdict(definition))

    def _write_payload(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)

    def _read_job(self, path: Path) -> JobDefinition:
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        return self._to_definition(payload)

    def _status_dir(self, status: str) -> Path:
        return self.queue_root / status

    def _job_path(self, status: str, job_id: str) -> Path:
        return self._status_dir(status) / f"{job_id}.json"

    @staticmethod
    def _to_definition(record: dict[str, Any]) -> JobDefinition:
        return JobDefinition(
            job_id=record["job_id"],
            job_type=record["job_type"],
            tenant_id=record["tenant_id"],
            agent_id=record.get("agent_id", ""),
            status=record.get("status", "pending"),
            payload=record.get("payload", {}) or {},
            result=record.get("result", {}) or {},
            error_message=record.get("error_message", ""),
            attempts=int(record.get("attempts", 0)),
            created_at=record["created_at"],
            updated_at=record["updated_at"],
            started_at=record.get("started_at", ""),
            completed_at=record.get("completed_at", ""),
            metadata=record.get("metadata", {}) or {},
        )

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat(timespec="seconds")

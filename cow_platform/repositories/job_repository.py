from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any

from cow_platform.db import connect, jsonb
from cow_platform.domain.models import JobDefinition


class PostgresJobRepository:
    """PostgreSQL-backed job repository with row-level claiming."""

    STATUSES = ("pending", "running", "completed", "failed")

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
        with connect() as conn:
            row = conn.execute(
                """
                INSERT INTO platform_jobs
                    (job_id, job_type, tenant_id, agent_id, status, payload, result,
                     attempts, created_at, updated_at, metadata)
                VALUES (%s, %s, %s, %s, 'pending', %s, '{}'::jsonb, 0, %s, %s, %s)
                RETURNING *
                """,
                (
                    job_id,
                    job_type,
                    tenant_id,
                    agent_id,
                    jsonb(payload or {}),
                    now,
                    now,
                    jsonb(metadata or {}),
                ),
            ).fetchone()
            conn.commit()
        return self._to_definition(row)

    def get_job(self, job_id: str) -> JobDefinition | None:
        with connect() as conn:
            row = conn.execute("SELECT * FROM platform_jobs WHERE job_id = %s", (job_id,)).fetchone()
        return self._to_definition(row) if row else None

    def list_jobs(
        self,
        *,
        status: str = "",
        tenant_id: str = "",
        agent_id: str = "",
        limit: int = 100,
    ) -> list[JobDefinition]:
        conditions: list[str] = []
        params: list[Any] = []
        if status:
            conditions.append("status = %s")
            params.append(status)
        if tenant_id:
            conditions.append("tenant_id = %s")
            params.append(tenant_id)
        if agent_id:
            conditions.append("agent_id = %s")
            params.append(agent_id)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(max(1, int(limit)))
        with connect() as conn:
            rows = conn.execute(
                f"""
                SELECT *
                FROM platform_jobs
                {where}
                ORDER BY created_at DESC
                LIMIT %s
                """,
                tuple(params),
            ).fetchall()
        return [self._to_definition(row) for row in rows]

    def claim_next_job(self, *, job_type: str = "") -> JobDefinition | None:
        now = self._now()
        job_filter = "AND job_type = %s" if job_type else ""
        params = (job_type,) if job_type else ()
        with connect() as conn:
            row = conn.execute(
                f"""
                WITH next_job AS (
                    SELECT job_id
                    FROM platform_jobs
                    WHERE status = 'pending' {job_filter}
                    ORDER BY created_at ASC
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                )
                UPDATE platform_jobs j
                SET status = 'running',
                    attempts = attempts + 1,
                    updated_at = %s,
                    started_at = %s,
                    error_message = ''
                FROM next_job
                WHERE j.job_id = next_job.job_id
                RETURNING j.*
                """,
                (*params, now, now),
            ).fetchone()
            conn.commit()
        return self._to_definition(row) if row else None

    def complete_job(self, job_id: str, result: dict[str, Any] | None = None) -> JobDefinition:
        now = self._now()
        with connect() as conn:
            row = conn.execute(
                """
                UPDATE platform_jobs
                SET status = 'completed', result = %s, error_message = '',
                    updated_at = %s, completed_at = %s
                WHERE job_id = %s AND status = 'running'
                RETURNING *
                """,
                (jsonb(result or {}), now, now, job_id),
            ).fetchone()
            conn.commit()
        if not row:
            raise KeyError(f"running job not found: {job_id}")
        return self._to_definition(row)

    def fail_job(self, job_id: str, error_message: str) -> JobDefinition:
        now = self._now()
        with connect() as conn:
            row = conn.execute(
                """
                UPDATE platform_jobs
                SET status = 'failed', error_message = %s,
                    updated_at = %s, completed_at = %s
                WHERE job_id = %s AND status = 'running'
                RETURNING *
                """,
                (error_message, now, now, job_id),
            ).fetchone()
            conn.commit()
        if not row:
            raise KeyError(f"running job not found: {job_id}")
        return self._to_definition(row)

    def export_record(self, definition: JobDefinition) -> dict[str, Any]:
        return asdict(definition)

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


JobRepository = PostgresJobRepository

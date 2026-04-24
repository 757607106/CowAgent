from __future__ import annotations

from dataclasses import asdict
from typing import Any

from cow_platform.db import connect, jsonb
from cow_platform.domain.models import AuditLogRecord


class PostgresAuditRepository:
    """PostgreSQL-backed audit log repository."""

    def append_record(self, record: AuditLogRecord) -> AuditLogRecord:
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO platform_audit_logs
                    (audit_id, action, resource_type, resource_id, status,
                     tenant_id, agent_id, actor, created_at, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    record.audit_id,
                    record.action,
                    record.resource_type,
                    record.resource_id,
                    record.status,
                    record.tenant_id,
                    record.agent_id,
                    record.actor,
                    record.created_at,
                    jsonb(record.metadata or {}),
                ),
            )
            conn.commit()
        return record

    def list_records(
        self,
        *,
        action: str = "",
        resource_type: str = "",
        tenant_id: str = "",
        agent_id: str = "",
        limit: int = 100,
    ) -> list[AuditLogRecord]:
        conditions: list[str] = []
        params: list[Any] = []
        if action:
            conditions.append("action = %s")
            params.append(action)
        if resource_type:
            conditions.append("resource_type = %s")
            params.append(resource_type)
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
                FROM platform_audit_logs
                {where}
                ORDER BY created_at DESC
                LIMIT %s
                """,
                tuple(params),
            ).fetchall()
        return [self._to_definition(row) for row in rows]

    @staticmethod
    def export_record(definition: AuditLogRecord) -> dict[str, Any]:
        return asdict(definition)

    @staticmethod
    def _to_definition(record: dict[str, Any]) -> AuditLogRecord:
        return AuditLogRecord(
            audit_id=record["audit_id"],
            action=record["action"],
            resource_type=record["resource_type"],
            resource_id=record["resource_id"],
            status=record["status"],
            tenant_id=record.get("tenant_id", ""),
            agent_id=record.get("agent_id", ""),
            actor=record.get("actor", "system"),
            created_at=record["created_at"],
            metadata=record.get("metadata", {}) or {},
        )


AuditRepository = PostgresAuditRepository

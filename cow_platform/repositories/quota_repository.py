from __future__ import annotations

from dataclasses import asdict
from typing import Any

from cow_platform.db import connect, jsonb
from cow_platform.domain.models import QuotaDefinition


class PostgresQuotaRepository:
    """PostgreSQL-backed quota repository."""

    def list_quotas(
        self,
        *,
        scope_type: str = "",
        tenant_id: str = "",
        agent_id: str = "",
    ) -> list[QuotaDefinition]:
        conditions: list[str] = []
        params: list[Any] = []
        if scope_type:
            conditions.append("scope_type = %s")
            params.append(scope_type)
        if tenant_id:
            conditions.append("tenant_id = %s")
            params.append(tenant_id)
        if agent_id:
            conditions.append("agent_id = %s")
            params.append(agent_id)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with connect() as conn:
            rows = conn.execute(
                f"""
                SELECT scope_type, tenant_id, agent_id, max_requests_per_day,
                       max_tokens_per_day, enabled, metadata
                FROM platform_quotas
                {where}
                ORDER BY scope_type, tenant_id, agent_id
                """,
                tuple(params),
            ).fetchall()
        return [self._to_definition(row) for row in rows]

    def get_quota(self, *, scope_type: str, tenant_id: str, agent_id: str = "") -> QuotaDefinition | None:
        with connect() as conn:
            row = conn.execute(
                """
                SELECT scope_type, tenant_id, agent_id, max_requests_per_day,
                       max_tokens_per_day, enabled, metadata
                FROM platform_quotas
                WHERE scope_type = %s AND tenant_id = %s AND agent_id = %s
                """,
                (scope_type, tenant_id, agent_id),
            ).fetchone()
        return self._to_definition(row) if row else None

    def upsert_quota(
        self,
        *,
        scope_type: str,
        tenant_id: str,
        agent_id: str = "",
        max_requests_per_day: int = 0,
        max_tokens_per_day: int = 0,
        enabled: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> QuotaDefinition:
        with connect() as conn:
            row = conn.execute(
                """
                INSERT INTO platform_quotas
                    (scope_type, tenant_id, agent_id, max_requests_per_day,
                     max_tokens_per_day, enabled, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (scope_type, tenant_id, agent_id)
                DO UPDATE SET
                    max_requests_per_day = EXCLUDED.max_requests_per_day,
                    max_tokens_per_day = EXCLUDED.max_tokens_per_day,
                    enabled = EXCLUDED.enabled,
                    metadata = EXCLUDED.metadata
                RETURNING scope_type, tenant_id, agent_id, max_requests_per_day,
                          max_tokens_per_day, enabled, metadata
                """,
                (
                    scope_type,
                    tenant_id,
                    agent_id,
                    int(max_requests_per_day),
                    int(max_tokens_per_day),
                    bool(enabled),
                    jsonb(metadata or {}),
                ),
            ).fetchone()
            conn.commit()
        return self._to_definition(row)

    def export_record(self, definition: QuotaDefinition) -> dict[str, Any]:
        return asdict(definition)

    @staticmethod
    def _to_definition(record: dict[str, Any]) -> QuotaDefinition:
        return QuotaDefinition(
            scope_type=record["scope_type"],
            tenant_id=record["tenant_id"],
            agent_id=record.get("agent_id", ""),
            max_requests_per_day=int(record.get("max_requests_per_day", 0)),
            max_tokens_per_day=int(record.get("max_tokens_per_day", 0)),
            enabled=bool(record.get("enabled", True)),
            metadata=record.get("metadata", {}) or {},
        )


QuotaRepository = PostgresQuotaRepository

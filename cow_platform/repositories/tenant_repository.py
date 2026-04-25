from __future__ import annotations

import time
from typing import Any

from psycopg import errors

from cow_platform.db import connect, jsonb
from cow_platform.domain.models import TenantDefinition


class PostgresTenantRepository:
    """PostgreSQL-backed tenant repository."""

    def list_tenants(self) -> list[TenantDefinition]:
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT tenant_id, name, status, metadata
                FROM platform_tenants
                ORDER BY tenant_id, name
                """
            ).fetchall()
        return [self._to_definition(row) for row in rows]

    def get_tenant(self, tenant_id: str) -> TenantDefinition | None:
        with connect() as conn:
            row = conn.execute(
                """
                SELECT tenant_id, name, status, metadata
                FROM platform_tenants
                WHERE tenant_id = %s
                """,
                (tenant_id,),
            ).fetchone()
        return self._to_definition(row) if row else None

    def create_tenant(
        self,
        tenant_id: str,
        name: str,
        *,
        status: str = "active",
        metadata: dict[str, Any] | None = None,
    ) -> TenantDefinition:
        now = int(time.time())
        try:
            with connect() as conn:
                row = conn.execute(
                    """
                    INSERT INTO platform_tenants
                        (tenant_id, name, status, metadata, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING tenant_id, name, status, metadata
                    """,
                    (tenant_id, name, status, jsonb(metadata or {}), now, now),
                ).fetchone()
                conn.commit()
        except errors.UniqueViolation as exc:
            raise ValueError(f"tenant already exists: {tenant_id}") from exc
        return self._to_definition(row)

    def update_tenant(
        self,
        tenant_id: str,
        *,
        name: str | None = None,
        status: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TenantDefinition:
        current = self.export_record_by_id(tenant_id)
        next_name = current["name"] if name is None else name
        next_status = current["status"] if status is None else status
        next_metadata = current["metadata"] if metadata is None else metadata
        with connect() as conn:
            row = conn.execute(
                """
                UPDATE platform_tenants
                SET name = %s, status = %s, metadata = %s, updated_at = %s
                WHERE tenant_id = %s
                RETURNING tenant_id, name, status, metadata
                """,
                (next_name, next_status, jsonb(next_metadata), int(time.time()), tenant_id),
            ).fetchone()
            conn.commit()
        if not row:
            raise KeyError(f"tenant not found: {tenant_id}")
        return self._to_definition(row)

    def delete_tenant(self, tenant_id: str) -> TenantDefinition:
        return self.update_tenant(tenant_id, status="deleted")

    def export_record(self, definition: TenantDefinition) -> dict[str, Any]:
        return self.export_record_by_id(definition.tenant_id)

    def export_record_by_id(self, tenant_id: str) -> dict[str, Any]:
        with connect() as conn:
            row = conn.execute(
                """
                SELECT tenant_id, name, status, metadata, created_at, updated_at
                FROM platform_tenants
                WHERE tenant_id = %s
                """,
                (tenant_id,),
            ).fetchone()
        if not row:
            raise KeyError(f"tenant not found: {tenant_id}")
        return dict(row)

    @staticmethod
    def _to_definition(record: dict[str, Any]) -> TenantDefinition:
        return TenantDefinition(
            tenant_id=record["tenant_id"],
            name=record["name"],
            status=record.get("status", "active"),
            metadata=record.get("metadata", {}) or {},
        )


TenantRepository = PostgresTenantRepository

from __future__ import annotations

import time
from types import MappingProxyType
from typing import Any

from cow_platform.db.postgres import connect, jsonb
from cow_platform.domain.models import TenantMcpServerDefinition


class PostgresTenantMcpServerRepository:
    """Tenant-scoped MCP server configuration repository."""

    def list_servers(self, tenant_id: str) -> list[TenantMcpServerDefinition]:
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT tenant_id, name, command, args, env, enabled, metadata
                FROM platform_mcp_servers
                WHERE tenant_id = %s
                ORDER BY name
                """,
                (tenant_id,),
            ).fetchall()
        return [self._to_definition(row) for row in rows]

    def get_server(self, tenant_id: str, name: str) -> TenantMcpServerDefinition | None:
        with connect() as conn:
            row = conn.execute(
                """
                SELECT tenant_id, name, command, args, env, enabled, metadata
                FROM platform_mcp_servers
                WHERE tenant_id = %s AND name = %s
                """,
                (tenant_id, name),
            ).fetchone()
        return self._to_definition(row) if row else None

    def upsert_server(
        self,
        *,
        tenant_id: str,
        name: str,
        command: str,
        args: list[str] | tuple[str, ...] | None = None,
        env: dict[str, str] | None = None,
        enabled: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> TenantMcpServerDefinition:
        now = int(time.time())
        with connect() as conn:
            row = conn.execute(
                """
                INSERT INTO platform_mcp_servers
                    (tenant_id, name, command, args, env, enabled, metadata, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (tenant_id, name) DO UPDATE SET
                    command = EXCLUDED.command,
                    args = EXCLUDED.args,
                    env = EXCLUDED.env,
                    enabled = EXCLUDED.enabled,
                    metadata = EXCLUDED.metadata,
                    updated_at = EXCLUDED.updated_at
                RETURNING tenant_id, name, command, args, env, enabled, metadata
                """,
                (
                    tenant_id,
                    name,
                    command,
                    jsonb(list(args or [])),
                    jsonb(env or {}),
                    bool(enabled),
                    jsonb(metadata or {}),
                    now,
                    now,
                ),
            ).fetchone()
            conn.commit()
        return self._to_definition(row)

    def delete_server(self, tenant_id: str, name: str) -> TenantMcpServerDefinition:
        with connect() as conn:
            row = conn.execute(
                """
                DELETE FROM platform_mcp_servers
                WHERE tenant_id = %s AND name = %s
                RETURNING tenant_id, name, command, args, env, enabled, metadata
                """,
                (tenant_id, name),
            ).fetchone()
            conn.commit()
        if not row:
            raise KeyError(f"mcp server not found: {name}")
        return self._to_definition(row)

    @staticmethod
    def export_record(definition: TenantMcpServerDefinition) -> dict[str, Any]:
        return {
            "tenant_id": definition.tenant_id,
            "name": definition.name,
            "command": definition.command,
            "args": list(definition.args),
            "env": dict(definition.env),
            "enabled": definition.enabled,
            "metadata": dict(definition.metadata),
        }

    @staticmethod
    def _to_definition(record: dict[str, Any]) -> TenantMcpServerDefinition:
        return TenantMcpServerDefinition(
            tenant_id=record["tenant_id"],
            name=record["name"],
            command=record.get("command", ""),
            args=tuple(record.get("args", []) or []),
            env=MappingProxyType(record.get("env", {}) or {}),
            enabled=bool(record.get("enabled", True)),
            metadata=MappingProxyType(record.get("metadata", {}) or {}),
        )


TenantMcpServerRepository = PostgresTenantMcpServerRepository

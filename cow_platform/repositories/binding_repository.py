from __future__ import annotations

import time
from dataclasses import asdict
from typing import Any

from psycopg import errors

from cow_platform.db import connect, jsonb
from cow_platform.domain.models import ChannelBindingDefinition


class PostgresChannelBindingRepository:
    """PostgreSQL-backed channel binding repository."""

    def list_bindings(
        self,
        *,
        tenant_id: str = "",
        channel_type: str = "",
        channel_config_id: str = "",
    ) -> list[ChannelBindingDefinition]:
        conditions: list[str] = []
        params: list[Any] = []
        if tenant_id:
            conditions.append("tenant_id = %s")
            params.append(tenant_id)
        if channel_type:
            conditions.append("channel_type = %s")
            params.append(channel_type)
        if channel_config_id:
            conditions.append("channel_config_id = %s")
            params.append(channel_config_id)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with connect() as conn:
            rows = conn.execute(
                f"""
                SELECT tenant_id, binding_id, name, channel_type, channel_config_id, agent_id,
                       version, enabled, metadata
                FROM platform_bindings
                {where}
                ORDER BY tenant_id, channel_type, channel_config_id, binding_id
                """,
                tuple(params),
            ).fetchall()
        return [self._to_definition(row) for row in rows]

    def get_binding(
        self,
        *,
        tenant_id: str = "",
        binding_id: str,
    ) -> ChannelBindingDefinition | None:
        if tenant_id:
            query = """
                SELECT tenant_id, binding_id, name, channel_type, channel_config_id, agent_id,
                       version, enabled, metadata
                FROM platform_bindings
                WHERE tenant_id = %s AND binding_id = %s
            """
            params = (tenant_id, binding_id)
        else:
            query = """
                SELECT tenant_id, binding_id, name, channel_type, channel_config_id, agent_id,
                       version, enabled, metadata
                FROM platform_bindings
                WHERE binding_id = %s
            """
            params = (binding_id,)
        with connect() as conn:
            row = conn.execute(query, params).fetchone()
        return self._to_definition(row) if row else None

    def create_binding(
        self,
        *,
        tenant_id: str,
        binding_id: str,
        name: str,
        channel_type: str,
        agent_id: str,
        channel_config_id: str = "",
        enabled: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> ChannelBindingDefinition:
        now = int(time.time())
        try:
            with connect() as conn:
                row = conn.execute(
                    """
                    INSERT INTO platform_bindings
                        (tenant_id, binding_id, name, channel_type, channel_config_id, agent_id, version,
                         enabled, metadata, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, 1, %s, %s, %s, %s)
                    RETURNING tenant_id, binding_id, name, channel_type, channel_config_id, agent_id,
                              version, enabled, metadata
                    """,
                    (
                        tenant_id,
                        binding_id,
                        name,
                        channel_type,
                        channel_config_id,
                        agent_id,
                        bool(enabled),
                        jsonb(metadata or {}),
                        now,
                        now,
                    ),
                ).fetchone()
                conn.commit()
        except errors.UniqueViolation as exc:
            raise ValueError(f"binding already exists: {binding_id}") from exc
        return self._to_definition(row)

    def update_binding(
        self,
        *,
        binding_id: str,
        tenant_id: str = "",
        name: str | None = None,
        channel_type: str | None = None,
        channel_config_id: str | None = None,
        agent_id: str | None = None,
        enabled: bool | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ChannelBindingDefinition:
        current = self.export_record_by_id(binding_id=binding_id, tenant_id=tenant_id)
        version = int(current.get("version", 1)) + 1
        with connect() as conn:
            row = conn.execute(
                """
                UPDATE platform_bindings
                SET name = %s, channel_type = %s, channel_config_id = %s, agent_id = %s, version = %s,
                    enabled = %s, metadata = %s, updated_at = %s
                WHERE tenant_id = %s AND binding_id = %s
                RETURNING tenant_id, binding_id, name, channel_type, channel_config_id, agent_id,
                          version, enabled, metadata
                """,
                (
                    current["name"] if name is None else name,
                    current["channel_type"] if channel_type is None else channel_type,
                    current["channel_config_id"] if channel_config_id is None else channel_config_id,
                    current["agent_id"] if agent_id is None else agent_id,
                    version,
                    current["enabled"] if enabled is None else bool(enabled),
                    jsonb(current["metadata"] if metadata is None else metadata),
                    int(time.time()),
                    current["tenant_id"],
                    current["binding_id"],
                ),
            ).fetchone()
            conn.commit()
        if not row:
            raise KeyError(f"binding not found: {binding_id}")
        return self._to_definition(row)

    def export_record(self, definition: ChannelBindingDefinition) -> dict[str, Any]:
        try:
            return self.export_record_by_id(binding_id=definition.binding_id, tenant_id=definition.tenant_id)
        except KeyError:
            record = asdict(definition)
            record["created_at"] = None
            record["updated_at"] = None
            return record

    def export_record_by_id(self, *, binding_id: str, tenant_id: str = "") -> dict[str, Any]:
        if tenant_id:
            where = "tenant_id = %s AND binding_id = %s"
            params = (tenant_id, binding_id)
        else:
            where = "binding_id = %s"
            params = (binding_id,)
        with connect() as conn:
            row = conn.execute(
                f"""
                SELECT tenant_id, binding_id, name, channel_type, channel_config_id, agent_id,
                       version, enabled, metadata, created_at, updated_at
                FROM platform_bindings
                WHERE {where}
                """,
                params,
            ).fetchone()
        if not row:
            raise KeyError(f"binding not found: {binding_id}")
        return dict(row)

    def delete_binding(
        self,
        *,
        binding_id: str,
        tenant_id: str = "",
    ) -> ChannelBindingDefinition:
        current = self.export_record_by_id(binding_id=binding_id, tenant_id=tenant_id)
        with connect() as conn:
            row = conn.execute(
                """
                DELETE FROM platform_bindings
                WHERE tenant_id = %s AND binding_id = %s
                RETURNING tenant_id, binding_id, name, channel_type, channel_config_id, agent_id,
                          version, enabled, metadata
                """,
                (current["tenant_id"], current["binding_id"]),
            ).fetchone()
            conn.commit()
        if not row:
            raise KeyError(f"binding not found: {binding_id}")
        return self._to_definition(row)

    @staticmethod
    def export_record_fallback(definition: ChannelBindingDefinition) -> dict[str, Any]:
        return asdict(definition)

    @staticmethod
    def _to_definition(record: dict[str, Any]) -> ChannelBindingDefinition:
        return ChannelBindingDefinition(
            tenant_id=record["tenant_id"],
            binding_id=record["binding_id"],
            name=record["name"],
            channel_type=record["channel_type"],
            agent_id=record["agent_id"],
            channel_config_id=record.get("channel_config_id", "") or "",
            version=int(record.get("version", 1)),
            enabled=bool(record.get("enabled", True)),
            metadata=record.get("metadata", {}) or {},
        )


ChannelBindingRepository = PostgresChannelBindingRepository

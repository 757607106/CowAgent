from __future__ import annotations

import time
from dataclasses import asdict
from typing import Any

from psycopg import errors

from cow_platform.db import connect, jsonb
from cow_platform.domain.models import ChannelConfigDefinition


class PostgresChannelConfigRepository:
    """PostgreSQL-backed tenant channel config repository."""

    def list_channel_configs(
        self,
        *,
        tenant_id: str = "",
        channel_type: str = "",
        enabled: bool | None = None,
    ) -> list[ChannelConfigDefinition]:
        conditions: list[str] = []
        params: list[Any] = []
        if tenant_id:
            conditions.append("tenant_id = %s")
            params.append(tenant_id)
        if channel_type:
            conditions.append("channel_type = %s")
            params.append(channel_type)
        if enabled is not None:
            conditions.append("enabled = %s")
            params.append(bool(enabled))
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with connect() as conn:
            rows = conn.execute(
                f"""
                SELECT tenant_id, channel_config_id, name, channel_type, config,
                       enabled, metadata, created_by
                FROM platform_channel_configs
                {where}
                ORDER BY tenant_id, channel_type, name, channel_config_id
                """,
                tuple(params),
            ).fetchall()
        return [self._to_definition(row) for row in rows]

    def get_channel_config(
        self,
        *,
        channel_config_id: str,
        tenant_id: str = "",
    ) -> ChannelConfigDefinition | None:
        if tenant_id:
            where = "tenant_id = %s AND channel_config_id = %s"
            params = (tenant_id, channel_config_id)
        else:
            where = "channel_config_id = %s"
            params = (channel_config_id,)
        with connect() as conn:
            row = conn.execute(
                f"""
                SELECT tenant_id, channel_config_id, name, channel_type, config,
                       enabled, metadata, created_by
                FROM platform_channel_configs
                WHERE {where}
                """,
                params,
            ).fetchone()
        return self._to_definition(row) if row else None

    def create_channel_config(
        self,
        *,
        tenant_id: str,
        channel_config_id: str,
        name: str,
        channel_type: str,
        config: dict[str, Any] | None = None,
        enabled: bool = True,
        metadata: dict[str, Any] | None = None,
        created_by: str = "",
    ) -> ChannelConfigDefinition:
        now = int(time.time())
        try:
            with connect() as conn:
                row = conn.execute(
                    """
                    INSERT INTO platform_channel_configs
                        (tenant_id, channel_config_id, name, channel_type, config,
                         enabled, metadata, created_by, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING tenant_id, channel_config_id, name, channel_type, config,
                              enabled, metadata, created_by
                    """,
                    (
                        tenant_id,
                        channel_config_id,
                        name,
                        channel_type,
                        jsonb(config or {}),
                        bool(enabled),
                        jsonb(metadata or {}),
                        created_by,
                        now,
                        now,
                    ),
                ).fetchone()
                conn.commit()
        except errors.UniqueViolation as exc:
            raise ValueError(f"channel config already exists: {channel_config_id}") from exc
        return self._to_definition(row)

    def update_channel_config(
        self,
        *,
        channel_config_id: str,
        tenant_id: str = "",
        name: str | None = None,
        channel_type: str | None = None,
        config: dict[str, Any] | None = None,
        enabled: bool | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ChannelConfigDefinition:
        current = self.export_record_by_id(channel_config_id=channel_config_id, tenant_id=tenant_id)
        with connect() as conn:
            row = conn.execute(
                """
                UPDATE platform_channel_configs
                SET name = %s, channel_type = %s, config = %s,
                    enabled = %s, metadata = %s, updated_at = %s
                WHERE tenant_id = %s AND channel_config_id = %s
                RETURNING tenant_id, channel_config_id, name, channel_type, config,
                          enabled, metadata, created_by
                """,
                (
                    current["name"] if name is None else name,
                    current["channel_type"] if channel_type is None else channel_type,
                    jsonb(current["config"] if config is None else config),
                    current["enabled"] if enabled is None else bool(enabled),
                    jsonb(current["metadata"] if metadata is None else metadata),
                    int(time.time()),
                    current["tenant_id"],
                    current["channel_config_id"],
                ),
            ).fetchone()
            conn.commit()
        if not row:
            raise KeyError(f"channel config not found: {channel_config_id}")
        return self._to_definition(row)

    def delete_channel_config(self, *, channel_config_id: str, tenant_id: str = "") -> ChannelConfigDefinition:
        current = self.export_record_by_id(channel_config_id=channel_config_id, tenant_id=tenant_id)
        with connect() as conn:
            row = conn.execute(
                """
                DELETE FROM platform_channel_configs
                WHERE tenant_id = %s AND channel_config_id = %s
                RETURNING tenant_id, channel_config_id, name, channel_type, config,
                          enabled, metadata, created_by
                """,
                (current["tenant_id"], current["channel_config_id"]),
            ).fetchone()
            conn.commit()
        if not row:
            raise KeyError(f"channel config not found: {channel_config_id}")
        return self._to_definition(row)

    def export_record(self, definition: ChannelConfigDefinition) -> dict[str, Any]:
        try:
            return self.export_record_by_id(
                channel_config_id=definition.channel_config_id,
                tenant_id=definition.tenant_id,
            )
        except KeyError:
            record = asdict(definition)
            record["created_at"] = None
            record["updated_at"] = None
            return record

    def export_record_by_id(self, *, channel_config_id: str, tenant_id: str = "") -> dict[str, Any]:
        if tenant_id:
            where = "tenant_id = %s AND channel_config_id = %s"
            params = (tenant_id, channel_config_id)
        else:
            where = "channel_config_id = %s"
            params = (channel_config_id,)
        with connect() as conn:
            row = conn.execute(
                f"""
                SELECT tenant_id, channel_config_id, name, channel_type, config,
                       enabled, metadata, created_by, created_at, updated_at
                FROM platform_channel_configs
                WHERE {where}
                """,
                params,
            ).fetchone()
        if not row:
            raise KeyError(f"channel config not found: {channel_config_id}")
        return dict(row)

    @staticmethod
    def _to_definition(record: dict[str, Any]) -> ChannelConfigDefinition:
        return ChannelConfigDefinition(
            tenant_id=record["tenant_id"],
            channel_config_id=record["channel_config_id"],
            name=record["name"],
            channel_type=record["channel_type"],
            config=record.get("config", {}) or {},
            enabled=bool(record.get("enabled", True)),
            metadata=record.get("metadata", {}) or {},
            created_by=record.get("created_by", "") or "",
        )


ChannelConfigRepository = PostgresChannelConfigRepository

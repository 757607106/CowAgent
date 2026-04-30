from __future__ import annotations

import time
from dataclasses import asdict
from typing import Any

from psycopg import errors

from cow_platform.db import connect, jsonb
from cow_platform.domain.models import CapabilityConfigDefinition


class PostgresCapabilityConfigRepository:
    """PostgreSQL-backed capability configuration repository."""

    def list_capability_configs(
        self,
        *,
        scope: str = "",
        tenant_id: str = "",
        capability: str = "",
        enabled: bool | None = None,
        public_only: bool = False,
    ) -> list[CapabilityConfigDefinition]:
        conditions: list[str] = []
        params: list[Any] = []
        if scope:
            conditions.append("scope = %s")
            params.append(scope)
        if tenant_id:
            conditions.append("tenant_id = %s")
            params.append(tenant_id)
        if capability:
            conditions.append("capability = %s")
            params.append(capability)
        if enabled is not None:
            conditions.append("enabled = %s")
            params.append(bool(enabled))
        if public_only:
            conditions.append("is_public = true")
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with connect() as conn:
            rows = conn.execute(
                f"""
                SELECT capability_config_id, scope, tenant_id, capability, provider,
                       model_name, display_name, api_key, api_base, enabled,
                       is_public, is_default, metadata, created_by
                FROM platform_capability_configs
                {where}
                ORDER BY scope, tenant_id, capability, is_default DESC, provider, display_name, model_name
                """,
                tuple(params),
            ).fetchall()
        return [self._to_definition(row) for row in rows]

    def get_capability_config(self, capability_config_id: str) -> CapabilityConfigDefinition | None:
        with connect() as conn:
            row = conn.execute(
                """
                SELECT capability_config_id, scope, tenant_id, capability, provider,
                       model_name, display_name, api_key, api_base, enabled,
                       is_public, is_default, metadata, created_by
                FROM platform_capability_configs
                WHERE capability_config_id = %s
                """,
                (capability_config_id,),
            ).fetchone()
        return self._to_definition(row) if row else None

    def create_capability_config(
        self,
        *,
        capability_config_id: str,
        scope: str,
        tenant_id: str = "",
        capability: str,
        provider: str,
        model_name: str,
        display_name: str = "",
        api_key: str = "",
        api_base: str = "",
        enabled: bool = True,
        is_public: bool = True,
        is_default: bool = False,
        metadata: dict[str, Any] | None = None,
        created_by: str = "",
    ) -> CapabilityConfigDefinition:
        now = int(time.time())
        try:
            with connect() as conn:
                row = conn.execute(
                    """
                    INSERT INTO platform_capability_configs
                        (capability_config_id, scope, tenant_id, capability, provider,
                         model_name, display_name, api_key, api_base, enabled,
                         is_public, is_default, metadata, created_by, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING capability_config_id, scope, tenant_id, capability, provider,
                              model_name, display_name, api_key, api_base, enabled,
                              is_public, is_default, metadata, created_by
                    """,
                    (
                        capability_config_id,
                        scope,
                        tenant_id,
                        capability,
                        provider,
                        model_name,
                        display_name,
                        api_key,
                        api_base,
                        bool(enabled),
                        bool(is_public),
                        bool(is_default),
                        jsonb(metadata or {}),
                        created_by,
                        now,
                        now,
                    ),
                ).fetchone()
                conn.commit()
        except errors.UniqueViolation as exc:
            raise ValueError(f"capability config already exists: {capability_config_id}") from exc
        return self._to_definition(row)

    def update_capability_config(
        self,
        capability_config_id: str,
        *,
        capability: str | None = None,
        provider: str | None = None,
        model_name: str | None = None,
        display_name: str | None = None,
        api_key: str | None = None,
        api_base: str | None = None,
        enabled: bool | None = None,
        is_public: bool | None = None,
        is_default: bool | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CapabilityConfigDefinition:
        current = self.export_record_by_id(capability_config_id)
        with connect() as conn:
            row = conn.execute(
                """
                UPDATE platform_capability_configs
                SET capability = %s,
                    provider = %s,
                    model_name = %s,
                    display_name = %s,
                    api_key = %s,
                    api_base = %s,
                    enabled = %s,
                    is_public = %s,
                    is_default = %s,
                    metadata = %s,
                    updated_at = %s
                WHERE capability_config_id = %s
                RETURNING capability_config_id, scope, tenant_id, capability, provider,
                          model_name, display_name, api_key, api_base, enabled,
                          is_public, is_default, metadata, created_by
                """,
                (
                    current["capability"] if capability is None else capability,
                    current["provider"] if provider is None else provider,
                    current["model_name"] if model_name is None else model_name,
                    current["display_name"] if display_name is None else display_name,
                    current["api_key"] if api_key is None else api_key,
                    current["api_base"] if api_base is None else api_base,
                    current["enabled"] if enabled is None else bool(enabled),
                    current["is_public"] if is_public is None else bool(is_public),
                    current["is_default"] if is_default is None else bool(is_default),
                    jsonb(current["metadata"] if metadata is None else metadata),
                    int(time.time()),
                    capability_config_id,
                ),
            ).fetchone()
            conn.commit()
        if not row:
            raise KeyError(f"capability config not found: {capability_config_id}")
        return self._to_definition(row)

    def unset_default_for_scope(
        self,
        *,
        scope: str,
        tenant_id: str,
        capability: str,
        except_id: str = "",
    ) -> None:
        conditions = ["scope = %s", "capability = %s"]
        params: list[Any] = [scope, capability]
        if scope == "tenant":
            conditions.append("tenant_id = %s")
            params.append(tenant_id)
        if except_id:
            conditions.append("capability_config_id != %s")
            params.append(except_id)
        with connect() as conn:
            conn.execute(
                f"""
                UPDATE platform_capability_configs
                SET is_default = false, updated_at = %s
                WHERE {' AND '.join(conditions)}
                """,
                (int(time.time()), *params),
            )
            conn.commit()

    def delete_capability_config(self, capability_config_id: str) -> CapabilityConfigDefinition:
        with connect() as conn:
            row = conn.execute(
                """
                DELETE FROM platform_capability_configs
                WHERE capability_config_id = %s
                RETURNING capability_config_id, scope, tenant_id, capability, provider,
                          model_name, display_name, api_key, api_base, enabled,
                          is_public, is_default, metadata, created_by
                """,
                (capability_config_id,),
            ).fetchone()
            conn.commit()
        if not row:
            raise KeyError(f"capability config not found: {capability_config_id}")
        return self._to_definition(row)

    def export_record(self, definition: CapabilityConfigDefinition) -> dict[str, Any]:
        try:
            return self.export_record_by_id(definition.capability_config_id)
        except KeyError:
            record = asdict(definition)
            record["created_at"] = None
            record["updated_at"] = None
            return record

    def export_record_by_id(self, capability_config_id: str) -> dict[str, Any]:
        with connect() as conn:
            row = conn.execute(
                """
                SELECT capability_config_id, scope, tenant_id, capability, provider,
                       model_name, display_name, api_key, api_base, enabled,
                       is_public, is_default, metadata, created_by, created_at, updated_at
                FROM platform_capability_configs
                WHERE capability_config_id = %s
                """,
                (capability_config_id,),
            ).fetchone()
        if not row:
            raise KeyError(f"capability config not found: {capability_config_id}")
        return dict(row)

    @staticmethod
    def _to_definition(record: dict[str, Any]) -> CapabilityConfigDefinition:
        return CapabilityConfigDefinition(
            capability_config_id=record["capability_config_id"],
            scope=record["scope"],
            tenant_id=record.get("tenant_id", ""),
            capability=record["capability"],
            provider=record["provider"],
            model_name=record["model_name"],
            display_name=record.get("display_name", ""),
            api_key=record.get("api_key", ""),
            api_base=record.get("api_base", ""),
            enabled=bool(record.get("enabled", True)),
            is_public=bool(record.get("is_public", True)),
            is_default=bool(record.get("is_default", False)),
            metadata=record.get("metadata", {}) or {},
            created_by=record.get("created_by", ""),
        )


CapabilityConfigRepository = PostgresCapabilityConfigRepository

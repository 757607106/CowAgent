from __future__ import annotations

import time
from dataclasses import asdict
from typing import Any

from psycopg import errors

from cow_platform.db import connect, jsonb
from cow_platform.domain.models import ModelConfigDefinition


class PostgresModelConfigRepository:
    """PostgreSQL-backed model configuration repository."""

    def list_model_configs(
        self,
        *,
        scope: str = "",
        tenant_id: str = "",
        enabled: bool | None = None,
    ) -> list[ModelConfigDefinition]:
        conditions: list[str] = []
        params: list[Any] = []
        if scope:
            conditions.append("scope = %s")
            params.append(scope)
        if tenant_id:
            conditions.append("tenant_id = %s")
            params.append(tenant_id)
        if enabled is not None:
            conditions.append("enabled = %s")
            params.append(bool(enabled))
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with connect() as conn:
            rows = conn.execute(
                f"""
                SELECT model_config_id, scope, tenant_id, provider, model_name,
                       display_name, api_key, api_base, enabled, is_public,
                       metadata, created_by
                FROM platform_model_configs
                {where}
                ORDER BY scope, tenant_id, provider, display_name, model_name
                """,
                tuple(params),
            ).fetchall()
        return [self._to_definition(row) for row in rows]

    def get_model_config(self, model_config_id: str) -> ModelConfigDefinition | None:
        with connect() as conn:
            row = conn.execute(
                """
                SELECT model_config_id, scope, tenant_id, provider, model_name,
                       display_name, api_key, api_base, enabled, is_public,
                       metadata, created_by
                FROM platform_model_configs
                WHERE model_config_id = %s
                """,
                (model_config_id,),
            ).fetchone()
        return self._to_definition(row) if row else None

    def create_model_config(
        self,
        *,
        model_config_id: str,
        scope: str,
        tenant_id: str = "",
        provider: str,
        model_name: str,
        display_name: str = "",
        api_key: str = "",
        api_base: str = "",
        enabled: bool = True,
        is_public: bool = True,
        metadata: dict[str, Any] | None = None,
        created_by: str = "",
    ) -> ModelConfigDefinition:
        now = int(time.time())
        try:
            with connect() as conn:
                row = conn.execute(
                    """
                    INSERT INTO platform_model_configs
                        (model_config_id, scope, tenant_id, provider, model_name,
                         display_name, api_key, api_base, enabled, is_public,
                         metadata, created_by, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING model_config_id, scope, tenant_id, provider, model_name,
                              display_name, api_key, api_base, enabled, is_public,
                              metadata, created_by
                    """,
                    (
                        model_config_id,
                        scope,
                        tenant_id,
                        provider,
                        model_name,
                        display_name,
                        api_key,
                        api_base,
                        bool(enabled),
                        bool(is_public),
                        jsonb(metadata or {}),
                        created_by,
                        now,
                        now,
                    ),
                ).fetchone()
                conn.commit()
        except errors.UniqueViolation as exc:
            raise ValueError(f"model config already exists: {model_config_id}") from exc
        return self._to_definition(row)

    def update_model_config(
        self,
        model_config_id: str,
        *,
        provider: str | None = None,
        model_name: str | None = None,
        display_name: str | None = None,
        api_key: str | None = None,
        api_base: str | None = None,
        enabled: bool | None = None,
        is_public: bool | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ModelConfigDefinition:
        current = self.export_record_by_id(model_config_id)
        with connect() as conn:
            row = conn.execute(
                """
                UPDATE platform_model_configs
                SET provider = %s,
                    model_name = %s,
                    display_name = %s,
                    api_key = %s,
                    api_base = %s,
                    enabled = %s,
                    is_public = %s,
                    metadata = %s,
                    updated_at = %s
                WHERE model_config_id = %s
                RETURNING model_config_id, scope, tenant_id, provider, model_name,
                          display_name, api_key, api_base, enabled, is_public,
                          metadata, created_by
                """,
                (
                    current["provider"] if provider is None else provider,
                    current["model_name"] if model_name is None else model_name,
                    current["display_name"] if display_name is None else display_name,
                    current["api_key"] if api_key is None else api_key,
                    current["api_base"] if api_base is None else api_base,
                    current["enabled"] if enabled is None else bool(enabled),
                    current["is_public"] if is_public is None else bool(is_public),
                    jsonb(current["metadata"] if metadata is None else metadata),
                    int(time.time()),
                    model_config_id,
                ),
            ).fetchone()
            conn.commit()
        if not row:
            raise KeyError(f"model config not found: {model_config_id}")
        return self._to_definition(row)

    def delete_model_config(self, model_config_id: str) -> ModelConfigDefinition:
        with connect() as conn:
            row = conn.execute(
                """
                DELETE FROM platform_model_configs
                WHERE model_config_id = %s
                RETURNING model_config_id, scope, tenant_id, provider, model_name,
                          display_name, api_key, api_base, enabled, is_public,
                          metadata, created_by
                """,
                (model_config_id,),
            ).fetchone()
            conn.commit()
        if not row:
            raise KeyError(f"model config not found: {model_config_id}")
        return self._to_definition(row)

    def export_record(self, definition: ModelConfigDefinition) -> dict[str, Any]:
        try:
            return self.export_record_by_id(definition.model_config_id)
        except KeyError:
            record = asdict(definition)
            record["created_at"] = None
            record["updated_at"] = None
            return record

    def export_record_by_id(self, model_config_id: str) -> dict[str, Any]:
        with connect() as conn:
            row = conn.execute(
                """
                SELECT model_config_id, scope, tenant_id, provider, model_name,
                       display_name, api_key, api_base, enabled, is_public,
                       metadata, created_by, created_at, updated_at
                FROM platform_model_configs
                WHERE model_config_id = %s
                """,
                (model_config_id,),
            ).fetchone()
        if not row:
            raise KeyError(f"model config not found: {model_config_id}")
        return dict(row)

    @staticmethod
    def _to_definition(record: dict[str, Any]) -> ModelConfigDefinition:
        return ModelConfigDefinition(
            model_config_id=record["model_config_id"],
            scope=record["scope"],
            tenant_id=record.get("tenant_id", ""),
            provider=record["provider"],
            model_name=record["model_name"],
            display_name=record.get("display_name", ""),
            api_key=record.get("api_key", ""),
            api_base=record.get("api_base", ""),
            enabled=bool(record.get("enabled", True)),
            is_public=bool(record.get("is_public", True)),
            metadata=record.get("metadata", {}) or {},
            created_by=record.get("created_by", ""),
        )


ModelConfigRepository = PostgresModelConfigRepository

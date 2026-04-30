from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from common.log import logger
from cow_platform.db import connect, jsonb
from cow_platform.runtime.namespaces import build_namespace


@dataclass(frozen=True, slots=True)
class RuntimeState:
    scope_key: str
    resource_type: str
    tenant_id: str
    agent_id: str
    config_version: int
    desired_state: dict[str, Any]
    metadata: dict[str, Any]
    invalidated_at: str
    updated_at: str


class RuntimeStateService:
    """Canonical runtime state and config-version service."""

    PLATFORM_SCOPE = "platform"
    TENANT_SCOPE = "tenant"
    AGENT_SCOPE = "agent"
    CHANNEL_CONFIG_SCOPE = "channel_config"

    def get_state(self, *, resource_type: str, tenant_id: str = "", agent_id: str = "") -> RuntimeState | None:
        scope_key = self.scope_key(resource_type=resource_type, tenant_id=tenant_id, agent_id=agent_id)
        with connect() as conn:
            row = conn.execute(
                """
                SELECT scope_key, resource_type, tenant_id, agent_id, config_version,
                       desired_state, metadata, invalidated_at, updated_at
                FROM platform_runtime_state
                WHERE scope_key = %s
                """,
                (scope_key,),
            ).fetchone()
        return self._from_row(row) if row else None

    def get_effective_config_version(self, *, tenant_id: str, agent_id: str) -> int:
        """Return the combined version that affects one tenant-agent runtime."""
        keys = [
            self.scope_key(resource_type=self.PLATFORM_SCOPE),
            self.scope_key(resource_type=self.TENANT_SCOPE, tenant_id=tenant_id),
            self.scope_key(resource_type=self.AGENT_SCOPE, tenant_id=tenant_id, agent_id=agent_id),
        ]
        with connect() as conn:
            row = conn.execute(
                """
                SELECT COALESCE(SUM(config_version), 0) AS version
                FROM platform_runtime_state
                WHERE scope_key = ANY(%s)
                """,
                (keys,),
            ).fetchone()
        return int((row or {}).get("version") or 0)

    def bump_config_version(
        self,
        *,
        resource_type: str,
        tenant_id: str = "",
        agent_id: str = "",
        reason: str = "",
        desired_state: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RuntimeState:
        normalized_resource_type = self._normalize_resource_type(resource_type)
        normalized_tenant_id = str(tenant_id or "").strip()
        normalized_agent_id = str(agent_id or "").strip()
        scope_key = self.scope_key(
            resource_type=normalized_resource_type,
            tenant_id=normalized_tenant_id,
            agent_id=normalized_agent_id,
        )
        now = self._now()
        merged_metadata = dict(metadata or {})
        if reason:
            merged_metadata["reason"] = reason
        with connect() as conn:
            row = conn.execute(
                """
                INSERT INTO platform_runtime_state (
                    scope_key, resource_type, tenant_id, agent_id, config_version,
                    desired_state, metadata, invalidated_at, updated_at
                )
                VALUES (%s, %s, %s, %s, 1, %s, %s, %s, %s)
                ON CONFLICT (scope_key) DO UPDATE
                SET config_version = platform_runtime_state.config_version + 1,
                    resource_type = EXCLUDED.resource_type,
                    tenant_id = EXCLUDED.tenant_id,
                    agent_id = EXCLUDED.agent_id,
                    desired_state = EXCLUDED.desired_state,
                    metadata = EXCLUDED.metadata,
                    invalidated_at = EXCLUDED.invalidated_at,
                    updated_at = EXCLUDED.updated_at
                RETURNING scope_key, resource_type, tenant_id, agent_id, config_version,
                          desired_state, metadata, invalidated_at, updated_at
                """,
                (
                    scope_key,
                    normalized_resource_type,
                    normalized_tenant_id,
                    normalized_agent_id,
                    jsonb(desired_state or {}),
                    jsonb(merged_metadata),
                    now,
                    now,
                ),
            ).fetchone()
        return self._from_row(row)

    def invalidate_platform(self, *, reason: str = "", metadata: dict[str, Any] | None = None) -> RuntimeState:
        return self.bump_config_version(
            resource_type=self.PLATFORM_SCOPE,
            reason=reason,
            metadata=metadata,
        )

    def invalidate_tenant(
        self,
        tenant_id: str,
        *,
        reason: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> RuntimeState:
        return self.bump_config_version(
            resource_type=self.TENANT_SCOPE,
            tenant_id=tenant_id,
            reason=reason,
            metadata=metadata,
        )

    def invalidate_agent(
        self,
        tenant_id: str,
        agent_id: str,
        *,
        reason: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> RuntimeState:
        return self.bump_config_version(
            resource_type=self.AGENT_SCOPE,
            tenant_id=tenant_id,
            agent_id=agent_id,
            reason=reason,
            metadata=metadata,
        )

    def invalidate_channel_config(
        self,
        channel_config_id: str,
        *,
        tenant_id: str = "",
        reason: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> RuntimeState:
        return self.bump_config_version(
            resource_type=self.CHANNEL_CONFIG_SCOPE,
            tenant_id=tenant_id,
            agent_id=channel_config_id,
            reason=reason,
            metadata=metadata,
        )

    def safe_invalidate_platform(self, *, reason: str = "", metadata: dict[str, Any] | None = None) -> None:
        self._safe(lambda: self.invalidate_platform(reason=reason, metadata=metadata))

    def safe_invalidate_tenant(self, tenant_id: str, *, reason: str = "", metadata: dict[str, Any] | None = None) -> None:
        self._safe(lambda: self.invalidate_tenant(tenant_id, reason=reason, metadata=metadata))

    def safe_invalidate_agent(
        self,
        tenant_id: str,
        agent_id: str,
        *,
        reason: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._safe(lambda: self.invalidate_agent(tenant_id, agent_id, reason=reason, metadata=metadata))

    def safe_invalidate_channel_config(
        self,
        channel_config_id: str,
        *,
        tenant_id: str = "",
        reason: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._safe(
            lambda: self.invalidate_channel_config(
                channel_config_id,
                tenant_id=tenant_id,
                reason=reason,
                metadata=metadata,
            )
        )

    @classmethod
    def scope_key(cls, *, resource_type: str, tenant_id: str = "", agent_id: str = "") -> str:
        normalized_resource_type = cls._normalize_resource_type(resource_type)
        normalized_tenant_id = str(tenant_id or "").strip()
        normalized_agent_id = str(agent_id or "").strip()
        if normalized_resource_type == cls.PLATFORM_SCOPE:
            return cls.PLATFORM_SCOPE
        if normalized_resource_type == cls.TENANT_SCOPE:
            return build_namespace(cls.TENANT_SCOPE, normalized_tenant_id)
        if normalized_resource_type == cls.AGENT_SCOPE:
            return build_namespace(cls.AGENT_SCOPE, normalized_tenant_id, normalized_agent_id)
        if normalized_resource_type == cls.CHANNEL_CONFIG_SCOPE:
            return build_namespace(cls.CHANNEL_CONFIG_SCOPE, normalized_agent_id)
        return build_namespace(normalized_resource_type, normalized_tenant_id, normalized_agent_id)

    @staticmethod
    def _normalize_resource_type(resource_type: str) -> str:
        resolved = str(resource_type or "").strip().lower()
        if not resolved:
            raise ValueError("resource_type must not be empty")
        return resolved

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _from_row(row: dict[str, Any]) -> RuntimeState:
        return RuntimeState(
            scope_key=str(row.get("scope_key", "") or ""),
            resource_type=str(row.get("resource_type", "") or ""),
            tenant_id=str(row.get("tenant_id", "") or ""),
            agent_id=str(row.get("agent_id", "") or ""),
            config_version=int(row.get("config_version") or 0),
            desired_state=dict(row.get("desired_state") or {}),
            metadata=dict(row.get("metadata") or {}),
            invalidated_at=str(row.get("invalidated_at", "") or ""),
            updated_at=str(row.get("updated_at", "") or ""),
        )

    @staticmethod
    def _safe(operation) -> None:
        try:
            operation()
        except Exception as exc:
            logger.warning(f"[RuntimeState] Invalidation skipped: {exc}")

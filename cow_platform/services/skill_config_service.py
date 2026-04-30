from __future__ import annotations

import time
from typing import Any

from cow_platform.db import connect, jsonb
from cow_platform.services.runtime_state_service import RuntimeStateService


class SkillConfigService:
    """Tenant-agent scoped skill configuration backed by PostgreSQL."""

    def __init__(self, runtime_state_service: RuntimeStateService | None = None):
        self.runtime_state_service = runtime_state_service or RuntimeStateService()

    def list_skill_configs(self, *, tenant_id: str, agent_id: str) -> dict[str, dict[str, Any]]:
        resolved_tenant_id = self._required("tenant_id", tenant_id)
        resolved_agent_id = self._required("agent_id", agent_id)
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT skill_name, config
                FROM platform_skill_configs
                WHERE tenant_id = %s AND agent_id = %s
                ORDER BY skill_name
                """,
                (resolved_tenant_id, resolved_agent_id),
            ).fetchall()
        return {row["skill_name"]: dict(row.get("config") or {}) for row in rows}

    def save_skill_configs(
        self,
        *,
        tenant_id: str,
        agent_id: str,
        configs: dict[str, dict[str, Any]],
        invalidate: bool = False,
    ) -> dict[str, dict[str, Any]]:
        resolved_tenant_id = self._required("tenant_id", tenant_id)
        resolved_agent_id = self._required("agent_id", agent_id)
        normalized = {
            self._required("skill_name", name): dict(config or {})
            for name, config in (configs or {}).items()
        }
        now = int(time.time())
        names = sorted(normalized)
        with connect() as conn:
            for name in names:
                conn.execute(
                    """
                    INSERT INTO platform_skill_configs (
                        tenant_id, agent_id, skill_name, config, created_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (tenant_id, agent_id, skill_name)
                    DO UPDATE SET config = EXCLUDED.config, updated_at = EXCLUDED.updated_at
                    """,
                    (
                        resolved_tenant_id,
                        resolved_agent_id,
                        name,
                        jsonb(normalized[name]),
                        now,
                        now,
                    ),
                )
            if names:
                conn.execute(
                    """
                    DELETE FROM platform_skill_configs
                    WHERE tenant_id = %s
                      AND agent_id = %s
                      AND NOT (skill_name = ANY(%s))
                    """,
                    (resolved_tenant_id, resolved_agent_id, names),
                )
            else:
                conn.execute(
                    """
                    DELETE FROM platform_skill_configs
                    WHERE tenant_id = %s AND agent_id = %s
                    """,
                    (resolved_tenant_id, resolved_agent_id),
                )
            conn.commit()
        if invalidate:
            self.runtime_state_service.safe_invalidate_agent(
                resolved_tenant_id,
                resolved_agent_id,
                reason="skills_config_updated",
                metadata={"skill_names": names},
            )
        return normalized

    @staticmethod
    def _required(name: str, value: str | None) -> str:
        resolved = str(value or "").strip()
        if not resolved:
            raise ValueError(f"{name} must not be empty")
        return resolved

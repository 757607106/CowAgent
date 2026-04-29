from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from bridge.context import Context
from common.log import logger
from cow_platform.db import connect, jsonb
from cow_platform.services.agent_service import DEFAULT_TENANT_ID


_TASK_COLUMNS = {
    "id",
    "tenant_id",
    "agent_id",
    "binding_id",
    "channel_config_id",
    "session_id",
    "name",
    "enabled",
    "schedule",
    "action",
    "next_run_at",
    "last_run_at",
    "last_error",
    "last_error_at",
    "created_at",
    "updated_at",
    "metadata",
}


class PlatformSchedulerTaskStore:
    """DB-backed scheduler task store with tenant/agent scope.

    The global scheduler service uses an unscoped instance to find due tasks,
    while UI and tool operations use `for_context()` / `for_scope()` to avoid
    cross-tenant reads and writes.
    """

    def __init__(
        self,
        *,
        tenant_id: str = "",
        agent_id: str = "",
        binding_id: str = "",
        channel_config_id: str = "",
        session_id: str = "",
    ):
        self.tenant_id = (tenant_id or "").strip()
        self.agent_id = (agent_id or "").strip()
        self.binding_id = (binding_id or "").strip()
        self.channel_config_id = (channel_config_id or "").strip()
        self.session_id = (session_id or "").strip()

    def for_scope(
        self,
        *,
        tenant_id: str = "",
        agent_id: str = "",
        binding_id: str = "",
        channel_config_id: str = "",
        session_id: str = "",
    ) -> "PlatformSchedulerTaskStore":
        return PlatformSchedulerTaskStore(
            tenant_id=tenant_id or self.tenant_id,
            agent_id=agent_id or self.agent_id,
            binding_id=binding_id or self.binding_id,
            channel_config_id=channel_config_id or self.channel_config_id,
            session_id=session_id or self.session_id,
        )

    def for_context(self, context: Context | None) -> "PlatformSchedulerTaskStore":
        if context is None:
            return self
        return self.for_scope(
            tenant_id=context.get("tenant_id") or context.get("source_tenant_id") or DEFAULT_TENANT_ID,
            agent_id=context.get("agent_id") or "default",
            binding_id=context.get("binding_id") or "",
            channel_config_id=context.get("channel_config_id") or "",
            session_id=context.get("session_id") or "",
        )

    def add_task(self, task: dict) -> bool:
        task_id = str(task.get("id") or "").strip()
        if not task_id:
            raise ValueError("Task must have an 'id' field")

        tenant_id = self._task_value(task, "tenant_id", DEFAULT_TENANT_ID)
        agent_id = self._task_value(task, "agent_id", "default")
        now = datetime.now().isoformat()
        metadata = self._metadata_for_storage(task)

        with connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO platform_scheduled_tasks (
                    tenant_id, agent_id, task_id, binding_id, channel_config_id,
                    session_id, name, enabled, schedule, action, next_run_at,
                    last_run_at, last_error, last_error_at, metadata, created_at, updated_at
                )
                VALUES (
                    %(tenant_id)s, %(agent_id)s, %(task_id)s, %(binding_id)s, %(channel_config_id)s,
                    %(session_id)s, %(name)s, %(enabled)s, %(schedule)s, %(action)s, %(next_run_at)s,
                    %(last_run_at)s, %(last_error)s, %(last_error_at)s, %(metadata)s, %(created_at)s, %(updated_at)s
                )
                ON CONFLICT (tenant_id, agent_id, task_id) DO NOTHING
                """,
                {
                    "tenant_id": tenant_id,
                    "agent_id": agent_id,
                    "task_id": task_id,
                    "binding_id": self._task_value(task, "binding_id", ""),
                    "channel_config_id": self._task_value(task, "channel_config_id", ""),
                    "session_id": self._task_value(task, "session_id", ""),
                    "name": str(task.get("name") or ""),
                    "enabled": bool(task.get("enabled", True)),
                    "schedule": jsonb(task.get("schedule") or {}),
                    "action": jsonb(task.get("action") or {}),
                    "next_run_at": str(task.get("next_run_at") or ""),
                    "last_run_at": str(task.get("last_run_at") or ""),
                    "last_error": str(task.get("last_error") or ""),
                    "last_error_at": str(task.get("last_error_at") or ""),
                    "metadata": jsonb(metadata),
                    "created_at": str(task.get("created_at") or now),
                    "updated_at": str(task.get("updated_at") or now),
                },
            )
            if cursor.rowcount == 0:
                raise ValueError(f"Task with id '{task_id}' already exists")
        return True

    def update_task(self, task_id: str, updates: dict, task: dict | None = None) -> bool:
        tenant_id, agent_id = self._scope_for_existing(task)
        if not tenant_id or not agent_id:
            raise ValueError("tenant_id and agent_id are required to update scheduler task")

        allowed = {
            "name",
            "enabled",
            "schedule",
            "action",
            "next_run_at",
            "last_run_at",
            "last_error",
            "last_error_at",
            "binding_id",
            "channel_config_id",
            "session_id",
            "metadata",
        }
        values: dict[str, Any] = {
            "tenant_id": tenant_id,
            "agent_id": agent_id,
            "task_id": task_id,
            "updated_at": datetime.now().isoformat(),
        }
        assignments = ["updated_at = %(updated_at)s"]
        for key, value in (updates or {}).items():
            if key not in allowed:
                continue
            assignments.append(f"{key} = %({key})s")
            values[key] = jsonb(value) if key in {"schedule", "action", "metadata"} else value

        if len(assignments) == 1:
            return True

        with connect() as conn:
            cursor = conn.execute(
                f"""
                UPDATE platform_scheduled_tasks
                SET {", ".join(assignments)}
                WHERE tenant_id = %(tenant_id)s
                  AND agent_id = %(agent_id)s
                  AND task_id = %(task_id)s
                """,
                values,
            )
            if cursor.rowcount == 0:
                raise ValueError(f"Task '{task_id}' not found")
        return True

    def delete_task(self, task_id: str, task: dict | None = None) -> bool:
        tenant_id, agent_id = self._scope_for_existing(task)
        if not tenant_id or not agent_id:
            raise ValueError("tenant_id and agent_id are required to delete scheduler task")
        with connect() as conn:
            cursor = conn.execute(
                """
                DELETE FROM platform_scheduled_tasks
                WHERE tenant_id = %s AND agent_id = %s AND task_id = %s
                """,
                (tenant_id, agent_id, task_id),
            )
            if cursor.rowcount == 0:
                raise ValueError(f"Task '{task_id}' not found")
        return True

    def get_task(self, task_id: str, task: dict | None = None) -> Optional[dict]:
        tenant_id, agent_id = self._scope_for_existing(task, required=False)
        where = ["task_id = %s"]
        params: list[Any] = [task_id]
        if tenant_id:
            where.append("tenant_id = %s")
            params.append(tenant_id)
        if agent_id:
            where.append("agent_id = %s")
            params.append(agent_id)
        with connect() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM platform_scheduled_tasks
                WHERE {" AND ".join(where)}
                ORDER BY tenant_id, agent_id
                LIMIT 2
                """,
                params,
            ).fetchall()
        if not rows:
            return None
        if len(rows) > 1:
            logger.warning("[Scheduler] task_id lookup is ambiguous without tenant scope: %s", task_id)
            return None
        return self._row_to_task(rows[0])

    def list_tasks(self, enabled_only: bool = False) -> list[dict]:
        where = []
        params: list[Any] = []
        if self.tenant_id:
            where.append("tenant_id = %s")
            params.append(self.tenant_id)
        if self.agent_id:
            where.append("agent_id = %s")
            params.append(self.agent_id)
        if enabled_only:
            where.append("enabled = true")
        sql = "SELECT * FROM platform_scheduled_tasks"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY COALESCE(NULLIF(next_run_at, ''), '9999-12-31T23:59:59'), created_at"
        with connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_task(row) for row in rows]

    def enable_task(self, task_id: str, enabled: bool = True) -> bool:
        return self.update_task(task_id, {"enabled": enabled})

    def _task_value(self, task: dict, key: str, default: str) -> str:
        value = task.get(key)
        if value is None or value == "":
            value = getattr(self, key, "")
        if value is None or value == "":
            value = default
        return str(value)

    def _scope_for_existing(
        self, task: dict | None = None, *, required: bool = True
    ) -> tuple[str, str]:
        tenant_id = ""
        agent_id = ""
        if task:
            tenant_id = str(task.get("tenant_id") or "")
            agent_id = str(task.get("agent_id") or "")
        tenant_id = tenant_id or self.tenant_id
        agent_id = agent_id or self.agent_id
        if required:
            return tenant_id or DEFAULT_TENANT_ID, agent_id or "default"
        return tenant_id, agent_id

    def _metadata_for_storage(self, task: dict) -> dict[str, Any]:
        metadata = dict(task.get("metadata") or {})
        extra = {key: value for key, value in task.items() if key not in _TASK_COLUMNS}
        if extra:
            metadata["extra"] = extra
        return metadata

    def _row_to_task(self, row: dict) -> dict:
        metadata = dict(row.get("metadata") or {})
        task = dict(metadata.pop("extra", {}) or {})
        task.update(
            {
                "id": row["task_id"],
                "tenant_id": row["tenant_id"],
                "agent_id": row["agent_id"],
                "binding_id": row.get("binding_id", ""),
                "channel_config_id": row.get("channel_config_id", ""),
                "session_id": row.get("session_id", ""),
                "name": row.get("name", ""),
                "enabled": bool(row.get("enabled", True)),
                "schedule": dict(row.get("schedule") or {}),
                "action": dict(row.get("action") or {}),
                "created_at": row.get("created_at", ""),
                "updated_at": row.get("updated_at", ""),
                "metadata": metadata,
            }
        )
        for key in ("next_run_at", "last_run_at", "last_error", "last_error_at"):
            value = row.get(key)
            if value:
                task[key] = value
        return task

from __future__ import annotations

import time
from dataclasses import asdict
from typing import Any

from psycopg import errors

from cow_platform.db import connect, jsonb
from cow_platform.domain.models import PlatformUserDefinition


class PostgresPlatformUserRepository:
    """PostgreSQL-backed platform user repository."""

    def list_users(
        self,
        *,
        role: str = "",
        status: str = "",
    ) -> list[PlatformUserDefinition]:
        conditions: list[str] = []
        params: list[Any] = []
        if role:
            conditions.append("role = %s")
            params.append(role)
        if status:
            conditions.append("status = %s")
            params.append(status)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with connect() as conn:
            rows = conn.execute(
                f"""
                SELECT user_id, name, role, status, metadata
                FROM platform_users
                {where}
                ORDER BY user_id
                """,
                tuple(params),
            ).fetchall()
        return [self._to_definition(row) for row in rows]

    def get_user(self, user_id: str) -> PlatformUserDefinition | None:
        with connect() as conn:
            row = conn.execute(
                """
                SELECT user_id, name, role, status, metadata
                FROM platform_users
                WHERE user_id = %s
                """,
                (user_id,),
            ).fetchone()
        return self._to_definition(row) if row else None

    def create_user(
        self,
        *,
        user_id: str,
        name: str = "",
        role: str = "platform_super_admin",
        status: str = "active",
        metadata: dict[str, Any] | None = None,
    ) -> PlatformUserDefinition:
        now = int(time.time())
        try:
            with connect() as conn:
                row = conn.execute(
                    """
                    INSERT INTO platform_users
                        (user_id, name, role, status, metadata, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING user_id, name, role, status, metadata
                    """,
                    (user_id, name, role, status, jsonb(metadata or {}), now, now),
                ).fetchone()
                conn.commit()
        except errors.UniqueViolation as exc:
            raise ValueError(f"platform user already exists: {user_id}") from exc
        return self._to_definition(row)

    def update_user(
        self,
        *,
        user_id: str,
        name: str | None = None,
        role: str | None = None,
        status: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PlatformUserDefinition:
        current = self.export_user_record_by_id(user_id)
        with connect() as conn:
            row = conn.execute(
                """
                UPDATE platform_users
                SET name = %s, role = %s, status = %s, metadata = %s, updated_at = %s
                WHERE user_id = %s
                RETURNING user_id, name, role, status, metadata
                """,
                (
                    current["name"] if name is None else name,
                    current["role"] if role is None else role,
                    current["status"] if status is None else status,
                    jsonb(current["metadata"] if metadata is None else metadata),
                    int(time.time()),
                    user_id,
                ),
            ).fetchone()
            conn.commit()
        if not row:
            raise KeyError(f"platform user not found: {user_id}")
        return self._to_definition(row)

    def export_user_record(self, definition: PlatformUserDefinition) -> dict[str, Any]:
        try:
            return self.export_user_record_by_id(definition.user_id)
        except KeyError:
            record = asdict(definition)
            record["created_at"] = None
            record["updated_at"] = None
            return record

    def export_user_record_by_id(self, user_id: str) -> dict[str, Any]:
        with connect() as conn:
            row = conn.execute(
                """
                SELECT user_id, name, role, status, metadata, created_at, updated_at
                FROM platform_users
                WHERE user_id = %s
                """,
                (user_id,),
            ).fetchone()
        if not row:
            raise KeyError(f"platform user not found: {user_id}")
        return dict(row)

    @staticmethod
    def _to_definition(record: dict[str, Any]) -> PlatformUserDefinition:
        return PlatformUserDefinition(
            user_id=record["user_id"],
            name=record.get("name", ""),
            role=record.get("role", "platform_super_admin"),
            status=record.get("status", "active"),
            metadata=record.get("metadata", {}) or {},
        )


PlatformUserRepository = PostgresPlatformUserRepository

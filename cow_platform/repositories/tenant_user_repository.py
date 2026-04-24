from __future__ import annotations

import time
from dataclasses import asdict
from typing import Any

from psycopg import errors

from cow_platform.db import connect, jsonb
from cow_platform.domain.models import TenantUserDefinition, TenantUserIdentityDefinition


class PostgresTenantUserRepository:
    """PostgreSQL-backed tenant user and identity repository."""

    def list_users(
        self,
        *,
        tenant_id: str = "",
        role: str = "",
        status: str = "",
    ) -> list[TenantUserDefinition]:
        conditions: list[str] = []
        params: list[Any] = []
        if tenant_id:
            conditions.append("tenant_id = %s")
            params.append(tenant_id)
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
                SELECT tenant_id, user_id, name, role, status, metadata
                FROM platform_tenant_users
                {where}
                ORDER BY tenant_id, user_id
                """,
                tuple(params),
            ).fetchall()
        return [self._to_user_definition(row) for row in rows]

    def get_user(self, tenant_id: str, user_id: str) -> TenantUserDefinition | None:
        with connect() as conn:
            row = conn.execute(
                """
                SELECT tenant_id, user_id, name, role, status, metadata
                FROM platform_tenant_users
                WHERE tenant_id = %s AND user_id = %s
                """,
                (tenant_id, user_id),
            ).fetchone()
        return self._to_user_definition(row) if row else None

    def create_user(
        self,
        *,
        tenant_id: str,
        user_id: str,
        name: str = "",
        role: str,
        status: str = "active",
        metadata: dict[str, Any] | None = None,
    ) -> TenantUserDefinition:
        now = int(time.time())
        try:
            with connect() as conn:
                row = conn.execute(
                    """
                    INSERT INTO platform_tenant_users
                        (tenant_id, user_id, name, role, status, metadata, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING tenant_id, user_id, name, role, status, metadata
                    """,
                    (tenant_id, user_id, name, role, status, jsonb(metadata or {}), now, now),
                ).fetchone()
                conn.commit()
        except errors.UniqueViolation as exc:
            raise ValueError(f"tenant user already exists: {tenant_id}/{user_id}") from exc
        return self._to_user_definition(row)

    def update_user(
        self,
        *,
        tenant_id: str,
        user_id: str,
        name: str | None = None,
        role: str | None = None,
        status: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TenantUserDefinition:
        current = self.export_user_record_by_id(tenant_id, user_id)
        with connect() as conn:
            row = conn.execute(
                """
                UPDATE platform_tenant_users
                SET name = %s, role = %s, status = %s, metadata = %s, updated_at = %s
                WHERE tenant_id = %s AND user_id = %s
                RETURNING tenant_id, user_id, name, role, status, metadata
                """,
                (
                    current["name"] if name is None else name,
                    current["role"] if role is None else role,
                    current["status"] if status is None else status,
                    jsonb(current["metadata"] if metadata is None else metadata),
                    int(time.time()),
                    tenant_id,
                    user_id,
                ),
            ).fetchone()
            conn.commit()
        if not row:
            raise KeyError(f"tenant user not found: {tenant_id}/{user_id}")
        return self._to_user_definition(row)

    def delete_user(self, *, tenant_id: str, user_id: str) -> TenantUserDefinition:
        with connect() as conn:
            row = conn.execute(
                """
                DELETE FROM platform_tenant_users
                WHERE tenant_id = %s AND user_id = %s
                RETURNING tenant_id, user_id, name, role, status, metadata
                """,
                (tenant_id, user_id),
            ).fetchone()
            conn.commit()
        if not row:
            raise KeyError(f"tenant user not found: {tenant_id}/{user_id}")
        return self._to_user_definition(row)

    def list_identities(
        self,
        *,
        tenant_id: str = "",
        user_id: str = "",
        channel_type: str = "",
    ) -> list[TenantUserIdentityDefinition]:
        conditions: list[str] = []
        params: list[Any] = []
        if tenant_id:
            conditions.append("tenant_id = %s")
            params.append(tenant_id)
        if user_id:
            conditions.append("user_id = %s")
            params.append(user_id)
        if channel_type:
            conditions.append("channel_type = %s")
            params.append(channel_type)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with connect() as conn:
            rows = conn.execute(
                f"""
                SELECT tenant_id, user_id, channel_type, external_user_id, metadata
                FROM platform_tenant_user_identities
                {where}
                ORDER BY tenant_id, user_id, channel_type, external_user_id
                """,
                tuple(params),
            ).fetchall()
        return [self._to_identity_definition(row) for row in rows]

    def get_identity(
        self,
        *,
        tenant_id: str,
        channel_type: str,
        external_user_id: str,
    ) -> TenantUserIdentityDefinition | None:
        with connect() as conn:
            row = conn.execute(
                """
                SELECT tenant_id, user_id, channel_type, external_user_id, metadata
                FROM platform_tenant_user_identities
                WHERE tenant_id = %s AND channel_type = %s AND external_user_id = %s
                """,
                (tenant_id, channel_type, external_user_id),
            ).fetchone()
        return self._to_identity_definition(row) if row else None

    def upsert_identity(
        self,
        *,
        tenant_id: str,
        user_id: str,
        channel_type: str,
        external_user_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> TenantUserIdentityDefinition:
        now = int(time.time())
        try:
            with connect() as conn:
                existing = conn.execute(
                    """
                    SELECT user_id
                    FROM platform_tenant_user_identities
                    WHERE tenant_id = %s AND channel_type = %s AND external_user_id = %s
                    """,
                    (tenant_id, channel_type, external_user_id),
                ).fetchone()
                if existing and existing["user_id"] != user_id:
                    raise ValueError(
                        "identity already bound to another tenant user: "
                        f"{tenant_id}/{channel_type}/{external_user_id}"
                    )
                row = conn.execute(
                    """
                    INSERT INTO platform_tenant_user_identities
                        (tenant_id, user_id, channel_type, external_user_id, metadata, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (tenant_id, channel_type, external_user_id)
                    DO UPDATE SET
                        user_id = EXCLUDED.user_id,
                        metadata = EXCLUDED.metadata,
                        updated_at = EXCLUDED.updated_at
                    RETURNING tenant_id, user_id, channel_type, external_user_id, metadata
                    """,
                    (tenant_id, user_id, channel_type, external_user_id, jsonb(metadata or {}), now, now),
                ).fetchone()
                conn.commit()
        except errors.ForeignKeyViolation as exc:
            raise KeyError(f"tenant user not found: {tenant_id}/{user_id}") from exc
        return self._to_identity_definition(row)

    def delete_identity(
        self,
        *,
        tenant_id: str,
        channel_type: str,
        external_user_id: str,
    ) -> TenantUserIdentityDefinition:
        with connect() as conn:
            row = conn.execute(
                """
                DELETE FROM platform_tenant_user_identities
                WHERE tenant_id = %s AND channel_type = %s AND external_user_id = %s
                RETURNING tenant_id, user_id, channel_type, external_user_id, metadata
                """,
                (tenant_id, channel_type, external_user_id),
            ).fetchone()
            conn.commit()
        if not row:
            raise KeyError(f"identity not found: {tenant_id}/{channel_type}/{external_user_id}")
        return self._to_identity_definition(row)

    def find_user_by_identity(
        self,
        *,
        tenant_id: str,
        channel_type: str,
        external_user_id: str,
    ) -> TenantUserDefinition | None:
        with connect() as conn:
            row = conn.execute(
                """
                SELECT u.tenant_id, u.user_id, u.name, u.role, u.status, u.metadata
                FROM platform_tenant_user_identities i
                JOIN platform_tenant_users u
                  ON u.tenant_id = i.tenant_id AND u.user_id = i.user_id
                WHERE i.tenant_id = %s AND i.channel_type = %s AND i.external_user_id = %s
                """,
                (tenant_id, channel_type, external_user_id),
            ).fetchone()
        return self._to_user_definition(row) if row else None

    def export_user_record(self, definition: TenantUserDefinition) -> dict[str, Any]:
        try:
            return self.export_user_record_by_id(definition.tenant_id, definition.user_id)
        except KeyError:
            record = asdict(definition)
            record["created_at"] = None
            record["updated_at"] = None
            return record

    def export_user_record_by_id(self, tenant_id: str, user_id: str) -> dict[str, Any]:
        with connect() as conn:
            row = conn.execute(
                """
                SELECT tenant_id, user_id, name, role, status, metadata, created_at, updated_at
                FROM platform_tenant_users
                WHERE tenant_id = %s AND user_id = %s
                """,
                (tenant_id, user_id),
            ).fetchone()
        if not row:
            raise KeyError(f"tenant user not found: {tenant_id}/{user_id}")
        return dict(row)

    def export_identity_record(self, definition: TenantUserIdentityDefinition) -> dict[str, Any]:
        with connect() as conn:
            row = conn.execute(
                """
                SELECT tenant_id, user_id, channel_type, external_user_id, metadata, created_at, updated_at
                FROM platform_tenant_user_identities
                WHERE tenant_id = %s AND channel_type = %s AND external_user_id = %s
                """,
                (definition.tenant_id, definition.channel_type, definition.external_user_id),
            ).fetchone()
        return dict(row) if row else asdict(definition)

    @staticmethod
    def _to_user_definition(record: dict[str, Any]) -> TenantUserDefinition:
        return TenantUserDefinition(
            tenant_id=record["tenant_id"],
            user_id=record["user_id"],
            name=record.get("name", ""),
            role=record.get("role", "member"),
            status=record.get("status", "active"),
            metadata=record.get("metadata", {}) or {},
        )

    @staticmethod
    def _to_identity_definition(record: dict[str, Any]) -> TenantUserIdentityDefinition:
        return TenantUserIdentityDefinition(
            tenant_id=record["tenant_id"],
            user_id=record["user_id"],
            channel_type=record["channel_type"],
            external_user_id=record["external_user_id"],
            metadata=record.get("metadata", {}) or {},
        )


TenantUserRepository = PostgresTenantUserRepository

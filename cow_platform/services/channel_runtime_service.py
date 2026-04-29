from __future__ import annotations

import os
import socket
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from cow_platform.db import connect, jsonb


_PROCESS_OWNER_ID = (
    os.getenv("COW_PLATFORM_INSTANCE_ID", "").strip()
    or f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat()


@dataclass(frozen=True, slots=True)
class ChannelRuntimeLease:
    channel_config_id: str
    tenant_id: str
    channel_type: str
    owner_id: str
    lease_until: str
    acquired: bool


class ChannelRuntimeLeaseService:
    """Distributed lease service for managed tenant channel runtimes."""

    def __init__(self, *, owner_id: str | None = None, ttl_seconds: int = 90):
        self.owner_id = (owner_id or _PROCESS_OWNER_ID).strip()
        self.ttl_seconds = max(15, int(ttl_seconds))

    def acquire(self, definition: Any) -> ChannelRuntimeLease:
        channel_config_id = str(getattr(definition, "channel_config_id", "") or "").strip()
        tenant_id = str(getattr(definition, "tenant_id", "") or "").strip()
        channel_type = str(getattr(definition, "channel_type", "") or "").strip()
        if not channel_config_id or not tenant_id or not channel_type:
            raise ValueError("channel_config_id, tenant_id and channel_type are required")

        now = _utc_now()
        lease_until = now + timedelta(seconds=self.ttl_seconds)
        params = {
            "channel_config_id": channel_config_id,
            "tenant_id": tenant_id,
            "channel_type": channel_type,
            "owner_id": self.owner_id,
            "status": "running",
            "lease_until": _iso(lease_until),
            "heartbeat_at": _iso(now),
            "metadata": jsonb({}),
            "created_at": _iso(now),
            "updated_at": _iso(now),
            "now": _iso(now),
        }
        with connect() as conn:
            row = conn.execute(
                """
                INSERT INTO platform_channel_runtime_leases (
                    channel_config_id, tenant_id, channel_type, owner_id, status,
                    lease_until, heartbeat_at, metadata, created_at, updated_at
                )
                VALUES (
                    %(channel_config_id)s, %(tenant_id)s, %(channel_type)s, %(owner_id)s, %(status)s,
                    %(lease_until)s, %(heartbeat_at)s, %(metadata)s, %(created_at)s, %(updated_at)s
                )
                ON CONFLICT (channel_config_id) DO UPDATE
                SET tenant_id = EXCLUDED.tenant_id,
                    channel_type = EXCLUDED.channel_type,
                    owner_id = EXCLUDED.owner_id,
                    status = EXCLUDED.status,
                    lease_until = EXCLUDED.lease_until,
                    heartbeat_at = EXCLUDED.heartbeat_at,
                    updated_at = EXCLUDED.updated_at
                WHERE platform_channel_runtime_leases.owner_id = EXCLUDED.owner_id
                   OR platform_channel_runtime_leases.status <> 'running'
                   OR platform_channel_runtime_leases.lease_until <= %(now)s
                RETURNING channel_config_id, tenant_id, channel_type, owner_id, lease_until
                """,
                params,
            ).fetchone()
        if row is None:
            return ChannelRuntimeLease(
                channel_config_id=channel_config_id,
                tenant_id=tenant_id,
                channel_type=channel_type,
                owner_id=self.owner_id,
                lease_until=params["lease_until"],
                acquired=False,
            )
        return ChannelRuntimeLease(
            channel_config_id=row["channel_config_id"],
            tenant_id=row["tenant_id"],
            channel_type=row["channel_type"],
            owner_id=row["owner_id"],
            lease_until=row["lease_until"],
            acquired=True,
        )

    def heartbeat(self, channel_config_id: str) -> bool:
        now = _utc_now()
        with connect() as conn:
            cursor = conn.execute(
                """
                UPDATE platform_channel_runtime_leases
                SET lease_until = %s,
                    heartbeat_at = %s,
                    updated_at = %s
                WHERE channel_config_id = %s
                  AND owner_id = %s
                  AND status = 'running'
                """,
                (
                    _iso(now + timedelta(seconds=self.ttl_seconds)),
                    _iso(now),
                    _iso(now),
                    channel_config_id,
                    self.owner_id,
                ),
            )
        return bool(cursor.rowcount)

    def release(self, channel_config_id: str) -> bool:
        with connect() as conn:
            cursor = conn.execute(
                """
                DELETE FROM platform_channel_runtime_leases
                WHERE channel_config_id = %s AND owner_id = %s
                """,
                (channel_config_id, self.owner_id),
            )
        return bool(cursor.rowcount)

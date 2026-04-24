from __future__ import annotations

from datetime import datetime
from typing import Any
import uuid

from cow_platform.domain.models import AuditLogRecord
from cow_platform.repositories.audit_repository import AuditRepository


class AuditService:
    """Audit service backed by PostgreSQL."""

    def __init__(self, repository: AuditRepository | None = None):
        self.repository = repository or AuditRepository()

    def record_event(
        self,
        *,
        action: str,
        resource_type: str,
        resource_id: str,
        status: str = "success",
        tenant_id: str = "",
        agent_id: str = "",
        actor: str = "system",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = AuditLogRecord(
            audit_id=f"audit_{uuid.uuid4().hex}",
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status,
            tenant_id=tenant_id,
            agent_id=agent_id,
            actor=actor,
            created_at=datetime.now().isoformat(timespec="seconds"),
            metadata=metadata or {},
        )
        self.repository.append_record(record)
        return self.serialize_record(record)

    def list_records(
        self,
        *,
        action: str = "",
        resource_type: str = "",
        tenant_id: str = "",
        agent_id: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        return [
            self.serialize_record(item)
            for item in self.repository.list_records(
                action=action,
                resource_type=resource_type,
                tenant_id=tenant_id,
                agent_id=agent_id,
                limit=limit,
            )
        ]

    def serialize_record(self, definition: AuditLogRecord) -> dict[str, Any]:
        return self.repository.export_record(definition)

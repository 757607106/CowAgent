from __future__ import annotations

import json
import threading
from dataclasses import asdict
from pathlib import Path
from typing import Any

from cow_platform.domain.models import AuditLogRecord
from cow_platform.repositories.agent_repository import get_platform_data_root


class FileAuditRepository:
    """基于 JSON 文件的审计日志仓储。"""

    def __init__(self, store_path: Path | None = None):
        self.store_path = store_path or (get_platform_data_root() / "audit_logs.json")
        self._lock = threading.Lock()
        self.store_path.parent.mkdir(parents=True, exist_ok=True)

    def append_record(self, record: AuditLogRecord) -> AuditLogRecord:
        with self._lock:
            store = self._load_store()
            store["records"].append(asdict(record))
            self._save_store(store)
        return record

    def list_records(
        self,
        *,
        action: str = "",
        resource_type: str = "",
        tenant_id: str = "",
        agent_id: str = "",
        limit: int = 100,
    ) -> list[AuditLogRecord]:
        with self._lock:
            store = self._load_store()
        items = []
        for raw in store.get("records", []):
            if action and raw.get("action") != action:
                continue
            if resource_type and raw.get("resource_type") != resource_type:
                continue
            if tenant_id and raw.get("tenant_id", "") != tenant_id:
                continue
            if agent_id and raw.get("agent_id", "") != agent_id:
                continue
            items.append(self._to_definition(raw))
        items.sort(key=lambda item: item.created_at, reverse=True)
        return items[: max(1, int(limit))]

    @staticmethod
    def export_record(definition: AuditLogRecord) -> dict[str, Any]:
        return asdict(definition)

    def _load_store(self) -> dict[str, Any]:
        if not self.store_path.exists():
            return {"records": []}
        with self.store_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if "records" not in data:
            data["records"] = []
        return data

    def _save_store(self, store: dict[str, Any]) -> None:
        with self.store_path.open("w", encoding="utf-8") as file:
            json.dump(store, file, ensure_ascii=False, indent=2)

    @staticmethod
    def _to_definition(record: dict[str, Any]) -> AuditLogRecord:
        return AuditLogRecord(
            audit_id=record["audit_id"],
            action=record["action"],
            resource_type=record["resource_type"],
            resource_id=record["resource_id"],
            status=record["status"],
            tenant_id=record.get("tenant_id", ""),
            agent_id=record.get("agent_id", ""),
            actor=record.get("actor", "system"),
            created_at=record["created_at"],
            metadata=record.get("metadata", {}) or {},
        )

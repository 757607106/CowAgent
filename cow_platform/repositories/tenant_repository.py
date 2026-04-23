from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from cow_platform.domain.models import TenantDefinition
from cow_platform.repositories.agent_repository import get_platform_data_root


class FileTenantRepository:
    """基于 JSON 文件的租户仓储。"""

    def __init__(self, store_path: Path | None = None):
        self.store_path = store_path or (get_platform_data_root() / "tenants.json")
        self._lock = threading.Lock()
        self.store_path.parent.mkdir(parents=True, exist_ok=True)

    def list_tenants(self) -> list[TenantDefinition]:
        with self._lock:
            store = self._load_store()
        tenants = [self._to_definition(record) for record in store.get("tenants", {}).values()]
        tenants.sort(key=lambda item: (item.tenant_id, item.name))
        return tenants

    def get_tenant(self, tenant_id: str) -> TenantDefinition | None:
        with self._lock:
            store = self._load_store()
            record = store.get("tenants", {}).get(tenant_id)
        if not record:
            return None
        return self._to_definition(record)

    def create_tenant(
        self,
        tenant_id: str,
        name: str,
        *,
        status: str = "active",
        metadata: dict[str, Any] | None = None,
    ) -> TenantDefinition:
        now = int(time.time())
        with self._lock:
            store = self._load_store()
            if tenant_id in store["tenants"]:
                raise ValueError(f"tenant already exists: {tenant_id}")

            record = {
                "tenant_id": tenant_id,
                "name": name,
                "status": status,
                "metadata": metadata or {},
                "created_at": now,
                "updated_at": now,
            }
            store["tenants"][tenant_id] = record
            self._save_store(store)
        return self._to_definition(record)

    def update_tenant(
        self,
        tenant_id: str,
        *,
        name: str | None = None,
        status: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TenantDefinition:
        now = int(time.time())
        with self._lock:
            store = self._load_store()
            record = store["tenants"].get(tenant_id)
            if not record:
                raise KeyError(f"tenant not found: {tenant_id}")

            if name is not None:
                record["name"] = name
            if status is not None:
                record["status"] = status
            if metadata is not None:
                record["metadata"] = metadata
            record["updated_at"] = now
            self._save_store(store)
        return self._to_definition(record)

    def export_record(self, definition: TenantDefinition) -> dict[str, Any]:
        """导出给接口层使用的完整租户记录。"""
        record = asdict(definition)
        with self._lock:
            store = self._load_store()
            saved = store.get("tenants", {}).get(definition.tenant_id, {})
        record["created_at"] = saved.get("created_at")
        record["updated_at"] = saved.get("updated_at")
        return record

    def _load_store(self) -> dict[str, Any]:
        if not self.store_path.exists():
            return {"tenants": {}}
        with self.store_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if "tenants" not in data:
            data["tenants"] = {}
        return data

    def _save_store(self, store: dict[str, Any]) -> None:
        with self.store_path.open("w", encoding="utf-8") as file:
            json.dump(store, file, ensure_ascii=False, indent=2)

    @staticmethod
    def _to_definition(record: dict[str, Any]) -> TenantDefinition:
        return TenantDefinition(
            tenant_id=record["tenant_id"],
            name=record["name"],
            status=record.get("status", "active"),
            metadata=record.get("metadata", {}) or {},
        )

from __future__ import annotations

import json
import threading
from dataclasses import asdict
from pathlib import Path
from typing import Any

from cow_platform.domain.models import QuotaDefinition
from cow_platform.repositories.agent_repository import get_platform_data_root


class FileQuotaRepository:
    """基于 JSON 文件的配额仓储。"""

    def __init__(self, store_path: Path | None = None):
        self.store_path = store_path or (get_platform_data_root() / "quotas.json")
        self._lock = threading.Lock()
        self.store_path.parent.mkdir(parents=True, exist_ok=True)

    def list_quotas(self, *, scope_type: str = "", tenant_id: str = "", agent_id: str = "") -> list[QuotaDefinition]:
        with self._lock:
            store = self._load_store()
        items = []
        for record in store.get("items", {}).values():
            if scope_type and record.get("scope_type") != scope_type:
                continue
            if tenant_id and record.get("tenant_id") != tenant_id:
                continue
            if agent_id and record.get("agent_id", "") != agent_id:
                continue
            items.append(self._to_definition(record))
        items.sort(key=lambda item: (item.scope_type, item.tenant_id, item.agent_id))
        return items

    def get_quota(self, *, scope_type: str, tenant_id: str, agent_id: str = "") -> QuotaDefinition | None:
        with self._lock:
            store = self._load_store()
            record = store.get("items", {}).get(self._build_key(scope_type, tenant_id, agent_id))
        if not record:
            return None
        return self._to_definition(record)

    def upsert_quota(
        self,
        *,
        scope_type: str,
        tenant_id: str,
        agent_id: str = "",
        max_requests_per_day: int = 0,
        max_tokens_per_day: int = 0,
        enabled: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> QuotaDefinition:
        key = self._build_key(scope_type, tenant_id, agent_id)
        with self._lock:
            store = self._load_store()
            store["items"][key] = {
                "scope_type": scope_type,
                "tenant_id": tenant_id,
                "agent_id": agent_id,
                "max_requests_per_day": int(max_requests_per_day),
                "max_tokens_per_day": int(max_tokens_per_day),
                "enabled": bool(enabled),
                "metadata": metadata or {},
            }
            self._save_store(store)
            record = store["items"][key]
        return self._to_definition(record)

    def export_record(self, definition: QuotaDefinition) -> dict[str, Any]:
        return asdict(definition)

    @staticmethod
    def _build_key(scope_type: str, tenant_id: str, agent_id: str = "") -> str:
        return f"{scope_type}:{tenant_id}:{agent_id}"

    def _load_store(self) -> dict[str, Any]:
        if not self.store_path.exists():
            return {"items": {}}
        with self.store_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if "items" not in data:
            data["items"] = {}
        return data

    def _save_store(self, store: dict[str, Any]) -> None:
        with self.store_path.open("w", encoding="utf-8") as file:
            json.dump(store, file, ensure_ascii=False, indent=2)

    @staticmethod
    def _to_definition(record: dict[str, Any]) -> QuotaDefinition:
        return QuotaDefinition(
            scope_type=record["scope_type"],
            tenant_id=record["tenant_id"],
            agent_id=record.get("agent_id", ""),
            max_requests_per_day=int(record.get("max_requests_per_day", 0)),
            max_tokens_per_day=int(record.get("max_tokens_per_day", 0)),
            enabled=bool(record.get("enabled", True)),
            metadata=record.get("metadata", {}) or {},
        )

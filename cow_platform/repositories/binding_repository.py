from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from cow_platform.domain.models import ChannelBindingDefinition
from cow_platform.repositories.agent_repository import get_platform_data_root


class FileChannelBindingRepository:
    """基于 JSON 文件的渠道绑定仓储。"""

    def __init__(self, store_path: Path | None = None):
        self.store_path = store_path or (get_platform_data_root() / "bindings.json")
        self._lock = threading.Lock()
        self.store_path.parent.mkdir(parents=True, exist_ok=True)

    def list_bindings(
        self,
        *,
        tenant_id: str = "",
        channel_type: str = "",
    ) -> list[ChannelBindingDefinition]:
        with self._lock:
            store = self._load_store()
        bindings = []
        for record in store.get("bindings", {}).values():
            if tenant_id and record.get("tenant_id") != tenant_id:
                continue
            if channel_type and record.get("channel_type") != channel_type:
                continue
            bindings.append(self._to_definition(record))
        bindings.sort(key=lambda item: (item.tenant_id, item.channel_type, item.binding_id))
        return bindings

    def get_binding(
        self,
        *,
        tenant_id: str = "",
        binding_id: str,
    ) -> ChannelBindingDefinition | None:
        with self._lock:
            store = self._load_store()
            if tenant_id:
                record = store.get("bindings", {}).get(self._build_key(tenant_id, binding_id))
                if record:
                    return self._to_definition(record)

            for saved in store.get("bindings", {}).values():
                if saved.get("binding_id") == binding_id:
                    return self._to_definition(saved)
        return None

    def create_binding(
        self,
        *,
        tenant_id: str,
        binding_id: str,
        name: str,
        channel_type: str,
        agent_id: str,
        enabled: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> ChannelBindingDefinition:
        now = int(time.time())
        with self._lock:
            store = self._load_store()
            self._ensure_binding_id_available(store, binding_id)
            key = self._build_key(tenant_id, binding_id)
            record = {
                "tenant_id": tenant_id,
                "binding_id": binding_id,
                "name": name,
                "channel_type": channel_type,
                "agent_id": agent_id,
                "version": 1,
                "enabled": enabled,
                "metadata": metadata or {},
                "created_at": now,
                "updated_at": now,
            }
            store["bindings"][key] = record
            self._save_store(store)
        return self._to_definition(record)

    def update_binding(
        self,
        *,
        binding_id: str,
        tenant_id: str = "",
        name: str | None = None,
        channel_type: str | None = None,
        agent_id: str | None = None,
        enabled: bool | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ChannelBindingDefinition:
        now = int(time.time())
        with self._lock:
            store = self._load_store()
            key, record = self._find_binding_record(store, binding_id=binding_id, tenant_id=tenant_id)
            if not record:
                raise KeyError(f"binding not found: {binding_id}")

            record["version"] = int(record.get("version", 0)) + 1
            if name is not None:
                record["name"] = name
            if channel_type is not None:
                record["channel_type"] = channel_type
            if agent_id is not None:
                record["agent_id"] = agent_id
            if enabled is not None:
                record["enabled"] = enabled
            if metadata is not None:
                record["metadata"] = metadata
            record["updated_at"] = now
            store["bindings"][key] = record
            self._save_store(store)
        return self._to_definition(record)

    def export_record(self, definition: ChannelBindingDefinition) -> dict[str, Any]:
        """导出给接口层使用的完整绑定记录。"""
        record = asdict(definition)
        with self._lock:
            store = self._load_store()
            saved = store.get("bindings", {}).get(self._build_key(definition.tenant_id, definition.binding_id), {})
        record["created_at"] = saved.get("created_at")
        record["updated_at"] = saved.get("updated_at")
        return record

    def delete_binding(
        self,
        *,
        binding_id: str,
        tenant_id: str = "",
    ) -> ChannelBindingDefinition:
        with self._lock:
            store = self._load_store()
            key, record = self._find_binding_record(store, binding_id=binding_id, tenant_id=tenant_id)
            if not record:
                raise KeyError(f"binding not found: {binding_id}")
            del store["bindings"][key]
            self._save_store(store)
        return self._to_definition(record)

    @staticmethod
    def _build_key(tenant_id: str, binding_id: str) -> str:
        return f"{tenant_id}:{binding_id}"

    def _ensure_binding_id_available(self, store: dict[str, Any], binding_id: str) -> None:
        for record in store.get("bindings", {}).values():
            if record.get("binding_id") == binding_id:
                raise ValueError(f"binding already exists: {binding_id}")

    def _find_binding_record(
        self,
        store: dict[str, Any],
        *,
        binding_id: str,
        tenant_id: str = "",
    ) -> tuple[str, dict[str, Any] | None]:
        if tenant_id:
            key = self._build_key(tenant_id, binding_id)
            return key, store.get("bindings", {}).get(key)

        for key, record in store.get("bindings", {}).items():
            if record.get("binding_id") == binding_id:
                return key, record
        return "", None

    def _load_store(self) -> dict[str, Any]:
        if not self.store_path.exists():
            return {"bindings": {}}
        with self.store_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if "bindings" not in data:
            data["bindings"] = {}
        return data

    def _save_store(self, store: dict[str, Any]) -> None:
        with self.store_path.open("w", encoding="utf-8") as file:
            json.dump(store, file, ensure_ascii=False, indent=2)

    @staticmethod
    def _to_definition(record: dict[str, Any]) -> ChannelBindingDefinition:
        return ChannelBindingDefinition(
            tenant_id=record["tenant_id"],
            binding_id=record["binding_id"],
            name=record["name"],
            channel_type=record["channel_type"],
            agent_id=record["agent_id"],
            version=int(record.get("version", 1)),
            enabled=bool(record.get("enabled", True)),
            metadata=record.get("metadata", {}) or {},
        )

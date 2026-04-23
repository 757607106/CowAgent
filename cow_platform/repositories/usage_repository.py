from __future__ import annotations

import json
import threading
from dataclasses import asdict
from pathlib import Path
from typing import Any

from cow_platform.domain.models import UsageRecord
from cow_platform.repositories.agent_repository import get_platform_data_root


class FileUsageRepository:
    """基于 JSON 文件的 usage 台账仓储。"""

    def __init__(self, store_path: Path | None = None):
        self.store_path = store_path or (get_platform_data_root() / "usage_ledger.json")
        self._lock = threading.Lock()
        self.store_path.parent.mkdir(parents=True, exist_ok=True)

    def append_record(self, record: UsageRecord) -> UsageRecord:
        with self._lock:
            store = self._load_store()
            store["records"].append(asdict(record))
            self._save_store(store)
        return record

    def list_records(
        self,
        *,
        tenant_id: str = "",
        agent_id: str = "",
        day: str = "",
        request_id: str = "",
        limit: int = 100,
    ) -> list[UsageRecord]:
        with self._lock:
            store = self._load_store()
        records = []
        for raw in store.get("records", []):
            if tenant_id and raw.get("tenant_id") != tenant_id:
                continue
            if agent_id and raw.get("agent_id") != agent_id:
                continue
            if day and not str(raw.get("created_at", "")).startswith(day):
                continue
            if request_id and raw.get("request_id") != request_id:
                continue
            records.append(self._to_definition(raw))
        records.sort(key=lambda item: item.created_at, reverse=True)
        return records[: max(1, int(limit))]

    def summarize(
        self,
        *,
        tenant_id: str = "",
        agent_id: str = "",
        day: str = "",
    ) -> dict[str, Any]:
        records = self.list_records(tenant_id=tenant_id, agent_id=agent_id, day=day, limit=1_000_000)
        summary = {
            "request_count": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "provider_request_count": 0,
            "estimated_request_count": 0,
            "tool_call_count": 0,
            "mcp_call_count": 0,
            "tool_error_count": 0,
            "tool_execution_time_ms": 0,
            "estimated_cost": 0.0,
        }
        for item in records:
            summary["request_count"] += int(item.request_count)
            summary["prompt_tokens"] += int(item.prompt_tokens)
            summary["completion_tokens"] += int(item.completion_tokens)
            summary["total_tokens"] += int(item.total_tokens)
            if item.token_source == "provider":
                summary["provider_request_count"] += int(item.request_count)
            else:
                summary["estimated_request_count"] += int(item.request_count)
            summary["tool_call_count"] += int(item.tool_call_count)
            summary["mcp_call_count"] += int(item.mcp_call_count)
            summary["tool_error_count"] += int(item.tool_error_count)
            summary["tool_execution_time_ms"] += int(item.tool_execution_time_ms)
            summary["estimated_cost"] += float(item.estimated_cost)
        summary["estimated_cost"] = round(summary["estimated_cost"], 6)
        return summary

    @staticmethod
    def export_record(definition: UsageRecord) -> dict[str, Any]:
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
    def _to_definition(record: dict[str, Any]) -> UsageRecord:
        return UsageRecord(
            event_id=record["event_id"],
            request_id=record["request_id"],
            tenant_id=record["tenant_id"],
            agent_id=record["agent_id"],
            binding_id=record.get("binding_id", ""),
            session_id=record.get("session_id", ""),
            channel_type=record.get("channel_type", ""),
            model=record.get("model", ""),
            prompt_tokens=int(record.get("prompt_tokens", 0)),
            completion_tokens=int(record.get("completion_tokens", 0)),
            total_tokens=int(record.get("total_tokens", 0)),
            token_source=record.get("token_source", "estimated"),
            request_count=int(record.get("request_count", 1)),
            tool_call_count=int(record.get("tool_call_count", 0)),
            mcp_call_count=int(record.get("mcp_call_count", 0)),
            tool_error_count=int(record.get("tool_error_count", 0)),
            tool_execution_time_ms=int(record.get("tool_execution_time_ms", 0)),
            estimated_cost=float(record.get("estimated_cost", 0.0)),
            created_at=record["created_at"],
            metadata=record.get("metadata", {}) or {},
        )

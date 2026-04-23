from __future__ import annotations

import json
import threading
from dataclasses import asdict
from pathlib import Path
from typing import Any

from cow_platform.domain.models import PricingDefinition
from cow_platform.repositories.agent_repository import get_platform_data_root


class FilePricingRepository:
    """基于 JSON 文件的定价仓储。"""

    def __init__(self, store_path: Path | None = None):
        self.store_path = store_path or (get_platform_data_root() / "pricing.json")
        self._lock = threading.Lock()
        self.store_path.parent.mkdir(parents=True, exist_ok=True)

    def list_pricing(self) -> list[PricingDefinition]:
        with self._lock:
            store = self._load_store()
        items = [self._to_definition(record) for record in store.get("items", {}).values()]
        items.sort(key=lambda item: item.model)
        return items

    def get_pricing(self, model: str) -> PricingDefinition | None:
        with self._lock:
            store = self._load_store()
            record = store.get("items", {}).get(model)
        if not record:
            return None
        return self._to_definition(record)

    def upsert_pricing(
        self,
        *,
        model: str,
        input_price_per_million: float,
        output_price_per_million: float,
        currency: str = "CNY",
        metadata: dict[str, Any] | None = None,
    ) -> PricingDefinition:
        with self._lock:
            store = self._load_store()
            store["items"][model] = {
                "model": model,
                "input_price_per_million": float(input_price_per_million),
                "output_price_per_million": float(output_price_per_million),
                "currency": currency,
                "metadata": metadata or {},
            }
            self._save_store(store)
            record = store["items"][model]
        return self._to_definition(record)

    def export_record(self, definition: PricingDefinition) -> dict[str, Any]:
        return asdict(definition)

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
    def _to_definition(record: dict[str, Any]) -> PricingDefinition:
        return PricingDefinition(
            model=record["model"],
            input_price_per_million=float(record.get("input_price_per_million", 0.0)),
            output_price_per_million=float(record.get("output_price_per_million", 0.0)),
            currency=record.get("currency", "CNY"),
            metadata=record.get("metadata", {}) or {},
        )

from __future__ import annotations

import time
from dataclasses import asdict
from typing import Any

from cow_platform.domain.models import ModelConfigDefinition, TenantDefinition
from cow_platform.services.model_config_service import ModelConfigService


class FakeModelConfigRepository:
    def __init__(self) -> None:
        self.records: dict[str, ModelConfigDefinition] = {}
        self.timestamps: dict[str, tuple[int, int]] = {}

    def list_model_configs(
        self,
        *,
        scope: str = "",
        tenant_id: str = "",
        enabled: bool | None = None,
    ) -> list[ModelConfigDefinition]:
        items = list(self.records.values())
        if scope:
            items = [item for item in items if item.scope == scope]
        if tenant_id:
            items = [item for item in items if item.tenant_id == tenant_id]
        if enabled is not None:
            items = [item for item in items if item.enabled is bool(enabled)]
        return items

    def get_model_config(self, model_config_id: str) -> ModelConfigDefinition | None:
        return self.records.get(model_config_id)

    def create_model_config(self, **kwargs: Any) -> ModelConfigDefinition:
        definition = ModelConfigDefinition(**kwargs)
        if definition.model_config_id in self.records:
            raise ValueError(f"model config already exists: {definition.model_config_id}")
        self.records[definition.model_config_id] = definition
        now = int(time.time())
        self.timestamps[definition.model_config_id] = (now, now)
        return definition

    def update_model_config(self, model_config_id: str, **kwargs: Any) -> ModelConfigDefinition:
        current = self.records[model_config_id]
        data = asdict(current)
        data.update({key: value for key, value in kwargs.items() if value is not None})
        definition = ModelConfigDefinition(**data)
        self.records[model_config_id] = definition
        return definition

    def delete_model_config(self, model_config_id: str) -> ModelConfigDefinition:
        return self.records.pop(model_config_id)

    def export_record(self, definition: ModelConfigDefinition) -> dict[str, Any]:
        record = asdict(definition)
        created_at, updated_at = self.timestamps.get(definition.model_config_id, (None, None))
        record["created_at"] = created_at
        record["updated_at"] = updated_at
        return record


class FakeTenantService:
    def resolve_tenant(self, tenant_id: str) -> TenantDefinition:
        return TenantDefinition(tenant_id=tenant_id, name=tenant_id)


class FakeRuntimeStateService:
    def safe_invalidate_platform(self, **kwargs: Any) -> None:
        return None

    def safe_invalidate_tenant(self, tenant_id: str, **kwargs: Any) -> None:
        return None


def make_service() -> ModelConfigService:
    return ModelConfigService(
        repository=FakeModelConfigRepository(),
        tenant_service=FakeTenantService(),
        runtime_state_service=FakeRuntimeStateService(),
    )


def test_tenant_provider_options_include_vendor_dropdown_choices() -> None:
    service = make_service()
    providers = {item["provider"] for item in service.list_provider_options(scope="tenant")}

    assert {"custom", "openai", "deepseek", "dashscope"}.issubset(providers)


def test_tenant_can_create_vendor_model_without_custom_base_url() -> None:
    service = make_service()

    model = service.create_tenant_model(
        tenant_id="tenant-a",
        provider="deepseek",
        model_name="deepseek-reasoner",
        api_key="sk-tenant-secret",
    )

    assert model["provider"] == "deepseek"
    assert model["api_base"] == ""
    assert model["api_key_set"] is True

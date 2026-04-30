from __future__ import annotations

import time
from dataclasses import asdict
from typing import Any

import pytest

from cow_platform.domain.models import CapabilityConfigDefinition, TenantDefinition
from cow_platform.services.capability_config_service import CapabilityConfigService


class FakeCapabilityConfigRepository:
    def __init__(self) -> None:
        self.records: dict[str, CapabilityConfigDefinition] = {}
        self.timestamps: dict[str, tuple[int, int]] = {}

    def list_capability_configs(
        self,
        *,
        scope: str = "",
        tenant_id: str = "",
        capability: str = "",
        enabled: bool | None = None,
        public_only: bool = False,
    ) -> list[CapabilityConfigDefinition]:
        items = list(self.records.values())
        if scope:
            items = [item for item in items if item.scope == scope]
        if tenant_id:
            items = [item for item in items if item.tenant_id == tenant_id]
        if capability:
            items = [item for item in items if item.capability == capability]
        if enabled is not None:
            items = [item for item in items if item.enabled is bool(enabled)]
        if public_only:
            items = [item for item in items if item.is_public]
        return sorted(
            items,
            key=lambda item: (item.scope, item.tenant_id, item.capability, not item.is_default, item.provider),
        )

    def get_capability_config(self, capability_config_id: str) -> CapabilityConfigDefinition | None:
        return self.records.get(capability_config_id)

    def create_capability_config(self, **kwargs: Any) -> CapabilityConfigDefinition:
        definition = CapabilityConfigDefinition(**kwargs)
        if definition.capability_config_id in self.records:
            raise ValueError(f"capability config already exists: {definition.capability_config_id}")
        self.records[definition.capability_config_id] = definition
        now = int(time.time())
        self.timestamps[definition.capability_config_id] = (now, now)
        return definition

    def update_capability_config(self, capability_config_id: str, **kwargs: Any) -> CapabilityConfigDefinition:
        current = self.records.get(capability_config_id)
        if current is None:
            raise KeyError(f"capability config not found: {capability_config_id}")
        data = asdict(current)
        data.update({key: value for key, value in kwargs.items() if value is not None})
        definition = CapabilityConfigDefinition(**data)
        self.records[capability_config_id] = definition
        return definition

    def unset_default_for_scope(self, *, scope: str, tenant_id: str, capability: str, except_id: str = "") -> None:
        for key, item in list(self.records.items()):
            if item.scope != scope or item.capability != capability:
                continue
            if scope == "tenant" and item.tenant_id != tenant_id:
                continue
            if except_id and key == except_id:
                continue
            data = asdict(item)
            data["is_default"] = False
            self.records[key] = CapabilityConfigDefinition(**data)

    def delete_capability_config(self, capability_config_id: str) -> CapabilityConfigDefinition:
        current = self.records.pop(capability_config_id, None)
        if current is None:
            raise KeyError(f"capability config not found: {capability_config_id}")
        return current

    def export_record(self, definition: CapabilityConfigDefinition) -> dict[str, Any]:
        record = asdict(definition)
        created_at, updated_at = self.timestamps.get(definition.capability_config_id, (None, None))
        record["created_at"] = created_at
        record["updated_at"] = updated_at
        return record

    def export_record_by_id(self, capability_config_id: str) -> dict[str, Any]:
        definition = self.records.get(capability_config_id)
        if definition is None:
            raise KeyError(f"capability config not found: {capability_config_id}")
        return self.export_record(definition)


class FakeTenantService:
    def __init__(self) -> None:
        self.tenants = {
            "tenant-a": TenantDefinition(tenant_id="tenant-a", name="Tenant A"),
            "tenant-b": TenantDefinition(tenant_id="tenant-b", name="Tenant B"),
        }

    def resolve_tenant(self, tenant_id: str) -> TenantDefinition:
        tenant = self.tenants.get(tenant_id)
        if tenant is None:
            raise KeyError(tenant_id)
        return tenant


class FakeRuntimeStateService:
    def safe_invalidate_platform(self, **kwargs: Any) -> None:
        return None

    def safe_invalidate_tenant(self, tenant_id: str, **kwargs: Any) -> None:
        return None


def make_service() -> CapabilityConfigService:
    return CapabilityConfigService(
        repository=FakeCapabilityConfigRepository(),
        tenant_service=FakeTenantService(),
        runtime_state_service=FakeRuntimeStateService(),
    )


def test_tenant_capability_overrides_platform_default_and_stays_isolated() -> None:
    service = make_service()
    platform = service.create_platform_config(
        capability="image_generation",
        provider="openai",
        model_name="dall-e-3",
        api_key="sk-platform-secret",
        is_default=True,
    )
    tenant = service.create_tenant_config(
        tenant_id="tenant-a",
        capability="image_generation",
        provider="custom",
        model_name="tenant-image-model",
        api_base="https://tenant.example.test/v1",
        api_key="sk-tenant-secret",
        is_default=True,
    )

    assert service.resolve_for_runtime("tenant-a", "image_generation").model_name == "tenant-image-model"
    assert service.resolve_for_runtime("tenant-b", "image_generation").model_name == "dall-e-3"
    available_a = service.list_available_configs("tenant-a")
    available_b = service.list_available_configs("tenant-b")
    assert {item.capability_config_id for item in available_a} == {
        platform["capability_config_id"],
        tenant["capability_config_id"],
    }
    assert {item.capability_config_id for item in available_b} == {platform["capability_config_id"]}

    serialized = service.serialize_config(service.resolve_for_runtime("tenant-a", "image_generation"))
    assert "api_key" not in serialized
    assert serialized["api_key_set"] is True
    assert serialized["api_key_masked"].startswith("sk-t")


def test_tenant_cannot_resolve_another_tenant_capability_config() -> None:
    service = make_service()
    config = service.create_tenant_config(
        tenant_id="tenant-a",
        capability="speech_to_text",
        provider="custom",
        model_name="whisper-1",
        api_base="https://asr.example.test/v1",
        api_key="sk-tenant-secret",
    )

    with pytest.raises(PermissionError):
        service.resolve_config_for_scope(
            config["capability_config_id"],
            expected_scope="tenant",
            tenant_id="tenant-b",
        )


def test_runtime_overrides_are_capability_specific() -> None:
    service = make_service()
    asr = service.create_tenant_config(
        tenant_id="tenant-a",
        capability="speech_to_text",
        provider="custom",
        model_name="whisper-large",
        api_base="https://asr.example.test/v1",
        api_key="sk-asr-secret",
    )
    tts = service.create_tenant_config(
        tenant_id="tenant-a",
        capability="text_to_speech",
        provider="minimax",
        model_name="speech-2.8-hd",
        api_key="sk-tts-secret",
        metadata={"voice": "Chinese_Warm_Woman"},
    )
    multimodal = service.create_tenant_config(
        tenant_id="tenant-a",
        capability="multimodal",
        provider="dashscope",
        model_name="qwen3.6-plus",
        api_key="sk-mm-secret",
    )

    asr_overrides = service.build_runtime_overrides(service.resolve_config_for_scope(asr["capability_config_id"]))
    assert asr_overrides["voice_to_text"] == "openai"
    assert asr_overrides["speech_to_text_model"] == "whisper-large"
    assert asr_overrides["open_ai_api_base"] == "https://asr.example.test/v1"

    tts_overrides = service.build_runtime_overrides(service.resolve_config_for_scope(tts["capability_config_id"]))
    assert tts_overrides["text_to_voice"] == "minimax"
    assert tts_overrides["text_to_voice_model"] == "speech-2.8-hd"
    assert tts_overrides["tts_voice_id"] == "Chinese_Warm_Woman"

    mm_overrides = service.build_runtime_overrides(service.resolve_config_for_scope(multimodal["capability_config_id"]))
    assert mm_overrides["dashscope_api_key"] == "sk-mm-secret"
    assert mm_overrides["tools"]["vision"]["model"] == "qwen3.6-plus"


def test_image_generation_runtime_overrides_include_bot_type() -> None:
    service = make_service()
    image = service.create_tenant_config(
        tenant_id="tenant-a",
        capability="image_generation",
        provider="zhipu",
        model_name="cogview-3",
        api_key="sk-image-secret",
        metadata={"image_size": "1024x1024"},
    )

    overrides = service.build_runtime_overrides(service.resolve_config_for_scope(image["capability_config_id"]))

    assert overrides["bot_type"] == "zhipu"
    assert overrides["text_to_image"] == "cogview-3"
    assert overrides["image_create_size"] == "1024x1024"


def test_setting_new_default_unsets_previous_default_in_same_scope() -> None:
    service = make_service()
    first = service.create_platform_config(
        capability="text_to_speech",
        provider="openai",
        model_name="tts-1",
        api_key="sk-one",
        is_default=True,
    )
    second = service.create_platform_config(
        capability="text_to_speech",
        provider="minimax",
        model_name="speech-2.8-hd",
        api_key="sk-two",
        is_default=True,
    )

    assert service.resolve_config_for_scope(first["capability_config_id"]).is_default is False
    assert service.resolve_config_for_scope(second["capability_config_id"]).is_default is True

from __future__ import annotations

import re
import secrets
from dataclasses import dataclass
from typing import Any

from config import conf
from cow_platform.domain.models import CapabilityConfigDefinition
from cow_platform.repositories.capability_config_repository import CapabilityConfigRepository
from cow_platform.services.model_config_service import PROVIDER_RUNTIME_MAP
from cow_platform.services.runtime_state_service import RuntimeStateService
from cow_platform.services.tenant_service import TenantService


CAPABILITY_CONFIG_SCOPES = {"platform", "tenant"}
CAPABILITY_TYPES = {
    "chat": "对话模型",
    "multimodal": "多模态理解",
    "image_generation": "文生图",
    "speech_to_text": "语音识别",
    "text_to_speech": "语音合成",
    "translation": "翻译",
}


@dataclass(frozen=True, slots=True)
class CapabilityProviderOption:
    provider: str
    label: str
    capabilities: tuple[str, ...]
    default_api_base: str = ""
    custom: bool = False


CAPABILITY_PROVIDER_OPTIONS: dict[str, CapabilityProviderOption] = {
    "openai": CapabilityProviderOption(
        "openai",
        "OpenAI / OpenAI 兼容",
        ("multimodal", "image_generation", "speech_to_text", "text_to_speech"),
        "https://api.openai.com/v1",
    ),
    "custom": CapabilityProviderOption(
        "custom",
        "自定义 OpenAI 兼容",
        ("multimodal", "image_generation", "speech_to_text", "text_to_speech", "translation"),
        custom=True,
    ),
    "dashscope": CapabilityProviderOption(
        "dashscope",
        "通义千问 DashScope",
        ("multimodal",),
    ),
    "zhipu": CapabilityProviderOption(
        "zhipu",
        "智谱 GLM / CogView",
        ("multimodal", "image_generation"),
        "https://open.bigmodel.cn/api/paas/v4",
    ),
    "modelscope": CapabilityProviderOption(
        "modelscope",
        "魔搭 ModelScope",
        ("image_generation",),
        "https://api-inference.modelscope.cn/v1",
    ),
    "moonshot": CapabilityProviderOption(
        "moonshot",
        "Kimi / Moonshot",
        ("multimodal",),
        "https://api.moonshot.cn/v1",
    ),
    "doubao": CapabilityProviderOption(
        "doubao",
        "豆包 Doubao",
        ("multimodal",),
        "https://ark.cn-beijing.volces.com/api/v3",
    ),
    "claudeAPI": CapabilityProviderOption(
        "claudeAPI",
        "Claude",
        ("multimodal",),
        "https://api.anthropic.com/v1",
    ),
    "gemini": CapabilityProviderOption(
        "gemini",
        "Gemini",
        ("multimodal",),
        "https://generativelanguage.googleapis.com",
    ),
    "minimax": CapabilityProviderOption(
        "minimax",
        "MiniMax",
        ("multimodal", "text_to_speech"),
        "https://api.minimax.io",
    ),
    "linkai": CapabilityProviderOption(
        "linkai",
        "LinkAI",
        ("multimodal", "image_generation", "speech_to_text", "text_to_speech"),
        "https://api.link-ai.tech",
    ),
    "baidu": CapabilityProviderOption("baidu", "百度语音/翻译", ("speech_to_text", "text_to_speech", "translation")),
    "google": CapabilityProviderOption("google", "Google 语音", ("speech_to_text", "text_to_speech")),
    "azure": CapabilityProviderOption("azure", "Azure Speech", ("speech_to_text", "text_to_speech")),
    "ali": CapabilityProviderOption("ali", "阿里云语音", ("speech_to_text", "text_to_speech")),
    "xunfei": CapabilityProviderOption("xunfei", "讯飞语音", ("speech_to_text", "text_to_speech")),
    "tencent": CapabilityProviderOption("tencent", "腾讯云语音", ("text_to_speech",)),
    "edge": CapabilityProviderOption("edge", "Edge 在线语音", ("text_to_speech",)),
    "elevenlabs": CapabilityProviderOption("elevenlabs", "ElevenLabs", ("text_to_speech",)),
    "pytts": CapabilityProviderOption("pytts", "本地 pyttsx3", ("text_to_speech",)),
}


def provider_bot_type(provider: str) -> str:
    mapping = PROVIDER_RUNTIME_MAP.get((provider or "").strip())
    return mapping.bot_type if mapping else ""


class CapabilityConfigService:
    """平台/租户独立能力配置服务。"""

    def __init__(
        self,
        repository: CapabilityConfigRepository | None = None,
        tenant_service: TenantService | None = None,
        runtime_state_service: RuntimeStateService | None = None,
    ):
        self.repository = repository or CapabilityConfigRepository()
        self.tenant_service = tenant_service or TenantService()
        self.runtime_state_service = runtime_state_service or RuntimeStateService()

    def list_capability_types(self) -> list[dict[str, str]]:
        return [
            {"capability": capability, "label": label}
            for capability, label in CAPABILITY_TYPES.items()
            if capability != "chat"
        ]

    def list_provider_options(self, *, capability: str = "") -> list[dict[str, object]]:
        resolved_capability = (capability or "").strip()
        if resolved_capability:
            self._normalize_capability(resolved_capability)
        options = []
        for option in CAPABILITY_PROVIDER_OPTIONS.values():
            if resolved_capability and resolved_capability not in option.capabilities:
                continue
            options.append(
                {
                    "provider": option.provider,
                    "label": option.label,
                    "capabilities": list(option.capabilities),
                    "default_api_base": option.default_api_base,
                    "custom": option.custom,
                }
            )
        return options

    def list_platform_configs(self) -> list[CapabilityConfigDefinition]:
        return self.repository.list_capability_configs(scope="platform")

    def list_tenant_configs(self, tenant_id: str) -> list[CapabilityConfigDefinition]:
        resolved_tenant_id = self._normalize_required("tenant_id", tenant_id)
        self.tenant_service.resolve_tenant(resolved_tenant_id)
        return self.repository.list_capability_configs(scope="tenant", tenant_id=resolved_tenant_id)

    def list_available_configs(self, tenant_id: str) -> list[CapabilityConfigDefinition]:
        resolved_tenant_id = self._normalize_required("tenant_id", tenant_id)
        self.tenant_service.resolve_tenant(resolved_tenant_id)
        platform_items = self.repository.list_capability_configs(
            scope="platform",
            enabled=True,
            public_only=True,
        )
        tenant_items = self.repository.list_capability_configs(
            scope="tenant",
            tenant_id=resolved_tenant_id,
            enabled=True,
        )
        return platform_items + tenant_items

    def create_platform_config(
        self,
        *,
        capability: str,
        provider: str,
        model_name: str,
        display_name: str = "",
        api_key: str = "",
        api_base: str = "",
        enabled: bool = True,
        is_public: bool = True,
        is_default: bool = False,
        metadata: dict[str, Any] | None = None,
        created_by: str = "",
        capability_config_id: str = "",
    ) -> dict[str, Any]:
        definition = self._create_config(
            scope="platform",
            tenant_id="",
            capability=capability,
            provider=provider,
            model_name=model_name,
            display_name=display_name,
            api_key=api_key,
            api_base=api_base,
            enabled=enabled,
            is_public=is_public,
            is_default=is_default,
            metadata=metadata,
            created_by=created_by,
            capability_config_id=capability_config_id,
        )
        self.runtime_state_service.safe_invalidate_platform(
            reason="platform_capability_config_created",
            metadata={"capability_config_id": definition.capability_config_id},
        )
        return self.serialize_config(definition)

    def create_tenant_config(
        self,
        *,
        tenant_id: str,
        capability: str,
        provider: str,
        model_name: str,
        display_name: str = "",
        api_key: str = "",
        api_base: str = "",
        enabled: bool = True,
        is_default: bool = False,
        metadata: dict[str, Any] | None = None,
        created_by: str = "",
        capability_config_id: str = "",
    ) -> dict[str, Any]:
        resolved_tenant_id = self._normalize_required("tenant_id", tenant_id)
        self.tenant_service.resolve_tenant(resolved_tenant_id)
        definition = self._create_config(
            scope="tenant",
            tenant_id=resolved_tenant_id,
            capability=capability,
            provider=provider,
            model_name=model_name,
            display_name=display_name,
            api_key=api_key,
            api_base=api_base,
            enabled=enabled,
            is_public=False,
            is_default=is_default,
            metadata=metadata,
            created_by=created_by,
            capability_config_id=capability_config_id,
        )
        self.runtime_state_service.safe_invalidate_tenant(
            resolved_tenant_id,
            reason="tenant_capability_config_created",
            metadata={"capability_config_id": definition.capability_config_id},
        )
        return self.serialize_config(definition)

    def update_config(
        self,
        capability_config_id: str,
        *,
        expected_scope: str = "",
        tenant_id: str = "",
        capability: str | None = None,
        provider: str | None = None,
        model_name: str | None = None,
        display_name: str | None = None,
        api_key: str | None = None,
        api_base: str | None = None,
        enabled: bool | None = None,
        is_public: bool | None = None,
        is_default: bool | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        existing = self.resolve_config_for_scope(
            capability_config_id,
            expected_scope=expected_scope,
            tenant_id=tenant_id,
        )
        next_capability = self._normalize_capability(capability) if capability is not None else existing.capability
        next_provider = self._normalize_provider(provider) if provider is not None else existing.provider
        self._validate_provider_support(next_provider, next_capability)
        next_model_name = self._normalize_required("model_name", model_name) if model_name is not None else existing.model_name
        next_api_key = existing.api_key if api_key is None else (api_key.strip() if isinstance(api_key, str) else "")
        next_api_base = existing.api_base if api_base is None else (api_base.strip() if isinstance(api_base, str) else "")
        if next_provider == "custom" and not next_api_base:
            raise ValueError("api_base must not be empty for custom capability provider")
        if next_provider == "openai" and not next_api_base:
            next_api_base = CAPABILITY_PROVIDER_OPTIONS[next_provider].default_api_base
        next_is_default = existing.is_default if is_default is None else bool(is_default)
        if next_is_default:
            self.repository.unset_default_for_scope(
                scope=existing.scope,
                tenant_id=existing.tenant_id,
                capability=next_capability,
                except_id=existing.capability_config_id,
            )
        definition = self.repository.update_capability_config(
            existing.capability_config_id,
            capability=next_capability,
            provider=next_provider,
            model_name=next_model_name,
            display_name=(display_name or "").strip() if display_name is not None else None,
            api_key=next_api_key,
            api_base=next_api_base,
            enabled=enabled,
            is_public=is_public if existing.scope == "platform" else False,
            is_default=next_is_default,
            metadata=metadata,
        )
        self._invalidate_config_scope(definition, reason="capability_config_updated")
        return self.serialize_config(definition)

    def delete_config(
        self,
        capability_config_id: str,
        *,
        expected_scope: str = "",
        tenant_id: str = "",
    ) -> dict[str, Any]:
        existing = self.resolve_config_for_scope(
            capability_config_id,
            expected_scope=expected_scope,
            tenant_id=tenant_id,
        )
        definition = self.repository.delete_capability_config(existing.capability_config_id)
        self._invalidate_config_scope(definition, reason="capability_config_deleted")
        return self.serialize_config(definition)

    def resolve_config_for_scope(
        self,
        capability_config_id: str,
        *,
        expected_scope: str = "",
        tenant_id: str = "",
    ) -> CapabilityConfigDefinition:
        definition = self.repository.get_capability_config(
            self._normalize_required("capability_config_id", capability_config_id)
        )
        if definition is None:
            raise KeyError(f"capability config not found: {capability_config_id}")
        if expected_scope and definition.scope != expected_scope:
            raise PermissionError("capability config scope mismatch")
        if definition.scope == "tenant" and tenant_id and definition.tenant_id != tenant_id:
            raise PermissionError("cannot access another tenant capability config")
        return definition

    def resolve_for_runtime(self, tenant_id: str, capability: str) -> CapabilityConfigDefinition | None:
        resolved_tenant_id = self._normalize_required("tenant_id", tenant_id)
        resolved_capability = self._normalize_capability(capability)
        self.tenant_service.resolve_tenant(resolved_tenant_id)
        tenant_items = self.repository.list_capability_configs(
            scope="tenant",
            tenant_id=resolved_tenant_id,
            capability=resolved_capability,
            enabled=True,
        )
        platform_items = self.repository.list_capability_configs(
            scope="platform",
            capability=resolved_capability,
            enabled=True,
            public_only=True,
        )
        return self._pick_runtime_config(tenant_items) or self._pick_runtime_config(platform_items)

    def build_runtime_overrides(self, definition: CapabilityConfigDefinition) -> dict[str, Any]:
        overrides = self._provider_credential_overrides(definition)
        metadata = dict(definition.metadata or {})
        capability = definition.capability
        if capability == "image_generation":
            bot_type = provider_bot_type(definition.provider)
            if bot_type:
                overrides["bot_type"] = bot_type
            overrides["text_to_image"] = definition.model_name
            if metadata.get("image_size"):
                overrides["image_create_size"] = metadata["image_size"]
            if metadata.get("image_style"):
                overrides["dalle3_image_style"] = metadata["image_style"]
            if metadata.get("image_quality"):
                overrides["dalle3_image_quality"] = metadata["image_quality"]
        elif capability == "speech_to_text":
            overrides["voice_to_text"] = self._voice_engine(definition.provider)
            overrides["speech_to_text_model"] = definition.model_name
        elif capability == "text_to_speech":
            overrides["text_to_voice"] = self._voice_engine(definition.provider)
            overrides["text_to_voice_model"] = definition.model_name
            voice = metadata.get("voice") or metadata.get("voice_id") or metadata.get("tts_voice_id")
            if voice:
                overrides["tts_voice_id"] = voice
        elif capability == "multimodal":
            vision_config = self._vision_tool_config(definition)
            tools_config = dict(conf().get("tools", {}) or {})
            tools_config["vision"] = {**dict(tools_config.get("vision", {}) or {}), **vision_config}
            overrides["tools"] = tools_config
        elif capability == "translation":
            overrides["translate"] = definition.provider
        return overrides

    @staticmethod
    def _vision_tool_config(definition: CapabilityConfigDefinition) -> dict[str, Any]:
        return {
            "model": definition.model_name,
            "provider": definition.provider,
            "capability_config_id": definition.capability_config_id,
        }

    def serialize_config(self, definition: CapabilityConfigDefinition, *, include_secret: bool = False) -> dict[str, Any]:
        record = self.repository.export_record(definition)
        api_key = str(record.get("api_key", "") or "")
        record["api_key_set"] = bool(api_key)
        record["api_key_masked"] = api_key if include_secret else self._mask_secret(api_key)
        if not include_secret:
            record.pop("api_key", None)
        return record

    def _create_config(
        self,
        *,
        scope: str,
        tenant_id: str,
        capability: str,
        provider: str,
        model_name: str,
        display_name: str,
        api_key: str,
        api_base: str,
        enabled: bool,
        is_public: bool,
        is_default: bool,
        metadata: dict[str, Any] | None,
        created_by: str,
        capability_config_id: str,
    ) -> CapabilityConfigDefinition:
        resolved_scope = self._normalize_scope(scope)
        resolved_capability = self._normalize_capability(capability)
        resolved_provider = self._normalize_provider(provider)
        self._validate_provider_support(resolved_provider, resolved_capability)
        resolved_model_name = self._normalize_required("model_name", model_name)
        resolved_api_key = (api_key or "").strip()
        resolved_api_base = (api_base or "").strip()
        if resolved_provider == "custom" and not resolved_api_base:
            raise ValueError("api_base must not be empty for custom capability provider")
        if resolved_provider == "openai" and not resolved_api_base:
            resolved_api_base = CAPABILITY_PROVIDER_OPTIONS[resolved_provider].default_api_base
        resolved_id = (capability_config_id or "").strip() or self._generate_capability_config_id(
            scope=resolved_scope,
            tenant_id=tenant_id,
            capability=resolved_capability,
            provider=resolved_provider,
            model_name=resolved_model_name,
        )
        if is_default:
            self.repository.unset_default_for_scope(
                scope=resolved_scope,
                tenant_id=tenant_id,
                capability=resolved_capability,
            )
        return self.repository.create_capability_config(
            capability_config_id=resolved_id,
            scope=resolved_scope,
            tenant_id=tenant_id,
            capability=resolved_capability,
            provider=resolved_provider,
            model_name=resolved_model_name,
            display_name=(display_name or "").strip() or resolved_model_name,
            api_key=resolved_api_key,
            api_base=resolved_api_base,
            enabled=bool(enabled),
            is_public=bool(is_public) if resolved_scope == "platform" else False,
            is_default=bool(is_default),
            metadata=metadata or {},
            created_by=(created_by or "").strip(),
        )

    def _provider_credential_overrides(self, definition: CapabilityConfigDefinition) -> dict[str, Any]:
        provider = definition.provider
        api_base = definition.api_base
        api_key = definition.api_key
        metadata = dict(definition.metadata or {})
        overrides: dict[str, Any] = {}
        if provider in {"openai", "custom"}:
            if api_key:
                overrides["open_ai_api_key"] = api_key
            overrides["open_ai_api_base"] = api_base or CAPABILITY_PROVIDER_OPTIONS["openai"].default_api_base
            return overrides
        if provider == "dashscope":
            if api_key:
                overrides["dashscope_api_key"] = api_key
            return overrides
        if provider == "zhipu":
            if api_key:
                overrides["zhipu_ai_api_key"] = api_key
            if api_base:
                overrides["zhipu_ai_api_base"] = api_base
            return overrides
        if provider == "modelscope":
            if api_key:
                overrides["modelscope_api_key"] = api_key
            if api_base:
                overrides["modelscope_base_url"] = api_base
            return overrides
        if provider == "moonshot":
            if api_key:
                overrides["moonshot_api_key"] = api_key
            if api_base:
                overrides["moonshot_base_url"] = api_base
            return overrides
        if provider == "doubao":
            if api_key:
                overrides["ark_api_key"] = api_key
            if api_base:
                overrides["ark_base_url"] = api_base
            return overrides
        if provider == "claudeAPI":
            if api_key:
                overrides["claude_api_key"] = api_key
            if api_base:
                overrides["claude_api_base"] = api_base
            return overrides
        if provider == "gemini":
            if api_key:
                overrides["gemini_api_key"] = api_key
            if api_base:
                overrides["gemini_api_base"] = api_base
            return overrides
        if provider == "minimax":
            if api_key:
                overrides["minimax_api_key"] = api_key
            if api_base:
                overrides["minimax_api_base"] = api_base
            return overrides
        if provider == "linkai":
            if api_key:
                overrides["linkai_api_key"] = api_key
                overrides["open_ai_api_key"] = api_key
            if api_base:
                overrides["linkai_api_base"] = api_base
                overrides["open_ai_api_base"] = api_base.rstrip("/") + "/v1"
            overrides["use_linkai"] = True
            return overrides
        if provider == "baidu":
            if api_key:
                overrides["baidu_api_key"] = api_key
            if metadata.get("app_id"):
                overrides["baidu_app_id"] = metadata["app_id"]
            if metadata.get("secret_key"):
                overrides["baidu_secret_key"] = metadata["secret_key"]
            return overrides
        if provider == "azure":
            if api_key:
                overrides["azure_voice_api_key"] = api_key
            if metadata.get("region"):
                overrides["azure_voice_region"] = metadata["region"]
            return overrides
        if provider == "ali":
            if api_key:
                overrides["qwen_access_key_id"] = api_key
            if metadata.get("access_key_secret"):
                overrides["qwen_access_key_secret"] = metadata["access_key_secret"]
            return overrides
        if provider == "xunfei":
            if api_key:
                overrides["xunfei_api_key"] = api_key
            if metadata.get("app_id"):
                overrides["xunfei_app_id"] = metadata["app_id"]
            if metadata.get("api_secret"):
                overrides["xunfei_api_secret"] = metadata["api_secret"]
            return overrides
        if provider == "elevenlabs":
            if api_key:
                overrides["xi_api_key"] = api_key
            if metadata.get("voice_id"):
                overrides["xi_voice_id"] = metadata["voice_id"]
            return overrides
        return overrides

    @staticmethod
    def _voice_engine(provider: str) -> str:
        if provider == "custom":
            return "openai"
        if provider == "elevenlabs":
            return "elevenlabs"
        return provider

    @staticmethod
    def _pick_runtime_config(items: list[CapabilityConfigDefinition]) -> CapabilityConfigDefinition | None:
        if not items:
            return None
        for item in items:
            if item.is_default:
                return item
        return items[0]

    @staticmethod
    def _normalize_required(name: str, value: str | None) -> str:
        resolved = (value or "").strip()
        if not resolved:
            raise ValueError(f"{name} must not be empty")
        return resolved

    @staticmethod
    def _normalize_scope(scope: str) -> str:
        resolved = (scope or "").strip().lower()
        if resolved not in CAPABILITY_CONFIG_SCOPES:
            raise ValueError(f"unsupported capability config scope: {resolved}")
        return resolved

    @staticmethod
    def _normalize_capability(capability: str | None) -> str:
        resolved = (capability or "").strip()
        if resolved not in CAPABILITY_TYPES or resolved == "chat":
            raise ValueError(f"unsupported capability: {resolved}")
        return resolved

    @staticmethod
    def _normalize_provider(provider: str | None) -> str:
        resolved = (provider or "").strip()
        if resolved not in CAPABILITY_PROVIDER_OPTIONS:
            raise ValueError(f"unsupported capability provider: {resolved}")
        return resolved

    @staticmethod
    def _validate_provider_support(provider: str, capability: str) -> None:
        option = CAPABILITY_PROVIDER_OPTIONS[provider]
        if capability not in option.capabilities:
            raise ValueError(f"provider {provider} does not support capability {capability}")

    def _generate_capability_config_id(
        self,
        *,
        scope: str,
        tenant_id: str,
        capability: str,
        provider: str,
        model_name: str,
    ) -> str:
        seed = f"{scope}-{tenant_id}-{capability}-{provider}-{model_name}"
        for _ in range(50):
            slug = re.sub(r"[^a-z0-9]+", "-", seed.lower()).strip("-")[:42].strip("-")
            suffix = secrets.token_hex(4)
            candidate = f"cap_{slug}_{suffix}" if slug else f"cap_{suffix}"
            if self.repository.get_capability_config(candidate) is None:
                return candidate
        raise RuntimeError("failed to generate capability config id")

    def _invalidate_config_scope(self, definition: CapabilityConfigDefinition, *, reason: str) -> None:
        metadata = {"capability_config_id": definition.capability_config_id}
        if definition.scope == "platform":
            self.runtime_state_service.safe_invalidate_platform(reason=reason, metadata=metadata)
            return
        self.runtime_state_service.safe_invalidate_tenant(
            definition.tenant_id,
            reason=reason,
            metadata=metadata,
        )

    @staticmethod
    def _mask_secret(value: str) -> str:
        if not value:
            return ""
        if len(value) <= 8:
            return "*" * len(value)
        return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"

from __future__ import annotations

import re
import secrets
from dataclasses import dataclass
from typing import Any

from config import conf
from cow_platform.domain.models import AgentDefinition, ModelConfigDefinition
from cow_platform.repositories.model_config_repository import ModelConfigRepository
from cow_platform.services.tenant_service import TenantService


MODEL_CONFIG_SCOPES = {"platform", "tenant"}


@dataclass(frozen=True, slots=True)
class ProviderRuntimeMapping:
    bot_type: str
    api_key_field: str = ""
    api_base_field: str = ""
    default_api_base: str = ""
    use_linkai: bool = False
    label: str = ""
    models: tuple[str, ...] = ()
    platform_configurable: bool = True
    tenant_configurable: bool = False
    custom: bool = False


PROVIDER_RUNTIME_MAP: dict[str, ProviderRuntimeMapping] = {
    "openai": ProviderRuntimeMapping(
        "openai",
        "open_ai_api_key",
        "open_ai_api_base",
        "https://api.openai.com/v1",
        label="OpenAI",
        models=("gpt-5.4", "gpt-4.1", "gpt-4o", "gpt-4o-mini", "o1-preview", "o1-mini"),
    ),
    "deepseek": ProviderRuntimeMapping(
        "deepseek",
        "deepseek_api_key",
        "deepseek_api_base",
        "https://api.deepseek.com/v1",
        label="DeepSeek",
        models=("deepseek-v4-pro", "deepseek-v4-flash", "deepseek-chat", "deepseek-reasoner"),
    ),
    "dashscope": ProviderRuntimeMapping(
        "dashscope",
        "dashscope_api_key",
        label="通义千问 Qwen",
        models=("qwen3.6-plus", "qwen3.5-plus", "qwen3-max", "qwen-max", "qwen-plus", "qwen-turbo", "qwq-plus"),
    ),
    "zhipu": ProviderRuntimeMapping(
        "zhipu",
        "zhipu_ai_api_key",
        "zhipu_ai_api_base",
        "https://open.bigmodel.cn/api/paas/v4",
        label="智谱 GLM",
        models=("glm-5.1", "glm-5-turbo", "glm-5", "glm-4.7", "glm-4-plus", "glm-4"),
    ),
    "moonshot": ProviderRuntimeMapping(
        "moonshot",
        "moonshot_api_key",
        "moonshot_base_url",
        "https://api.moonshot.cn/v1",
        label="Kimi",
        models=("kimi-k2.6", "kimi-k2.5", "kimi-k2", "moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"),
    ),
    "doubao": ProviderRuntimeMapping(
        "doubao",
        "ark_api_key",
        "ark_base_url",
        "https://ark.cn-beijing.volces.com/api/v3",
        label="豆包 Doubao",
        models=("doubao-seed-2-0-pro-260215", "doubao-seed-2-0-lite-260215", "doubao-seed-2-0-mini-260215", "doubao-seed-2-0-code-preview-260215"),
    ),
    "claudeAPI": ProviderRuntimeMapping(
        "claudeAPI",
        "claude_api_key",
        "claude_api_base",
        "https://api.anthropic.com/v1",
        label="Claude",
        models=("claude-sonnet-4-6", "claude-opus-4-6", "claude-sonnet-4-5", "claude-sonnet-4-0", "claude-3-5-sonnet-latest"),
    ),
    "gemini": ProviderRuntimeMapping(
        "gemini",
        "gemini_api_key",
        "gemini_api_base",
        "https://generativelanguage.googleapis.com",
        label="Gemini",
        models=("gemini-3.1-pro-preview", "gemini-3.1-flash-lite-preview", "gemini-3-pro-preview", "gemini-3-flash-preview", "gemini-2.5-pro-preview-05-06"),
    ),
    "minimax": ProviderRuntimeMapping(
        "minimax",
        "minimax_api_key",
        "minimax_api_base",
        "https://api.minimaxi.com/v1",
        label="MiniMax",
        models=("MiniMax-M2.7", "MiniMax-M2.7-highspeed", "MiniMax-M2.5", "MiniMax-M2.1", "abab6.5-chat"),
    ),
    "modelscope": ProviderRuntimeMapping(
        "modelscope",
        "modelscope_api_key",
        "modelscope_base_url",
        "https://api-inference.modelscope.cn/v1",
        label="魔搭 ModelScope",
        models=("deepseek-ai/DeepSeek-V3.2", "Qwen/Qwen3-235B-A22B-Instruct-2507", "Qwen/Qwen3.5-27B", "ZhipuAI/GLM-5"),
    ),
    "linkai": ProviderRuntimeMapping(
        "linkai",
        "linkai_api_key",
        "linkai_api_base",
        "https://api.link-ai.tech",
        True,
        label="LinkAI",
        models=("linkai-4o", "linkai-4-turbo", "linkai-3.5"),
    ),
    "custom": ProviderRuntimeMapping(
        "openai",
        "open_ai_api_key",
        "open_ai_api_base",
        "",
        label="自定义",
        platform_configurable=False,
        tenant_configurable=True,
        custom=True,
    ),
}


class ModelConfigService:
    """平台/租户模型配置服务。"""

    def __init__(
        self,
        repository: ModelConfigRepository | None = None,
        tenant_service: TenantService | None = None,
    ):
        self.repository = repository or ModelConfigRepository()
        self.tenant_service = tenant_service or TenantService()

    def list_provider_options(self, *, scope: str = "") -> list[dict[str, object]]:
        resolved_scope = (scope or "").strip()
        if resolved_scope and resolved_scope not in MODEL_CONFIG_SCOPES:
            raise ValueError(f"unsupported model config scope: {resolved_scope}")
        return [
            {
                "provider": provider,
                "label": mapping.label or provider,
                "bot_type": mapping.bot_type,
                "models": list(mapping.models),
                "custom": mapping.custom,
                "requires_api_base": mapping.custom,
                "platform_configurable": mapping.platform_configurable,
                "tenant_configurable": mapping.tenant_configurable,
            }
            for provider, mapping in PROVIDER_RUNTIME_MAP.items()
            if not resolved_scope
            or (resolved_scope == "platform" and mapping.platform_configurable)
            or (resolved_scope == "tenant" and mapping.tenant_configurable)
        ]

    def list_platform_models(self) -> list[ModelConfigDefinition]:
        return self.repository.list_model_configs(scope="platform")

    def list_tenant_models(self, tenant_id: str) -> list[ModelConfigDefinition]:
        resolved_tenant_id = self._normalize_required("tenant_id", tenant_id)
        self.tenant_service.resolve_tenant(resolved_tenant_id)
        return self.repository.list_model_configs(scope="tenant", tenant_id=resolved_tenant_id)

    def list_available_models(self, tenant_id: str) -> list[ModelConfigDefinition]:
        resolved_tenant_id = self._normalize_required("tenant_id", tenant_id)
        self.tenant_service.resolve_tenant(resolved_tenant_id)
        platform_items = [
            item
            for item in self.repository.list_model_configs(scope="platform", enabled=True)
            if item.is_public
        ]
        tenant_items = self.repository.list_model_configs(
            scope="tenant",
            tenant_id=resolved_tenant_id,
            enabled=True,
        )
        return platform_items + tenant_items

    def create_platform_model(
        self,
        *,
        provider: str,
        model_name: str,
        display_name: str = "",
        api_key: str = "",
        api_base: str = "",
        enabled: bool = True,
        is_public: bool = True,
        metadata: dict[str, Any] | None = None,
        created_by: str = "",
        model_config_id: str = "",
    ) -> dict[str, Any]:
        return self.serialize_model(
            self._create_model(
                scope="platform",
                tenant_id="",
                provider=provider,
                model_name=model_name,
                display_name=display_name,
                api_key=api_key,
                api_base=api_base,
                enabled=enabled,
                is_public=is_public,
                metadata=metadata,
                created_by=created_by,
                model_config_id=model_config_id,
            )
        )

    def create_tenant_model(
        self,
        *,
        tenant_id: str,
        provider: str,
        model_name: str,
        display_name: str = "",
        api_key: str = "",
        api_base: str = "",
        enabled: bool = True,
        metadata: dict[str, Any] | None = None,
        created_by: str = "",
        model_config_id: str = "",
    ) -> dict[str, Any]:
        resolved_tenant_id = self._normalize_required("tenant_id", tenant_id)
        self.tenant_service.resolve_tenant(resolved_tenant_id)
        return self.serialize_model(
            self._create_model(
                scope="tenant",
                tenant_id=resolved_tenant_id,
                provider=provider,
                model_name=model_name,
                display_name=display_name,
                api_key=api_key,
                api_base=api_base,
                enabled=enabled,
                is_public=False,
                metadata=metadata,
                created_by=created_by,
                model_config_id=model_config_id,
            )
        )

    def update_model(
        self,
        model_config_id: str,
        *,
        expected_scope: str = "",
        tenant_id: str = "",
        provider: str | None = None,
        model_name: str | None = None,
        display_name: str | None = None,
        api_key: str | None = None,
        api_base: str | None = None,
        enabled: bool | None = None,
        is_public: bool | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        existing = self.resolve_model_for_scope(
            model_config_id,
            expected_scope=expected_scope,
            tenant_id=tenant_id,
        )
        next_provider = self._normalize_provider(provider) if provider is not None else existing.provider
        next_mapping = PROVIDER_RUNTIME_MAP[next_provider]
        if existing.scope == "platform" and not next_mapping.platform_configurable:
            raise ValueError(f"provider is not configurable by platform admin: {next_provider}")
        if existing.scope == "tenant" and not next_mapping.tenant_configurable:
            raise ValueError(f"tenant model provider must be custom: {next_provider}")
        next_model_name = self._normalize_required("model_name", model_name) if model_name is not None else existing.model_name
        next_api_key = existing.api_key if api_key is None else (api_key.strip() if isinstance(api_key, str) else api_key)
        if existing.scope == "platform" and not next_api_key:
            raise ValueError("api_key must not be empty for platform model")
        if api_base is None:
            next_api_base = existing.api_base
        elif isinstance(api_base, str):
            next_api_base = api_base.strip()
        else:
            next_api_base = ""
        if not next_mapping.custom:
            next_api_base = ""
        elif not next_api_base:
            raise ValueError("api_base must not be empty for custom model")
        definition = self.repository.update_model_config(
            existing.model_config_id,
            provider=next_provider,
            model_name=next_model_name,
            display_name=(display_name or "").strip() if display_name is not None else None,
            api_key=next_api_key,
            api_base=next_api_base,
            enabled=enabled,
            is_public=is_public if existing.scope == "platform" else False,
            metadata=metadata,
        )
        return self.serialize_model(definition)

    def delete_model(
        self,
        model_config_id: str,
        *,
        expected_scope: str = "",
        tenant_id: str = "",
    ) -> dict[str, Any]:
        existing = self.resolve_model_for_scope(
            model_config_id,
            expected_scope=expected_scope,
            tenant_id=tenant_id,
        )
        return self.serialize_model(self.repository.delete_model_config(existing.model_config_id))

    def resolve_model_for_scope(
        self,
        model_config_id: str,
        *,
        expected_scope: str = "",
        tenant_id: str = "",
    ) -> ModelConfigDefinition:
        definition = self.repository.get_model_config(self._normalize_required("model_config_id", model_config_id))
        if definition is None:
            raise KeyError(f"model config not found: {model_config_id}")
        if expected_scope and definition.scope != expected_scope:
            raise PermissionError("model config scope mismatch")
        if definition.scope == "tenant" and tenant_id and definition.tenant_id != tenant_id:
            raise PermissionError("cannot access another tenant model config")
        return definition

    def resolve_for_agent(self, tenant_id: str, agent_definition: AgentDefinition) -> ModelConfigDefinition:
        resolved_tenant_id = self._normalize_required("tenant_id", tenant_id)
        if agent_definition.model_config_id:
            definition = self.resolve_model_for_scope(agent_definition.model_config_id)
            if not self._is_visible_to_tenant(definition, resolved_tenant_id):
                raise PermissionError("model config is not visible to tenant")
            if not definition.enabled:
                raise PermissionError("model config is disabled")
            return definition

        if agent_definition.model:
            for definition in self.list_available_models(resolved_tenant_id):
                if definition.model_name == agent_definition.model:
                    return definition

        model_name = agent_definition.model or str(conf().get("model", "") or "")
        return self.build_legacy_model_config(model_name)

    def build_runtime_overrides(self, definition: ModelConfigDefinition) -> dict[str, Any]:
        provider = self._normalize_provider(definition.provider)
        mapping = PROVIDER_RUNTIME_MAP[provider]
        overrides: dict[str, Any] = {
            "model": definition.model_name,
            "bot_type": "" if mapping.use_linkai else mapping.bot_type,
            "use_linkai": mapping.use_linkai,
        }
        if mapping.api_key_field and definition.api_key:
            overrides[mapping.api_key_field] = definition.api_key
            if provider == "linkai":
                overrides["open_ai_api_key"] = definition.api_key
        if mapping.api_base_field:
            api_base = definition.api_base if mapping.custom else mapping.default_api_base
            if api_base:
                overrides[mapping.api_base_field] = api_base
                if provider == "linkai":
                    overrides["open_ai_api_base"] = api_base.rstrip("/") + "/v1"
        return overrides

    def build_legacy_model_config(self, model_name: str) -> ModelConfigDefinition:
        resolved_model_name = model_name or str(conf().get("model", "") or "") or "gpt-4.1"
        provider = self._detect_provider_by_model(resolved_model_name)
        mapping = PROVIDER_RUNTIME_MAP[provider]
        return ModelConfigDefinition(
            model_config_id="legacy",
            scope="platform",
            tenant_id="",
            provider=provider,
            model_name=resolved_model_name,
            display_name=resolved_model_name or "Legacy default",
            api_key=str(conf().get(mapping.api_key_field, "") or "") if mapping.api_key_field else "",
            api_base=str(conf().get(mapping.api_base_field, mapping.default_api_base) or "") if mapping.api_base_field else "",
            enabled=True,
            is_public=True,
            metadata={"source": "legacy-config"},
        )

    def serialize_model(self, definition: ModelConfigDefinition, *, include_secret: bool = False) -> dict[str, Any]:
        record = self.repository.export_record(definition) if definition.model_config_id != "legacy" else {
            "model_config_id": definition.model_config_id,
            "scope": definition.scope,
            "tenant_id": definition.tenant_id,
            "provider": definition.provider,
            "model_name": definition.model_name,
            "display_name": definition.display_name,
            "api_key": definition.api_key,
            "api_base": definition.api_base,
            "enabled": definition.enabled,
            "is_public": definition.is_public,
            "metadata": dict(definition.metadata or {}),
            "created_by": definition.created_by,
            "created_at": None,
            "updated_at": None,
        }
        api_key = str(record.get("api_key", "") or "")
        mapping = PROVIDER_RUNTIME_MAP.get(str(record.get("provider", "") or ""))
        if mapping is not None and not mapping.custom:
            record["api_base"] = ""
        record["api_key_set"] = bool(api_key)
        record["api_key_masked"] = api_key if include_secret else self._mask_secret(api_key)
        if not include_secret:
            record.pop("api_key", None)
        return record

    def _create_model(
        self,
        *,
        scope: str,
        tenant_id: str,
        provider: str,
        model_name: str,
        display_name: str,
        api_key: str,
        api_base: str,
        enabled: bool,
        is_public: bool,
        metadata: dict[str, Any] | None,
        created_by: str,
        model_config_id: str,
    ) -> ModelConfigDefinition:
        resolved_scope = self._normalize_scope(scope)
        resolved_provider = self._normalize_provider(provider)
        mapping = PROVIDER_RUNTIME_MAP[resolved_provider]
        if resolved_scope == "platform" and not mapping.platform_configurable:
            raise ValueError(f"provider is not configurable by platform admin: {resolved_provider}")
        if resolved_scope == "tenant" and not mapping.tenant_configurable:
            raise ValueError(f"tenant model provider must be custom: {resolved_provider}")
        resolved_model_name = self._normalize_required("model_name", model_name)
        resolved_api_key = (api_key or "").strip()
        resolved_api_base = (api_base or "").strip() if mapping.custom else ""
        if resolved_scope == "platform" and not resolved_api_key:
            raise ValueError("api_key must not be empty for platform model")
        if mapping.custom and not resolved_api_base:
            raise ValueError("api_base must not be empty for custom model")
        resolved_id = (model_config_id or "").strip() or self._generate_model_config_id(
            scope=resolved_scope,
            tenant_id=tenant_id,
            provider=resolved_provider,
            model_name=resolved_model_name,
        )
        return self.repository.create_model_config(
            model_config_id=resolved_id,
            scope=resolved_scope,
            tenant_id=tenant_id,
            provider=resolved_provider,
            model_name=resolved_model_name,
            display_name=(display_name or "").strip() or resolved_model_name,
            api_key=resolved_api_key,
            api_base=resolved_api_base,
            enabled=bool(enabled),
            is_public=bool(is_public) if resolved_scope == "platform" else False,
            metadata=metadata or {},
            created_by=(created_by or "").strip(),
        )

    def _generate_model_config_id(self, *, scope: str, tenant_id: str, provider: str, model_name: str) -> str:
        seed = f"{scope}-{tenant_id}-{provider}-{model_name}"
        for _ in range(50):
            slug = re.sub(r"[^a-z0-9]+", "-", seed.lower()).strip("-")[:36].strip("-")
            suffix = secrets.token_hex(4)
            candidate = f"mdl_{slug}_{suffix}" if slug else f"mdl_{suffix}"
            if self.repository.get_model_config(candidate) is None:
                return candidate
        raise RuntimeError("failed to generate model config id")

    @staticmethod
    def _normalize_required(name: str, value: str | None) -> str:
        resolved = (value or "").strip()
        if not resolved:
            raise ValueError(f"{name} must not be empty")
        return resolved

    @staticmethod
    def _normalize_scope(scope: str) -> str:
        resolved = (scope or "").strip().lower()
        if resolved not in MODEL_CONFIG_SCOPES:
            raise ValueError(f"unsupported model config scope: {resolved}")
        return resolved

    @staticmethod
    def _normalize_provider(provider: str | None) -> str:
        resolved = (provider or "").strip()
        if resolved not in PROVIDER_RUNTIME_MAP:
            raise ValueError(f"unsupported model provider: {resolved}")
        return resolved

    @staticmethod
    def _is_visible_to_tenant(definition: ModelConfigDefinition, tenant_id: str) -> bool:
        if definition.scope == "platform":
            return definition.is_public
        return definition.tenant_id == tenant_id

    @staticmethod
    def _mask_secret(value: str) -> str:
        if not value:
            return ""
        if len(value) <= 8:
            return "*" * len(value)
        return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"

    @staticmethod
    def _detect_provider_by_model(model_name: str) -> str:
        text = (model_name or "").strip()
        lowered = text.lower()
        if lowered.startswith(("deepseek",)):
            return "deepseek"
        if lowered.startswith(("qwen", "qwq", "qvq")):
            return "dashscope"
        if lowered.startswith(("glm",)):
            return "zhipu"
        if lowered.startswith(("kimi", "moonshot")):
            return "moonshot"
        if lowered.startswith(("doubao",)):
            return "doubao"
        if lowered.startswith(("claude",)):
            return "claudeAPI"
        if lowered.startswith(("gemini",)):
            return "gemini"
        if lowered.startswith(("minimax", "abab")):
            return "minimax"
        if "/" in text:
            return "modelscope"
        if lowered.startswith("linkai"):
            return "linkai"
        return "openai"

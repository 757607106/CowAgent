from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Any

from cow_platform.domain.models import ChannelConfigDefinition
from cow_platform.repositories.channel_config_repository import ChannelConfigRepository
from cow_platform.services.tenant_service import TenantService


@dataclass(frozen=True, slots=True)
class ChannelFieldDefinition:
    key: str
    label: str
    field_type: str = "text"
    default: str | int | bool | list[str] = ""
    visible: bool = True


@dataclass(frozen=True, slots=True)
class ChannelTypeDefinition:
    channel_type: str
    label: str
    fields: tuple[ChannelFieldDefinition, ...]
    managed_runtime: bool = False
    webhook_path_prefix: str = ""


CHANNEL_TYPE_DEFS: dict[str, ChannelTypeDefinition] = {
    "feishu": ChannelTypeDefinition(
        channel_type="feishu",
        label="飞书",
        managed_runtime=True,
        fields=(
            ChannelFieldDefinition("feishu_app_id", "App ID"),
            ChannelFieldDefinition("feishu_app_secret", "App Secret", "secret"),
            ChannelFieldDefinition("feishu_bot_name", "Bot Name"),
            ChannelFieldDefinition("feishu_token", "Verification Token", "secret", visible=False),
            ChannelFieldDefinition("feishu_event_mode", "Event Mode", default="websocket", visible=False),
            ChannelFieldDefinition("feishu_port", "Port", "number", 9891, visible=False),
        ),
    ),
    "qq": ChannelTypeDefinition(
        channel_type="qq",
        label="QQ 机器人",
        managed_runtime=True,
        fields=(
            ChannelFieldDefinition("qq_app_id", "App ID"),
            ChannelFieldDefinition("qq_app_secret", "App Secret", "secret"),
        ),
    ),
    "wechatmp": ChannelTypeDefinition(
        channel_type="wechatmp",
        label="公众号",
        webhook_path_prefix="/wx",
        fields=(
            ChannelFieldDefinition("single_chat_prefix", "Single Chat Prefix", "list", [""]),
            ChannelFieldDefinition("wechatmp_app_id", "App ID"),
            ChannelFieldDefinition("wechatmp_app_secret", "App Secret", "secret"),
            ChannelFieldDefinition("wechatmp_aes_key", "AES Key", "secret"),
            ChannelFieldDefinition("wechatmp_token", "Token", "secret"),
            ChannelFieldDefinition("wechatmp_port", "Port", "number", 80),
        ),
    ),
    "wechatmp_service": ChannelTypeDefinition(
        channel_type="wechatmp_service",
        label="服务号",
        webhook_path_prefix="/wx",
        fields=(
            ChannelFieldDefinition("single_chat_prefix", "Single Chat Prefix", "list", [""]),
            ChannelFieldDefinition("wechatmp_app_id", "App ID"),
            ChannelFieldDefinition("wechatmp_app_secret", "App Secret", "secret"),
            ChannelFieldDefinition("wechatmp_aes_key", "AES Key", "secret"),
            ChannelFieldDefinition("wechatmp_token", "Token", "secret"),
            ChannelFieldDefinition("wechatmp_port", "Port", "number", 80),
        ),
    ),
    "wechatcom_app": ChannelTypeDefinition(
        channel_type="wechatcom_app",
        label="企微自建应用",
        managed_runtime=True,
        fields=(
            ChannelFieldDefinition("single_chat_prefix", "Single Chat Prefix", "list", [""]),
            ChannelFieldDefinition("wechatcom_corp_id", "Corp ID"),
            ChannelFieldDefinition("wechatcomapp_token", "Token", "secret"),
            ChannelFieldDefinition("wechatcomapp_secret", "Secret", "secret"),
            ChannelFieldDefinition("wechatcomapp_agent_id", "Agent ID"),
            ChannelFieldDefinition("wechatcomapp_aes_key", "AES Key", "secret"),
            ChannelFieldDefinition("wechatcomapp_port", "Port", "number", 9898),
        ),
    ),
    "dingtalk": ChannelTypeDefinition(
        channel_type="dingtalk",
        label="钉钉",
        managed_runtime=True,
        fields=(
            ChannelFieldDefinition("dingtalk_client_id", "Client ID"),
            ChannelFieldDefinition("dingtalk_client_secret", "Client Secret", "secret"),
            ChannelFieldDefinition("dingtalk_card_enabled", "Card Enabled", "bool", False, visible=False),
        ),
    ),
    "wecom_bot": ChannelTypeDefinition(
        channel_type="wecom_bot",
        label="企微智能机器人",
        managed_runtime=True,
        fields=(
            ChannelFieldDefinition("wecom_bot_id", "Bot ID"),
            ChannelFieldDefinition("wecom_bot_secret", "Bot Secret", "secret"),
        ),
    ),
    "weixin": ChannelTypeDefinition(
        channel_type="weixin",
        label="微信",
        managed_runtime=True,
        fields=(
            ChannelFieldDefinition("weixin_token", "Bot Token", "secret", visible=False),
            ChannelFieldDefinition("weixin_base_url", "API Base URL", default="https://ilinkai.weixin.qq.com", visible=False),
            ChannelFieldDefinition("weixin_cdn_base_url", "CDN Base URL", default="https://novac2c.cdn.weixin.qq.com/c2c", visible=False),
            ChannelFieldDefinition("weixin_credentials_path", "Credentials Path", visible=False),
        ),
    ),
}


class ChannelConfigService:
    """Tenant-scoped channel access configuration service."""

    def __init__(
        self,
        repository: ChannelConfigRepository | None = None,
        tenant_service: TenantService | None = None,
    ):
        self.repository = repository or ChannelConfigRepository()
        self.tenant_service = tenant_service or TenantService()

    def list_channel_type_defs(self) -> list[dict[str, object]]:
        return [self.serialize_channel_type(definition) for definition in CHANNEL_TYPE_DEFS.values()]

    def list_channel_configs(
        self,
        *,
        tenant_id: str,
        channel_type: str = "",
        enabled: bool | None = None,
    ) -> list[ChannelConfigDefinition]:
        resolved_tenant_id = self._normalize_required("tenant_id", tenant_id)
        self.tenant_service.resolve_tenant(resolved_tenant_id)
        return self.repository.list_channel_configs(
            tenant_id=resolved_tenant_id,
            channel_type=(channel_type or "").strip(),
            enabled=enabled,
        )

    def list_enabled_runtime_configs(self) -> list[ChannelConfigDefinition]:
        return [
            item
            for item in self.repository.list_channel_configs(enabled=True)
            if self.is_managed_runtime_channel(item.channel_type)
        ]

    def resolve_channel_config(
        self,
        *,
        channel_config_id: str,
        tenant_id: str = "",
    ) -> ChannelConfigDefinition:
        definition = self.repository.get_channel_config(
            channel_config_id=self._normalize_required("channel_config_id", channel_config_id),
            tenant_id=(tenant_id or "").strip(),
        )
        if definition is None:
            raise KeyError(f"channel config not found: {channel_config_id}")
        return definition

    def create_channel_config(
        self,
        *,
        tenant_id: str,
        channel_type: str,
        name: str,
        config: dict[str, Any] | None = None,
        enabled: bool = True,
        metadata: dict[str, Any] | None = None,
        created_by: str = "",
        channel_config_id: str = "",
    ) -> dict[str, Any]:
        resolved_tenant_id = self._normalize_required("tenant_id", tenant_id)
        self.tenant_service.resolve_tenant(resolved_tenant_id)
        resolved_channel_type = self._normalize_channel_type(channel_type)
        resolved_id = (channel_config_id or "").strip() or self._generate_channel_config_id(
            tenant_id=resolved_tenant_id,
            channel_type=resolved_channel_type,
        )
        definition = self.repository.create_channel_config(
            tenant_id=resolved_tenant_id,
            channel_config_id=resolved_id,
            name=self._normalize_required("name", name),
            channel_type=resolved_channel_type,
            config=self._normalize_config(resolved_channel_type, config or {}),
            enabled=bool(enabled),
            metadata=metadata or {},
            created_by=(created_by or "").strip(),
        )
        return self.serialize_channel_config(definition)

    def update_channel_config(
        self,
        *,
        channel_config_id: str,
        tenant_id: str = "",
        name: str | None = None,
        channel_type: str | None = None,
        config: dict[str, Any] | None = None,
        enabled: bool | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        existing = self.resolve_channel_config(channel_config_id=channel_config_id, tenant_id=tenant_id)
        resolved_channel_type = existing.channel_type if channel_type is None else self._normalize_channel_type(channel_type)
        merged_config = None
        if config is not None:
            merged_config = self._merge_update_config(
                channel_type=resolved_channel_type,
                current=dict(existing.config or {}),
                updates=config,
            )
        definition = self.repository.update_channel_config(
            channel_config_id=existing.channel_config_id,
            tenant_id=existing.tenant_id,
            name=name,
            channel_type=resolved_channel_type,
            config=merged_config,
            enabled=enabled,
            metadata=metadata,
        )
        return self.serialize_channel_config(definition)

    def delete_channel_config(self, *, channel_config_id: str, tenant_id: str = "") -> dict[str, Any]:
        existing = self.resolve_channel_config(channel_config_id=channel_config_id, tenant_id=tenant_id)
        from cow_platform.repositories.binding_repository import ChannelBindingRepository

        linked_bindings = ChannelBindingRepository().list_bindings(
            tenant_id=existing.tenant_id,
            channel_config_id=existing.channel_config_id,
        )
        if linked_bindings:
            raise ValueError("channel config is still used by bindings")
        return self.serialize_channel_config(
            self.repository.delete_channel_config(
                channel_config_id=existing.channel_config_id,
                tenant_id=existing.tenant_id,
            )
        )

    def build_runtime_overrides(self, definition: ChannelConfigDefinition) -> dict[str, Any]:
        overrides = self._config_with_defaults(definition.channel_type, dict(definition.config or {}))
        if definition.channel_type == "weixin" and not overrides.get("weixin_credentials_path"):
            overrides["weixin_credentials_path"] = f"~/.cowagent/weixin/{definition.channel_config_id}.json"
        return overrides

    def serialize_channel_config(
        self,
        definition: ChannelConfigDefinition,
        *,
        include_secret: bool = False,
    ) -> dict[str, Any]:
        record = self.repository.export_record(definition)
        config = self._config_with_defaults(definition.channel_type, dict(record.get("config", {}) or {}))
        type_def = CHANNEL_TYPE_DEFS[definition.channel_type]
        secret_keys = self._secret_keys(definition.channel_type)
        visible_keys = {field.key for field in type_def.fields if field.visible}
        fields = []
        for field in type_def.fields:
            if not field.visible:
                continue
            value = config.get(field.key, field.default)
            raw_secret = str(value or "") if field.key in secret_keys else ""
            fields.append(
                {
                    "key": field.key,
                    "label": field.label,
                    "type": field.field_type,
                    "value": value if include_secret or field.key not in secret_keys else self._mask_secret(raw_secret),
                    "default": field.default,
                    "secret_set": bool(raw_secret) if field.key in secret_keys else False,
                }
            )
        exported_config = config if include_secret else {
            key: value
            for key, value in config.items()
            if key in visible_keys
        }
        record["config"] = exported_config if include_secret else {
            key: (self._mask_secret(str(value or "")) if key in secret_keys else value)
            for key, value in exported_config.items()
        }
        record["fields"] = fields
        record["label"] = type_def.label
        record["managed_runtime"] = type_def.managed_runtime
        if type_def.webhook_path_prefix:
            record["webhook_path"] = f"{type_def.webhook_path_prefix}/{definition.channel_config_id}"
        else:
            record["webhook_path"] = ""
        return record

    @staticmethod
    def serialize_channel_type(definition: ChannelTypeDefinition) -> dict[str, object]:
        return {
            "channel_type": definition.channel_type,
            "label": definition.label,
            "managed_runtime": definition.managed_runtime,
            "webhook_path_prefix": definition.webhook_path_prefix,
            "fields": [
                {
                    "key": field.key,
                    "label": field.label,
                    "type": field.field_type,
                    "default": field.default,
                }
                for field in definition.fields
                if field.visible
            ],
        }

    @staticmethod
    def is_managed_runtime_channel(channel_type: str) -> bool:
        definition = CHANNEL_TYPE_DEFS.get(channel_type)
        if definition is None:
            return False
        if channel_type == "feishu":
            return True
        return definition.managed_runtime

    def _generate_channel_config_id(self, *, tenant_id: str, channel_type: str) -> str:
        for _ in range(50):
            candidate = f"chcfg_{channel_type}_{secrets.token_hex(4)}"
            if self.repository.get_channel_config(channel_config_id=candidate, tenant_id=tenant_id) is None:
                return candidate
        raise RuntimeError("failed to generate channel config id")

    def _normalize_config(self, channel_type: str, config: dict[str, Any]) -> dict[str, Any]:
        type_def = CHANNEL_TYPE_DEFS[channel_type]
        allowed_fields = {field.key: field for field in type_def.fields}
        normalized: dict[str, Any] = {}
        for key, value in (config or {}).items():
            if key not in allowed_fields:
                continue
            field = allowed_fields[key]
            if field.field_type == "number":
                if value in ("", None):
                    normalized[key] = field.default
                else:
                    normalized[key] = int(value)
            elif field.field_type == "bool":
                normalized[key] = self._normalize_bool(value)
            elif field.field_type == "list":
                normalized[key] = self._normalize_string_list(value, field.default)
            else:
                normalized[key] = str(value or "").strip()
        return self._config_with_defaults(channel_type, normalized)

    def _merge_update_config(
        self,
        *,
        channel_type: str,
        current: dict[str, Any],
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        secret_keys = self._secret_keys(channel_type)
        sanitized_updates: dict[str, Any] = {}
        for key, value in (updates or {}).items():
            if key in secret_keys and (value in ("", None) or self._is_masked_secret(value)):
                continue
            sanitized_updates[key] = value
        merged = dict(current or {})
        merged.update(sanitized_updates)
        return self._normalize_config(channel_type, merged)

    @staticmethod
    def _config_with_defaults(channel_type: str, config: dict[str, Any]) -> dict[str, Any]:
        type_def = CHANNEL_TYPE_DEFS[channel_type]
        merged = {
            field.key: list(field.default) if isinstance(field.default, list) else field.default
            for field in type_def.fields
            if field.default not in ("", None)
        }
        merged.update(config or {})
        return merged

    @staticmethod
    def _secret_keys(channel_type: str) -> set[str]:
        type_def = CHANNEL_TYPE_DEFS[channel_type]
        return {field.key for field in type_def.fields if field.field_type == "secret"}

    @staticmethod
    def _normalize_required(name: str, value: str | None) -> str:
        resolved = (value or "").strip()
        if not resolved:
            raise ValueError(f"{name} must not be empty")
        return resolved

    @staticmethod
    def _normalize_channel_type(channel_type: str | None) -> str:
        resolved = (channel_type or "").strip()
        if resolved not in CHANNEL_TYPE_DEFS:
            raise ValueError(f"unsupported channel type: {resolved}")
        return resolved

    @staticmethod
    def _mask_secret(value: str) -> str:
        if not value:
            return ""
        if len(value) <= 8:
            return "*" * len(value)
        return value[:4] + "*" * (len(value) - 8) + value[-4:]

    @staticmethod
    def _is_masked_secret(value: object) -> bool:
        return isinstance(value, str) and "*" in value

    @staticmethod
    def _normalize_bool(value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    @staticmethod
    def _normalize_string_list(value: object, default: object = "") -> list[str]:
        if value in (None, ""):
            return list(default) if isinstance(default, list) else []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",")]
        if isinstance(value, (list, tuple)):
            return [str(item).strip() for item in value]
        return [str(value).strip()]

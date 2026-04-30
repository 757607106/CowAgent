from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from cow_platform.runtime.namespaces import (
    build_namespace,
    build_session_temp_path,
    build_workspace_path,
)


def _ensure_non_empty(name: str, value: str) -> None:
    if not str(value).strip():
        raise ValueError(f"{name} must not be empty")


@dataclass(frozen=True, slots=True)
class PolicySnapshot:
    """Resolved runtime policy after tenant/agent/channel rules are merged."""

    model: str = ""
    tool_whitelist: tuple[str, ...] = ()
    channel_rules: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def empty(cls) -> "PolicySnapshot":
        return cls()


@dataclass(frozen=True, slots=True)
class AgentDefinition:
    """Agent resource used by the platform layer."""

    tenant_id: str
    agent_id: str
    name: str
    version: int = 1
    model: str = ""
    model_config_id: str = ""
    system_prompt: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    tools: tuple[str, ...] = ()
    skills: tuple[str, ...] = ()
    knowledge_enabled: bool = False
    mcp_servers: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        _ensure_non_empty("tenant_id", self.tenant_id)
        _ensure_non_empty("agent_id", self.agent_id)
        _ensure_non_empty("name", self.name)


@dataclass(frozen=True, slots=True)
class TenantMcpServerDefinition:
    """Tenant-scoped MCP server configuration."""

    tenant_id: str
    name: str
    command: str
    args: tuple[str, ...] = ()
    env: Mapping[str, str] = field(default_factory=dict)
    enabled: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ensure_non_empty("tenant_id", self.tenant_id)
        _ensure_non_empty("name", self.name)
        _ensure_non_empty("command", self.command)


@dataclass(frozen=True, slots=True)
class TenantDefinition:
    """租户资源定义。"""

    tenant_id: str
    name: str
    status: str = "active"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ensure_non_empty("tenant_id", self.tenant_id)
        _ensure_non_empty("name", self.name)
        _ensure_non_empty("status", self.status)


@dataclass(frozen=True, slots=True)
class TenantUserDefinition:
    """租户用户资源定义。"""

    tenant_id: str
    user_id: str
    name: str = ""
    role: str = "member"
    status: str = "active"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ensure_non_empty("tenant_id", self.tenant_id)
        _ensure_non_empty("user_id", self.user_id)
        _ensure_non_empty("role", self.role)
        _ensure_non_empty("status", self.status)


@dataclass(frozen=True, slots=True)
class PlatformUserDefinition:
    """平台级用户定义。"""

    user_id: str
    name: str = ""
    role: str = "platform_super_admin"
    status: str = "active"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ensure_non_empty("user_id", self.user_id)
        _ensure_non_empty("role", self.role)
        _ensure_non_empty("status", self.status)


@dataclass(frozen=True, slots=True)
class ModelConfigDefinition:
    """平台或租户可用的模型接入配置。"""

    model_config_id: str
    scope: str
    tenant_id: str
    provider: str
    model_name: str
    display_name: str = ""
    api_key: str = ""
    api_base: str = ""
    enabled: bool = True
    is_public: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_by: str = ""

    def __post_init__(self) -> None:
        _ensure_non_empty("model_config_id", self.model_config_id)
        _ensure_non_empty("scope", self.scope)
        _ensure_non_empty("provider", self.provider)
        _ensure_non_empty("model_name", self.model_name)
        if self.scope == "tenant":
            _ensure_non_empty("tenant_id", self.tenant_id)


@dataclass(frozen=True, slots=True)
class CapabilityConfigDefinition:
    """平台或租户可用的独立能力接入配置。"""

    capability_config_id: str
    scope: str
    tenant_id: str
    capability: str
    provider: str
    model_name: str
    display_name: str = ""
    api_key: str = ""
    api_base: str = ""
    enabled: bool = True
    is_public: bool = True
    is_default: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_by: str = ""

    def __post_init__(self) -> None:
        _ensure_non_empty("capability_config_id", self.capability_config_id)
        _ensure_non_empty("scope", self.scope)
        _ensure_non_empty("capability", self.capability)
        _ensure_non_empty("provider", self.provider)
        _ensure_non_empty("model_name", self.model_name)
        if self.scope == "tenant":
            _ensure_non_empty("tenant_id", self.tenant_id)


@dataclass(frozen=True, slots=True)
class TenantUserIdentityDefinition:
    """租户用户与外部渠道身份的映射定义。"""

    tenant_id: str
    user_id: str
    channel_type: str
    external_user_id: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ensure_non_empty("tenant_id", self.tenant_id)
        _ensure_non_empty("user_id", self.user_id)
        _ensure_non_empty("channel_type", self.channel_type)
        _ensure_non_empty("external_user_id", self.external_user_id)


@dataclass(frozen=True, slots=True)
class ChannelBindingDefinition:
    """渠道绑定定义。"""

    tenant_id: str
    binding_id: str
    name: str
    channel_type: str
    agent_id: str
    channel_config_id: str = ""
    version: int = 1
    enabled: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ensure_non_empty("tenant_id", self.tenant_id)
        _ensure_non_empty("binding_id", self.binding_id)
        _ensure_non_empty("name", self.name)
        _ensure_non_empty("channel_type", self.channel_type)
        _ensure_non_empty("agent_id", self.agent_id)


@dataclass(frozen=True, slots=True)
class ChannelConfigDefinition:
    """租户级渠道接入配置。"""

    tenant_id: str
    channel_config_id: str
    name: str
    channel_type: str
    config: Mapping[str, Any] = field(default_factory=dict)
    enabled: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_by: str = ""

    def __post_init__(self) -> None:
        _ensure_non_empty("tenant_id", self.tenant_id)
        _ensure_non_empty("channel_config_id", self.channel_config_id)
        _ensure_non_empty("name", self.name)
        _ensure_non_empty("channel_type", self.channel_type)


@dataclass(frozen=True, slots=True)
class PricingDefinition:
    """模型定价定义。"""

    model: str
    input_price_per_million: float = 0.0
    output_price_per_million: float = 0.0
    currency: str = "CNY"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ensure_non_empty("model", self.model)
        _ensure_non_empty("currency", self.currency)


@dataclass(frozen=True, slots=True)
class QuotaDefinition:
    """平台日配额定义。"""

    scope_type: str
    tenant_id: str
    agent_id: str = ""
    max_requests_per_day: int = 0
    max_tokens_per_day: int = 0
    enabled: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ensure_non_empty("scope_type", self.scope_type)
        _ensure_non_empty("tenant_id", self.tenant_id)
        if self.scope_type == "agent":
            _ensure_non_empty("agent_id", self.agent_id)


@dataclass(frozen=True, slots=True)
class UsageRecord:
    """平台 usage 台账记录。"""

    event_id: str
    request_id: str
    tenant_id: str
    agent_id: str
    binding_id: str = ""
    session_id: str = ""
    channel_type: str = ""
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    token_source: str = "estimated"
    request_count: int = 1
    tool_call_count: int = 0
    mcp_call_count: int = 0
    tool_error_count: int = 0
    tool_execution_time_ms: int = 0
    estimated_cost: float = 0.0
    created_at: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in ("event_id", "request_id", "tenant_id", "agent_id", "created_at"):
            _ensure_non_empty(field_name, getattr(self, field_name))


@dataclass(frozen=True, slots=True)
class JobDefinition:
    """异步任务定义。"""

    job_id: str
    job_type: str
    tenant_id: str
    agent_id: str = ""
    status: str = "pending"
    payload: Mapping[str, Any] = field(default_factory=dict)
    result: Mapping[str, Any] = field(default_factory=dict)
    error_message: str = ""
    attempts: int = 0
    created_at: str = ""
    updated_at: str = ""
    started_at: str = ""
    completed_at: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in ("job_id", "job_type", "tenant_id", "status", "created_at", "updated_at"):
            _ensure_non_empty(field_name, getattr(self, field_name))


@dataclass(frozen=True, slots=True)
class AuditLogRecord:
    """平台审计日志记录。"""

    audit_id: str
    action: str
    resource_type: str
    resource_id: str
    status: str
    tenant_id: str = ""
    agent_id: str = ""
    actor: str = "system"
    created_at: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in ("audit_id", "action", "resource_type", "resource_id", "status", "created_at"):
            _ensure_non_empty(field_name, getattr(self, field_name))


@dataclass(frozen=True, slots=True)
class SessionState:
    """Minimal conversation state handle kept by the platform layer."""

    tenant_id: str
    agent_id: str
    user_id: str
    session_id: str
    status: str = "active"
    turn_count: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in ("tenant_id", "agent_id", "user_id", "session_id"):
            _ensure_non_empty(field_name, getattr(self, field_name))


@dataclass(frozen=True, slots=True)
class RuntimeContext:
    """Per-request runtime envelope for all future platform-side logic."""

    request_id: str
    tenant_id: str
    user_id: str
    agent_id: str
    session_id: str
    channel_type: str
    channel_user_id: str
    workspace_root: Path = Path("/data/workspaces")
    temp_root: Path = Path("/data/tmp")
    policy_snapshot: PolicySnapshot = field(default_factory=PolicySnapshot.empty)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in (
            "request_id",
            "tenant_id",
            "user_id",
            "agent_id",
            "session_id",
            "channel_type",
            "channel_user_id",
        ):
            _ensure_non_empty(field_name, getattr(self, field_name))

    @property
    def memory_namespace(self) -> str:
        return build_namespace(self.tenant_id, self.agent_id, "memory")

    @property
    def knowledge_namespace(self) -> str:
        return build_namespace(self.tenant_id, self.agent_id, "knowledge")

    @property
    def cache_namespace(self) -> str:
        return build_namespace(self.tenant_id, self.agent_id, "cache")

    @property
    def workspace_path(self) -> Path:
        return build_workspace_path(self.workspace_root, self.tenant_id, self.agent_id)

    @property
    def session_temp_path(self) -> Path:
        return build_session_temp_path(
            self.temp_root,
            self.tenant_id,
            self.agent_id,
            self.session_id,
        )

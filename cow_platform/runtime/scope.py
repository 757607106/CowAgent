from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

from cow_platform.domain.models import AgentDefinition, RuntimeContext


# 当前请求的运行时上下文
_runtime_context_var: ContextVar[RuntimeContext | None] = ContextVar(
    "cow_platform_runtime_context",
    default=None,
)

# 当前命中的 Agent 定义
_agent_definition_var: ContextVar[AgentDefinition | None] = ContextVar(
    "cow_platform_agent_definition",
    default=None,
)

_config_overrides_var: ContextVar[dict[str, object] | None] = ContextVar(
    "cow_platform_config_overrides",
    default=None,
)


def get_current_runtime_context() -> RuntimeContext | None:
    """获取当前协程里的运行时上下文。"""
    return _runtime_context_var.get()


def get_current_agent_definition() -> AgentDefinition | None:
    """获取当前协程里的 Agent 定义。"""
    return _agent_definition_var.get()


def get_current_model_name() -> str | None:
    """获取当前 Agent 绑定的模型名。"""
    runtime_context = get_current_runtime_context()
    if runtime_context is not None:
        model_config = runtime_context.metadata.get("model_config") if runtime_context.metadata else None
        if isinstance(model_config, dict) and model_config.get("model_name"):
            return str(model_config["model_name"])
    agent_definition = get_current_agent_definition()
    if agent_definition and agent_definition.model:
        return agent_definition.model
    return None


def get_current_model_config_id() -> str:
    """获取当前 Agent 运行时命中的模型配置 ID。"""
    runtime_context = get_current_runtime_context()
    if runtime_context is not None:
        model_config = runtime_context.metadata.get("model_config") if runtime_context.metadata else None
        if isinstance(model_config, dict):
            return str(model_config.get("model_config_id", "") or "")
    agent_definition = get_current_agent_definition()
    return agent_definition.model_config_id if agent_definition else ""


def get_current_config_overrides() -> dict[str, object]:
    """获取当前请求对全局配置的覆盖值。"""
    return dict(_config_overrides_var.get() or {})


@contextmanager
def activate_config_overrides(overrides: dict[str, object] | None) -> Iterator[None]:
    """Temporarily override conf().get values without requiring an agent scope."""
    token = _config_overrides_var.set(dict(overrides or {}))
    try:
        yield
    finally:
        _config_overrides_var.reset(token)


@contextmanager
def activate_runtime_scope(
    runtime_context: RuntimeContext,
    agent_definition: AgentDefinition,
) -> Iterator[None]:
    """在一个临时作用域里激活平台运行时信息。"""
    runtime_token = _runtime_context_var.set(runtime_context)
    agent_token = _agent_definition_var.set(agent_definition)
    overrides = runtime_context.metadata.get("config_overrides", {}) if runtime_context.metadata else {}
    config_token = _config_overrides_var.set(dict(overrides) if isinstance(overrides, dict) else {})
    try:
        yield
    finally:
        _config_overrides_var.reset(config_token)
        _runtime_context_var.reset(runtime_token)
        _agent_definition_var.reset(agent_token)

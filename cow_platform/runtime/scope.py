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


def get_current_runtime_context() -> RuntimeContext | None:
    """获取当前协程里的运行时上下文。"""
    return _runtime_context_var.get()


def get_current_agent_definition() -> AgentDefinition | None:
    """获取当前协程里的 Agent 定义。"""
    return _agent_definition_var.get()


def get_current_model_name() -> str | None:
    """获取当前 Agent 绑定的模型名。"""
    agent_definition = get_current_agent_definition()
    if agent_definition and agent_definition.model:
        return agent_definition.model
    return None


@contextmanager
def activate_runtime_scope(
    runtime_context: RuntimeContext,
    agent_definition: AgentDefinition,
) -> Iterator[None]:
    """在一个临时作用域里激活平台运行时信息。"""
    runtime_token = _runtime_context_var.set(runtime_context)
    agent_token = _agent_definition_var.set(agent_definition)
    try:
        yield
    finally:
        _runtime_context_var.reset(runtime_token)
        _agent_definition_var.reset(agent_token)

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator
import uuid

from bridge.context import Context

from cow_platform.domain.models import AgentDefinition, RuntimeContext
from cow_platform.runtime.namespaces import build_namespace
from cow_platform.runtime.scope import activate_runtime_scope
from cow_platform.services.agent_service import AgentService, DEFAULT_TENANT_ID
from cow_platform.services.binding_service import ChannelBindingService


@dataclass(frozen=True, slots=True)
class ResolvedAgentRuntime:
    """一次请求解析出来的 Agent 运行时信息。"""

    agent_definition: AgentDefinition
    runtime_context: RuntimeContext
    external_session_id: str
    cache_session_key: str

    @contextmanager
    def activate(self) -> Iterator[None]:
        with activate_runtime_scope(self.runtime_context, self.agent_definition):
            yield


class CowAgentRuntimeAdapter:
    """把平台侧 Agent 定义适配到现有 CowAgent 运行时。"""

    def __init__(
        self,
        agent_service: AgentService | None = None,
        binding_service: ChannelBindingService | None = None,
    ):
        self.agent_service = agent_service or AgentService()
        self.binding_service = binding_service or ChannelBindingService(agent_service=self.agent_service)

    def resolve_from_context(self, context: Context | None) -> ResolvedAgentRuntime | None:
        if context is None:
            return None

        tenant_id = context.get("tenant_id", DEFAULT_TENANT_ID) or DEFAULT_TENANT_ID
        agent_id = context.get("agent_id")
        binding_id = str(context.get("binding_id", "") or "").strip()
        resolved_binding = None

        if binding_id:
            resolved_binding = self.binding_service.resolve_binding(
                binding_id=binding_id,
                tenant_id=str(context.get("tenant_id", "") or "").strip(),
            )
            tenant_id = resolved_binding.tenant_id
            agent_id = resolved_binding.agent_id

        if not agent_id:
            return None

        session_id = context.get("session_id")
        if not session_id:
            return None

        agent_definition = self.agent_service.resolve_agent(tenant_id=tenant_id, agent_id=agent_id)
        workspace_root = self.agent_service.repository.get_workspace_path(
            tenant_id,
            agent_definition.agent_id,
        ).parent.parent

        runtime_context = RuntimeContext(
            request_id=context.get("request_id", "") or f"req_{uuid.uuid4().hex}",
            tenant_id=tenant_id,
            user_id=context.get("receiver", session_id),
            agent_id=agent_definition.agent_id,
            session_id=session_id,
            channel_type=context.get("channel_type", "") or getattr(resolved_binding, "channel_type", "") or "",
            channel_user_id=context.get("receiver", session_id),
            workspace_root=workspace_root,
            metadata={
                "agent_name": agent_definition.name,
                "binding_id": getattr(resolved_binding, "binding_id", ""),
            },
        )

        return ResolvedAgentRuntime(
            agent_definition=agent_definition,
            runtime_context=runtime_context,
            external_session_id=session_id,
            cache_session_key=self.build_cache_session_key(tenant_id, agent_definition.agent_id, session_id),
        )

    @staticmethod
    def build_cache_session_key(tenant_id: str, agent_id: str, session_id: str) -> str:
        return build_namespace(tenant_id, agent_id, session_id)

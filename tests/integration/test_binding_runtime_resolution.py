from pathlib import Path

import pytest

from agent.memory import get_conversation_store
from agent.memory.conversation_store import reset_conversation_store_cache
from bridge.context import Context, ContextType
from config import conf
from cow_platform.adapters.cowagent_runtime_adapter import CowAgentRuntimeAdapter
from cow_platform.repositories.session_repository import SessionRepository
from cow_platform.services.agent_service import AgentService
from cow_platform.services.binding_service import ChannelBindingService
from cow_platform.services.tenant_service import TenantService


def _build_binding_context(binding_id: str, session_id: str = "shared-session") -> Context:
    context = Context(ContextType.TEXT, "你好", kwargs={})
    context["request_id"] = f"req-{binding_id}-{session_id}"
    context["session_id"] = session_id
    context["receiver"] = "web-user-1"
    context["channel_type"] = "web"
    context["binding_id"] = binding_id
    return context


@pytest.mark.integration
def test_binding_runtime_resolution_isolates_tenants(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))
    monkeypatch.setitem(conf(), "model", "legacy-model")

    reset_conversation_store_cache()
    tenant_service = TenantService()
    agent_service = AgentService()
    binding_service = ChannelBindingService(
        tenant_service=tenant_service,
        agent_service=agent_service,
    )

    tenant_service.create_tenant(tenant_id="team-a", name="团队 A")
    tenant_service.create_tenant(tenant_id="team-b", name="团队 B")
    agent_service.create_agent(
        tenant_id="team-a",
        agent_id="assistant",
        name="团队 A 助手",
        model="model-a",
        system_prompt="你服务团队 A。",
    )
    agent_service.create_agent(
        tenant_id="team-b",
        agent_id="assistant",
        name="团队 B 助手",
        model="model-b",
        system_prompt="你服务团队 B。",
    )
    binding_service.create_binding(
        tenant_id="team-a",
        binding_id="team-a-web",
        name="团队 A Web",
        channel_type="web",
        agent_id="assistant",
    )
    binding_service.create_binding(
        tenant_id="team-b",
        binding_id="team-b-web",
        name="团队 B Web",
        channel_type="web",
        agent_id="assistant",
    )

    adapter = CowAgentRuntimeAdapter(
        agent_service=agent_service,
        binding_service=binding_service,
    )
    runtime_a = adapter.resolve_from_context(_build_binding_context("team-a-web"))
    runtime_b = adapter.resolve_from_context(_build_binding_context("team-b-web"))

    assert runtime_a is not None
    assert runtime_b is not None
    assert runtime_a.runtime_context.tenant_id == "team-a"
    assert runtime_b.runtime_context.tenant_id == "team-b"
    assert runtime_a.cache_session_key != runtime_b.cache_session_key

    with runtime_a.activate():
        get_conversation_store().append_messages(
            runtime_a.external_session_id,
            [{"role": "user", "content": [{"type": "text", "text": "来自租户 A 的消息"}]}],
            channel_type="web",
        )

    with runtime_b.activate():
        get_conversation_store().append_messages(
            runtime_b.external_session_id,
            [{"role": "user", "content": [{"type": "text", "text": "来自租户 B 的消息"}]}],
            channel_type="web",
        )

    repository = SessionRepository(agent_service.repository)
    history_a = repository.load_history_page("team-a", "assistant", "shared-session", page=1, page_size=20)
    history_b = repository.load_history_page("team-b", "assistant", "shared-session", page=1, page_size=20)

    assert history_a["messages"][0]["content"] == "来自租户 A 的消息"
    assert history_b["messages"][0]["content"] == "来自租户 B 的消息"
    assert runtime_a.runtime_context.workspace_path == Path(tmp_path / "legacy/workspaces/team-a/assistant")
    assert runtime_b.runtime_context.workspace_path == Path(tmp_path / "legacy/workspaces/team-b/assistant")

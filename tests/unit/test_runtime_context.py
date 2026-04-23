from pathlib import Path

import pytest

from cow_platform.domain.models import AgentDefinition, PolicySnapshot, RuntimeContext, SessionState


def test_runtime_context_builds_expected_namespaces_and_paths(tmp_path: Path) -> None:
    context = RuntimeContext(
        request_id="req-001",
        tenant_id="tenant-a",
        user_id="user-1",
        agent_id="agent-main",
        session_id="sess-9",
        channel_type="web",
        channel_user_id="web-user-1",
        workspace_root=tmp_path / "workspaces",
        temp_root=tmp_path / "tmp",
    )

    assert context.memory_namespace == "tenant-a:agent-main:memory"
    assert context.knowledge_namespace == "tenant-a:agent-main:knowledge"
    assert context.cache_namespace == "tenant-a:agent-main:cache"
    assert context.workspace_path == tmp_path / "workspaces" / "tenant-a" / "agent-main"
    assert context.session_temp_path == tmp_path / "tmp" / "tenant-a" / "agent-main" / "sess-9"


def test_policy_agent_and_session_models_are_constructible() -> None:
    policy = PolicySnapshot(model="qwen-max", tool_whitelist=("search",))
    agent = AgentDefinition(
        tenant_id="tenant-a",
        agent_id="agent-main",
        name="Main Agent",
        version=2,
        model="qwen-max",
        system_prompt="You are helpful.",
    )
    session = SessionState(
        tenant_id="tenant-a",
        agent_id="agent-main",
        user_id="user-1",
        session_id="sess-9",
        turn_count=3,
    )

    assert policy.model == "qwen-max"
    assert agent.version == 2
    assert session.turn_count == 3


def test_runtime_context_requires_non_empty_identifiers() -> None:
    with pytest.raises(ValueError, match="tenant_id"):
        RuntimeContext(
            request_id="req-001",
            tenant_id="",
            user_id="user-1",
            agent_id="agent-main",
            session_id="sess-9",
            channel_type="web",
            channel_user_id="web-user-1",
        )

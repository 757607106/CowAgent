from __future__ import annotations

import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from agent.prompt.builder import PromptBuilder
from agent.prompt.workspace import ensure_workspace
from agent.protocol.agent import Agent
from bridge.agent_initializer import AgentInitializer
from config import conf
from cow_platform.domain.models import AgentDefinition, RuntimeContext


class _DummyTool:
    def __init__(self, name: str):
        self.name = name
        self.description = f"{name} tool"
        self.params = {"type": "object", "properties": {}}
        self.config = None
        self.cwd = None


class _FakeToolManager:
    def __init__(self):
        self.tool_classes = {
            "read": object(),
            "write": object(),
        }

    def load_tools(self):
        return None

    def create_tool(self, tool_name: str):
        return _DummyTool(tool_name)


class _FakeSkillManager:
    def __init__(self, custom_dir: str | None = None):
        self.custom_dir = custom_dir
        self.skills_config = {
            "knowledge-wiki": {},
            "skill-creator": {},
        }
        self.disabled: list[str] = []

    def set_skill_enabled(self, skill_name: str, enabled: bool):
        if not enabled:
            self.disabled.append(skill_name)


def _make_initializer() -> AgentInitializer:
    bridge = object()
    agent_bridge = SimpleNamespace(scheduler_initialized=False)
    return AgentInitializer(bridge=bridge, agent_bridge=agent_bridge)


def test_agent_rebuild_keeps_custom_system_prompt(tmp_path: Path):
    workspace_dir = tmp_path / "workspace"
    ensure_workspace(str(workspace_dir), knowledge_enabled=False)

    agent = Agent(
        system_prompt="cached prompt",
        workspace_dir=str(workspace_dir),
        tools=[],
        enable_skills=False,
        custom_system_prompt="你是一名智能客服，负责解决用户的问题",
        knowledge_enabled=False,
    )

    rebuilt = agent.get_full_system_prompt()

    assert rebuilt.startswith("你是一名智能客服，负责解决用户的问题")
    assert rebuilt.count("你是一名智能客服，负责解决用户的问题") == 1
    assert "## 📂 工作空间" in rebuilt


def test_prompt_builder_respects_explicit_knowledge_toggle(tmp_path: Path):
    workspace_dir = tmp_path / "workspace"
    ensure_workspace(str(workspace_dir), knowledge_enabled=True)
    knowledge_index = workspace_dir / "knowledge" / "index.md"
    knowledge_index.write_text("[示例](notes/example.md) - 示例条目", encoding="utf-8")

    builder = PromptBuilder(workspace_dir=str(workspace_dir), language="zh")

    prompt_disabled = builder.build(
        tools=[],
        context_files=[],
        knowledge_enabled=False,
    )
    prompt_enabled = builder.build(
        tools=[],
        context_files=[],
        knowledge_enabled=True,
    )

    assert "## 📚 知识系统" not in prompt_disabled
    assert "## 📚 知识系统" in prompt_enabled


def test_empty_tool_allowlist_disables_all_tools(monkeypatch, tmp_path: Path):
    initializer = _make_initializer()
    monkeypatch.setattr("bridge.agent_initializer.ToolManager", _FakeToolManager)

    agent_definition = AgentDefinition(
        tenant_id="default",
        agent_id="agent-x",
        name="Agent X",
        tools=(),
        skills=(),
        knowledge_enabled=False,
    )

    memory_tools = [_DummyTool("memory_search"), _DummyTool("memory_get")]
    loaded = initializer._load_tools(
        workspace_root=str(tmp_path),
        memory_manager=None,
        memory_tools=memory_tools,
        session_id="session-1",
        agent_definition=agent_definition,
    )

    assert loaded == []


def test_memory_tools_also_follow_tool_allowlist(monkeypatch, tmp_path: Path):
    initializer = _make_initializer()
    monkeypatch.setattr("bridge.agent_initializer.ToolManager", _FakeToolManager)

    agent_definition = AgentDefinition(
        tenant_id="default",
        agent_id="agent-y",
        name="Agent Y",
        tools=("read", "memory_get"),
        skills=(),
        knowledge_enabled=False,
    )

    memory_tools = [_DummyTool("memory_search"), _DummyTool("memory_get")]
    loaded = initializer._load_tools(
        workspace_root=str(tmp_path),
        memory_manager=None,
        memory_tools=memory_tools,
        session_id="session-1",
        agent_definition=agent_definition,
    )

    assert [tool.name for tool in loaded] == ["read", "memory_get"]


def test_empty_skill_allowlist_disables_all_skills(monkeypatch, tmp_path: Path):
    initializer = _make_initializer()
    monkeypatch.setattr("agent.skills.SkillManager", _FakeSkillManager)

    agent_definition = AgentDefinition(
        tenant_id="default",
        agent_id="agent-z",
        name="Agent Z",
        tools=(),
        skills=(),
        knowledge_enabled=False,
    )

    manager = initializer._initialize_skill_manager(
        workspace_root=str(tmp_path),
        session_id="session-1",
        agent_definition=agent_definition,
    )

    assert isinstance(manager, _FakeSkillManager)
    assert set(manager.disabled) == {"knowledge-wiki", "skill-creator"}


def test_initializer_legacy_default_respects_explicit_knowledge_disabled(monkeypatch, tmp_path: Path):
    initializer = _make_initializer()

    monkeypatch.setitem(conf(), "knowledge", True)
    monkeypatch.setattr(initializer, "_migrate_config_to_env", lambda workspace_root: None)
    monkeypatch.setattr(initializer, "_load_env_file", lambda: None)
    monkeypatch.setattr(initializer, "_setup_memory_system", lambda workspace_root, session_id=None: (None, []))
    monkeypatch.setattr(initializer, "_load_tools", lambda workspace_root, memory_manager, memory_tools, session_id=None, agent_definition=None: [])
    monkeypatch.setattr(initializer, "_setup_mcp_tools", lambda tools, session_id=None, agent_definition=None: None)
    monkeypatch.setattr(initializer, "_initialize_scheduler", lambda tools, session_id=None: None)
    monkeypatch.setattr(initializer, "_initialize_skill_manager", lambda workspace_root, session_id=None, agent_definition=None: None)
    monkeypatch.setattr(initializer, "_restore_conversation_history", lambda agent, session_id, workspace_root: None)
    monkeypatch.setattr(initializer, "_start_daily_flush_timer", lambda: None)

    class _DummyCreatedAgent:
        def __init__(self):
            self.messages_lock = threading.Lock()
            self.messages = []
            self.model = None

    initializer.agent_bridge.create_agent = lambda **kwargs: _DummyCreatedAgent()

    runtime_context = RuntimeContext(
        request_id="req-1",
        tenant_id="default",
        user_id="u-1",
        agent_id="default",
        session_id="s-1",
        channel_type="web",
        channel_user_id="u-1",
        workspace_root=tmp_path / "workspaces",
    )
    agent_definition = AgentDefinition(
        tenant_id="default",
        agent_id="default",
        name="默认助手",
        model="qwen-max",
        system_prompt="你是一名智能客服",
        tools=(),
        skills=(),
        knowledge_enabled=False,
        metadata={"source": "legacy-default"},
    )

    monkeypatch.setattr("cow_platform.runtime.scope.get_current_runtime_context", lambda: runtime_context)
    monkeypatch.setattr("cow_platform.runtime.scope.get_current_agent_definition", lambda: agent_definition)

    initializer.initialize_agent(session_id="s-1")

    assert not runtime_context.workspace_path.joinpath("knowledge").exists()


def test_agent_bridge_can_clear_all_sessions_for_target_agent():
    from bridge.agent_bridge import AgentBridge

    with patch("bridge.agent_bridge.AgentInitializer"), patch("bridge.agent_bridge.CowAgentRuntimeAdapter"):
        bridge = MagicMock()
        agent_bridge = AgentBridge(bridge)

    agent_bridge.agents = {
        "default:agent-a:s1": object(),
        "default:agent-a:s2": object(),
        "default:agent-b:s1": object(),
        "legacy-session": object(),
    }

    agent_bridge.clear_agent_sessions(tenant_id="default", agent_id="agent-a")

    assert "default:agent-a:s1" not in agent_bridge.agents
    assert "default:agent-a:s2" not in agent_bridge.agents
    assert "default:agent-b:s1" in agent_bridge.agents
    assert "legacy-session" in agent_bridge.agents

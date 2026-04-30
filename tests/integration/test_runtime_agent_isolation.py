import threading
from pathlib import Path
from types import MethodType

import pytest

from agent.memory import get_conversation_store
from agent.memory.conversation_store import reset_conversation_store_cache
from agent.memory.service import MemoryService
from agent.knowledge.service import KnowledgeService
from bridge.agent_bridge import AgentLLMModel
from bridge.bridge import Bridge
from bridge.context import Context, ContextType
from config import conf
from cow_platform.adapters.cowagent_runtime_adapter import CowAgentRuntimeAdapter
from cow_platform.repositories.session_repository import SessionRepository
from cow_platform.services.agent_service import AgentService
from cow_platform.services.model_config_service import ModelConfigService


class _DummyAgent:
    def __init__(self, bridge, system_prompt: str, workspace_dir: str, tools: list):
        self.system_prompt = system_prompt
        self.workspace_dir = workspace_dir
        self.tools = tools
        self.model = AgentLLMModel(bridge)
        self.messages_lock = threading.Lock()
        self.messages = []

    def get_full_system_prompt(self) -> str:
        return self.system_prompt

    def _execute_post_process_tools(self) -> None:
        return None


def _build_context(agent_id: str, session_id: str = "shared-session") -> Context:
    context = Context(ContextType.TEXT, "你好", kwargs={})
    context["request_id"] = f"req-{agent_id}-{session_id}"
    context["session_id"] = session_id
    context["receiver"] = "web-user-1"
    context["channel_type"] = "web"
    context["tenant_id"] = "default"
    context["agent_id"] = agent_id
    return context


@pytest.mark.integration
def test_runtime_adapter_and_session_store_isolate_agents(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))
    monkeypatch.setitem(conf(), "model", "legacy-model")
    monkeypatch.setitem(conf(), "knowledge", True)

    reset_conversation_store_cache()
    bridge = Bridge()
    bridge.reset_bot()
    agent_bridge = bridge.get_agent_bridge()

    service = AgentService()
    service.ensure_default_agent()
    model_service = ModelConfigService()
    model_a_id = model_service.create_platform_model(
        provider="openai",
        model_name="model-a",
        api_key="test-key-a",
    )["model_config_id"]
    model_b_id = model_service.create_platform_model(
        provider="openai",
        model_name="model-b",
        api_key="test-key-b",
    )["model_config_id"]
    service.create_agent(
        agent_id="agent-a",
        name="助手A",
        model_config_id=model_a_id,
        system_prompt="你是助手A。",
        knowledge_enabled=True,
    )
    service.create_agent(
        agent_id="agent-b",
        name="助手B",
        model_config_id=model_b_id,
        system_prompt="你是助手B。",
        knowledge_enabled=True,
    )

    monkeypatch.setattr(agent_bridge.initializer, "_migrate_config_to_env", lambda workspace_root: None)
    monkeypatch.setattr(agent_bridge.initializer, "_load_env_file", lambda: None)
    monkeypatch.setattr(agent_bridge.initializer, "_load_tools", lambda workspace_root, memory_manager, memory_tools, session_id=None, agent_definition=None: list(memory_tools))
    monkeypatch.setattr(agent_bridge.initializer, "_initialize_scheduler", lambda tools, session_id=None: None)
    monkeypatch.setattr(agent_bridge.initializer, "_initialize_skill_manager", lambda workspace_root, session_id=None, agent_definition=None: None)

    def fake_create_agent(self, system_prompt: str, tools=None, **kwargs):
        return _DummyAgent(self.bridge, system_prompt, kwargs.get("workspace_dir", ""), tools or [])

    monkeypatch.setattr(agent_bridge, "create_agent", MethodType(fake_create_agent, agent_bridge))

    adapter = CowAgentRuntimeAdapter(service)
    runtime_a = adapter.resolve_from_context(_build_context("agent-a"))
    runtime_b = adapter.resolve_from_context(_build_context("agent-b"))

    assert runtime_a is not None
    assert runtime_b is not None
    assert runtime_a.cache_session_key != runtime_b.cache_session_key

    with runtime_a.activate():
        agent_a = agent_bridge.get_agent(session_id=runtime_a.external_session_id, cache_key=runtime_a.cache_session_key)
        get_conversation_store().append_messages(
            runtime_a.external_session_id,
            [{"role": "user", "content": [{"type": "text", "text": "来自A的消息"}]}],
            channel_type="web",
        )

    with runtime_b.activate():
        agent_b = agent_bridge.get_agent(session_id=runtime_b.external_session_id, cache_key=runtime_b.cache_session_key)
        get_conversation_store().append_messages(
            runtime_b.external_session_id,
            [{"role": "user", "content": [{"type": "text", "text": "来自B的消息"}]}],
            channel_type="web",
        )

    workspace_a = Path(agent_a.workspace_dir)
    workspace_b = Path(agent_b.workspace_dir)
    assert workspace_a != workspace_b
    assert workspace_a.joinpath("MEMORY.md").exists()
    assert workspace_b.joinpath("MEMORY.md").exists()
    assert workspace_a.joinpath("knowledge", "index.md").exists()
    assert workspace_b.joinpath("knowledge", "index.md").exists()
    assert "你是助手A。" in agent_a.system_prompt
    assert "你是助手B。" in agent_b.system_prompt

    with runtime_a.activate():
        assert agent_a.model.model == "model-a"
    with runtime_b.activate():
        assert agent_b.model.model == "model-b"

    repository = SessionRepository(service.repository)
    sessions_a = repository.list_sessions("default", "agent-a", channel_type="web", page=1, page_size=20)
    sessions_b = repository.list_sessions("default", "agent-b", channel_type="web", page=1, page_size=20)
    history_a = repository.load_history_page("default", "agent-a", "shared-session", page=1, page_size=20)
    history_b = repository.load_history_page("default", "agent-b", "shared-session", page=1, page_size=20)

    assert [item["session_id"] for item in sessions_a["sessions"]] == ["shared-session"]
    assert [item["session_id"] for item in sessions_b["sessions"]] == ["shared-session"]
    assert history_a["messages"][0]["content"] == "来自A的消息"
    assert history_b["messages"][0]["content"] == "来自B的消息"

    dream_a = workspace_a / "memory" / "dreams" / "2026-04-23.md"
    dream_b = workspace_b / "memory" / "dreams" / "2026-04-23.md"
    dream_a.parent.mkdir(parents=True, exist_ok=True)
    dream_b.parent.mkdir(parents=True, exist_ok=True)
    dream_a.write_text("A 的梦境", encoding="utf-8")
    dream_b.write_text("B 的梦境", encoding="utf-8")

    knowledge_a = workspace_a / "knowledge" / "notes" / "notes-a.md"
    knowledge_b = workspace_b / "knowledge" / "notes" / "notes-b.md"
    knowledge_a.parent.mkdir(parents=True, exist_ok=True)
    knowledge_b.parent.mkdir(parents=True, exist_ok=True)
    knowledge_a.write_text("# A\nA 专属知识", encoding="utf-8")
    knowledge_b.write_text("# B\nB 专属知识", encoding="utf-8")

    memory_service_a = MemoryService(str(workspace_a))
    memory_service_b = MemoryService(str(workspace_b))
    knowledge_service_a = KnowledgeService(str(workspace_a))
    knowledge_service_b = KnowledgeService(str(workspace_b))

    assert memory_service_a.get_content("2026-04-23.md", category="dream")["content"] == "A 的梦境"
    assert memory_service_b.get_content("2026-04-23.md", category="dream")["content"] == "B 的梦境"
    assert "notes-a.md" in {item["name"] for group in knowledge_service_a.list_tree()["tree"] for item in group["files"]}
    assert "notes-b.md" in {item["name"] for group in knowledge_service_b.list_tree()["tree"] for item in group["files"]}

import threading
from types import MethodType

import pytest

from bridge.agent_bridge import AgentLLMModel
from bridge.bridge import Bridge
from bridge.context import Context, ContextType
from bridge.reply import ReplyType
from config import conf
from cow_platform.services.agent_service import AgentService
from cow_platform.services.model_config_service import ModelConfigService


class _DummyQuotaAgent:
    def __init__(self, bridge, system_prompt: str, workspace_dir: str, tools: list):
        self.system_prompt = system_prompt
        self.workspace_dir = workspace_dir
        self.tools = tools
        self.model = AgentLLMModel(bridge)
        self.messages_lock = threading.Lock()
        self.messages = []
        self._last_run_new_messages = []

    def get_full_system_prompt(self) -> str:
        return self.system_prompt

    def _execute_post_process_tools(self) -> None:
        return None

    def run_stream(self, user_message: str, on_event=None, clear_history: bool = False, **kwargs) -> str:
        return f"已处理:{user_message}"


def _build_context(agent_id: str, session_id: str, request_id: str) -> Context:
    context = Context(ContextType.TEXT, "你好", kwargs={})
    context["request_id"] = request_id
    context["session_id"] = session_id
    context["receiver"] = "web-user-1"
    context["channel_type"] = "web"
    context["tenant_id"] = "default"
    context["agent_id"] = agent_id
    return context


@pytest.mark.integration
def test_agent_bridge_enforces_quota_and_records_usage(tmp_path, monkeypatch) -> None:
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))
    monkeypatch.setitem(conf(), "model", "legacy-model")

    bridge = Bridge()
    bridge.reset_bot()
    agent_bridge = bridge.get_agent_bridge()

    service = AgentService()
    service.ensure_default_agent()
    model_config_id = ModelConfigService().create_platform_model(
        provider="dashscope",
        model_name="qwen-plus",
        api_key="test-dashscope-key",
    )["model_config_id"]
    service.create_agent(
        agent_id="writer",
        name="写作助手",
        model_config_id=model_config_id,
        system_prompt="你擅长写作。",
    )

    agent_bridge.pricing_service.upsert_pricing(
        model="qwen-plus",
        input_price_per_million=2.0,
        output_price_per_million=8.0,
    )
    agent_bridge.quota_service.upsert_quota(
        scope_type="agent",
        tenant_id="default",
        agent_id="writer",
        max_requests_per_day=1,
        max_tokens_per_day=10000,
    )

    monkeypatch.setattr(agent_bridge.initializer, "_migrate_config_to_env", lambda workspace_root: None)
    monkeypatch.setattr(agent_bridge.initializer, "_load_env_file", lambda: None)
    monkeypatch.setattr(agent_bridge.initializer, "_load_tools", lambda workspace_root, memory_manager, memory_tools, session_id=None, agent_definition=None: list(memory_tools))
    monkeypatch.setattr(agent_bridge.initializer, "_initialize_scheduler", lambda tools, session_id=None: None)
    monkeypatch.setattr(agent_bridge.initializer, "_initialize_skill_manager", lambda workspace_root, session_id=None, agent_definition=None: None)

    def fake_create_agent(self, system_prompt: str, tools=None, **kwargs):
        return _DummyQuotaAgent(self.bridge, system_prompt, kwargs.get("workspace_dir", ""), tools or [])

    monkeypatch.setattr(agent_bridge, "create_agent", MethodType(fake_create_agent, agent_bridge))

    reply_ok = agent_bridge.agent_reply(
        "请写一段产品介绍",
        _build_context("writer", "session-1", "req-bridge-1"),
    )
    reply_blocked = agent_bridge.agent_reply(
        "再写一段",
        _build_context("writer", "session-1", "req-bridge-2"),
    )
    summary = agent_bridge.usage_service.summarize_usage(
        tenant_id="default",
        agent_id="writer",
    )
    records = agent_bridge.usage_service.list_usage_records(
        tenant_id="default",
        agent_id="writer",
    )

    assert reply_ok.type == ReplyType.TEXT
    assert "已处理" in reply_ok.content
    assert reply_blocked.type == ReplyType.ERROR
    assert "已超过当日请求配额" in reply_blocked.content
    assert summary["request_count"] == 1
    assert summary["estimated_cost"] > 0
    assert records[0]["request_id"] == "req-bridge-1"

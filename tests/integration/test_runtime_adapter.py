import pytest

from bridge.context import Context, ContextType
from config import conf

from cow_platform.adapters.cowagent_runtime_adapter import CowAgentRuntimeAdapter
from cow_platform.services.agent_service import AgentService


@pytest.mark.integration
def test_runtime_adapter_returns_none_without_explicit_agent(tmp_path, monkeypatch) -> None:
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))
    adapter = CowAgentRuntimeAdapter(AgentService())
    context = Context(ContextType.TEXT, "hello", kwargs={})
    context["session_id"] = "sid-1"
    context["request_id"] = "req-1"
    context["receiver"] = "user-1"
    context["channel_type"] = "web"

    assert adapter.resolve_from_context(context) is None

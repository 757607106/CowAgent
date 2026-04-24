from pathlib import Path

import pytest

from config import conf

from cow_platform.repositories.agent_repository import AgentRepository, get_platform_workspace_root
from cow_platform.services.agent_service import AgentService


def test_agent_service_can_create_update_and_list_agents(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))
    monkeypatch.setitem(conf(), "model", "legacy-model")

    repository = AgentRepository()
    service = AgentService(repository)

    default_agent = service.ensure_default_agent()
    created = service.create_agent(
        agent_id="analyst",
        name="数据分析师",
        model="qwen-plus",
        system_prompt="你是数据分析师。",
    )
    updated = service.update_agent(
        "analyst",
        name="高级数据分析师",
        model="qwen-max",
        system_prompt="你是高级数据分析师。",
    )
    listed = service.list_agent_records()

    assert default_agent.agent_id == "default"
    assert created["agent_id"] == "analyst"
    assert updated["version"] == 2
    assert updated["name"] == "高级数据分析师"
    assert any(item["agent_id"] == "analyst" for item in listed)
    assert Path(updated["workspace_path"]) == get_platform_workspace_root() / "default" / "analyst"
    assert len(updated["versions"]) == 2


def test_agent_service_can_auto_generate_agent_id(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))
    monkeypatch.setitem(conf(), "model", "legacy-model")

    repository = AgentRepository()
    service = AgentService(repository)

    created = service.create_agent(
        name="自动编号",
        model="qwen-plus",
    )

    assert created["agent_id"].startswith("agt_")
    assert len(created["agent_id"]) == 12
    assert created["name"] == "自动编号"


def test_agent_service_rejects_default_agent_delete() -> None:
    service = AgentService(repository=object(), tenant_service=object())

    with pytest.raises(ValueError, match="default agent cannot be deleted"):
        service.delete_agent("default", tenant_id="any")

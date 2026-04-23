import pytest
from fastapi.testclient import TestClient

from config import conf

from cow_platform.api.app import create_app
from cow_platform.api.settings import PlatformSettings


@pytest.mark.integration
def test_platform_agent_api_supports_crud(tmp_path, monkeypatch) -> None:
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))
    monkeypatch.setitem(conf(), "model", "legacy-model")

    app = create_app(PlatformSettings(host="127.0.0.1", port=9911, mode="test"))
    client = TestClient(app, raise_server_exceptions=False)

    list_before = client.get("/api/platform/agents")
    create_resp = client.post(
        "/api/platform/agents",
        json={
            "agent_id": "writer",
            "name": "写作助手",
            "model": "qwen-plus",
            "system_prompt": "你擅长写作。",
        },
    )
    create_auto_resp = client.post(
        "/api/platform/agents",
        json={
            "name": "自动编号助手",
            "model": "qwen-plus",
        },
    )
    auto_agent_id = create_auto_resp.json()["agent"]["agent_id"]
    get_resp = client.get("/api/platform/agents/writer")
    get_auto_resp = client.get(f"/api/platform/agents/{auto_agent_id}")
    update_resp = client.put(
        "/api/platform/agents/writer",
        json={
            "name": "高级写作助手",
            "model": "qwen-max",
            "system_prompt": "你擅长结构化写作。",
        },
    )

    assert list_before.status_code == 200
    assert list_before.json()["status"] == "success"
    assert any(item["agent_id"] == "default" for item in list_before.json()["agents"])

    assert create_resp.status_code == 200
    assert create_resp.json()["agent"]["agent_id"] == "writer"
    assert create_resp.json()["agent"]["version"] == 1

    assert create_auto_resp.status_code == 200
    assert auto_agent_id.startswith("agt_")
    assert len(auto_agent_id) == 12

    assert get_resp.status_code == 200
    assert get_resp.json()["agent"]["name"] == "写作助手"

    assert get_auto_resp.status_code == 200
    assert get_auto_resp.json()["agent"]["name"] == "自动编号助手"

    assert update_resp.status_code == 200
    assert update_resp.json()["agent"]["version"] == 2
    assert update_resp.json()["agent"]["name"] == "高级写作助手"
    assert len(update_resp.json()["agent"]["versions"]) == 2


@pytest.mark.integration
def test_platform_agent_api_rejects_nonexistent_tenant(tmp_path, monkeypatch) -> None:
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))
    monkeypatch.setitem(conf(), "model", "legacy-model")

    app = create_app(PlatformSettings(host="127.0.0.1", port=9921, mode="test"))
    client = TestClient(app, raise_server_exceptions=False)

    create_resp = client.post(
        "/api/platform/agents",
        json={
            "tenant_id": "missing-tenant",
            "agent_id": "writer",
            "name": "写作助手",
        },
    )

    assert create_resp.status_code == 500


@pytest.mark.integration
def test_platform_agent_api_isolates_same_agent_id_across_tenants(tmp_path, monkeypatch) -> None:
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))
    monkeypatch.setitem(conf(), "model", "legacy-model")

    app = create_app(PlatformSettings(host="127.0.0.1", port=9922, mode="test"))
    client = TestClient(app, raise_server_exceptions=False)

    tenant_a = "tenant-a"
    tenant_b = "tenant-b"
    for tenant_id in (tenant_a, tenant_b):
        create_tenant_resp = client.post(
            "/api/platform/tenants",
            json={"tenant_id": tenant_id, "name": tenant_id},
        )
        assert create_tenant_resp.status_code == 200

    create_a = client.post(
        "/api/platform/agents",
        json={
            "tenant_id": tenant_a,
            "agent_id": "shared-agent",
            "name": "Shared Agent A",
            "model": "qwen-plus",
        },
    )
    create_b = client.post(
        "/api/platform/agents",
        json={
            "tenant_id": tenant_b,
            "agent_id": "shared-agent",
            "name": "Shared Agent B",
            "model": "qwen-plus",
        },
    )

    assert create_a.status_code == 200
    assert create_b.status_code == 200

    get_a = client.get("/api/platform/agents/shared-agent", params={"tenant_id": tenant_a})
    get_b = client.get("/api/platform/agents/shared-agent", params={"tenant_id": tenant_b})
    assert get_a.status_code == 200
    assert get_b.status_code == 200
    assert get_a.json()["agent"]["name"] == "Shared Agent A"
    assert get_b.json()["agent"]["name"] == "Shared Agent B"

    update_a = client.put(
        "/api/platform/agents/shared-agent",
        json={"tenant_id": tenant_a, "name": "Shared Agent A v2"},
    )
    assert update_a.status_code == 200
    assert update_a.json()["agent"]["name"] == "Shared Agent A v2"

    get_b_after = client.get("/api/platform/agents/shared-agent", params={"tenant_id": tenant_b})
    assert get_b_after.status_code == 200
    assert get_b_after.json()["agent"]["name"] == "Shared Agent B"

    delete_a = client.delete("/api/platform/agents/shared-agent", params={"tenant_id": tenant_a})
    assert delete_a.status_code == 200
    assert delete_a.json()["agent_id"] == "shared-agent"

    still_get_b = client.get("/api/platform/agents/shared-agent", params={"tenant_id": tenant_b})
    assert still_get_b.status_code == 200
    assert still_get_b.json()["agent"]["tenant_id"] == tenant_b


@pytest.mark.integration
def test_platform_agent_update_invalidates_runtime_cache(tmp_path, monkeypatch) -> None:
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))
    monkeypatch.setitem(conf(), "model", "legacy-model")

    cleared = []

    class _FakeAgentBridge:
        def clear_agent_sessions(self, tenant_id: str, agent_id: str):
            cleared.append((tenant_id, agent_id))

    class _FakeBridge:
        def get_agent_bridge(self):
            return _FakeAgentBridge()

    monkeypatch.setattr("bridge.bridge.Bridge", _FakeBridge)

    app = create_app(PlatformSettings(host="127.0.0.1", port=9931, mode="test"))
    client = TestClient(app, raise_server_exceptions=False)

    create_resp = client.post(
        "/api/platform/agents",
        json={
            "agent_id": "cache-target",
            "name": "缓存目标助手",
            "model": "qwen-plus",
            "system_prompt": "旧提示词",
        },
    )
    assert create_resp.status_code == 200

    update_resp = client.put(
        "/api/platform/agents/cache-target",
        json={
            "name": "缓存目标助手V2",
            "model": "qwen-max",
            "system_prompt": "新提示词",
        },
    )
    assert update_resp.status_code == 200
    assert ("default", "cache-target") in cleared

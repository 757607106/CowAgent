from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests

from tests.conftest import REPO_ROOT, find_free_port, wait_for_http


@pytest.mark.e2e
def test_web_console_platform_routes_work_in_real_process(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    port = find_free_port()
    base_url = f"http://127.0.0.1:{port}"
    binding_id = f"web-bind-{int(time.time())}"
    tenant_id = f"web-tenant-{int(time.time())}"
    tenant_id_2 = f"{tenant_id}-b"

    env = os.environ.copy()
    env.update(
        {
            "agent_workspace": str(workspace),
            "model": "qwen-plus",
            "agent": "true",
            "channel_type": "web",
            "web_port": str(port),
            "web_password": "",
            "web_tenant_auth": "false",
        }
    )

    process = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        chat_resp = wait_for_http(f"{base_url}/chat", timeout=40)
        assert chat_resp.status_code == 200
        assert "<div id=\"root\"></div>" in chat_resp.text

        list_agents_resp = requests.get(f"{base_url}/api/platform/agents", timeout=5)
        assert list_agents_resp.status_code == 200
        assert list_agents_resp.json()["status"] == "success"

        list_tenants_resp = requests.get(f"{base_url}/api/platform/tenants", timeout=5)
        assert list_tenants_resp.status_code == 200
        assert list_tenants_resp.json()["status"] == "success"

        create_tenant_resp = requests.post(
            f"{base_url}/api/platform/tenants",
            json={"tenant_id": tenant_id, "name": "Web Console Tenant"},
            timeout=5,
        )
        assert create_tenant_resp.status_code == 200
        assert create_tenant_resp.json()["tenant"]["tenant_id"] == tenant_id

        create_tenant_2_resp = requests.post(
            f"{base_url}/api/platform/tenants",
            json={"tenant_id": tenant_id_2, "name": "Web Console Tenant B"},
            timeout=5,
        )
        assert create_tenant_2_resp.status_code == 200
        assert create_tenant_2_resp.json()["tenant"]["tenant_id"] == tenant_id_2

        create_mcp_a_resp = requests.post(
            f"{base_url}/api/mcp/servers",
            json={
                "tenant_id": tenant_id,
                "name": "shared-mcp",
                "command": "python",
                "args": ["-m", "tenant_a"],
                "env": {"TENANT": "A"},
            },
            timeout=5,
        )
        create_mcp_b_resp = requests.post(
            f"{base_url}/api/mcp/servers",
            json={
                "tenant_id": tenant_id_2,
                "name": "shared-mcp",
                "command": "node",
                "args": ["tenant-b.js"],
                "env": {"TENANT": "B"},
            },
            timeout=5,
        )
        assert create_mcp_a_resp.status_code == 200
        assert create_mcp_a_resp.json()["server"]["command"] == "python"
        assert create_mcp_b_resp.status_code == 200
        assert create_mcp_b_resp.json()["server"]["command"] == "node"

        list_mcp_a_resp = requests.get(
            f"{base_url}/api/mcp/servers",
            params={"tenant_id": tenant_id},
            timeout=5,
        )
        list_mcp_b_resp = requests.get(
            f"{base_url}/api/mcp/servers",
            params={"tenant_id": tenant_id_2},
            timeout=5,
        )
        assert list_mcp_a_resp.status_code == 200
        assert list_mcp_b_resp.status_code == 200
        assert list_mcp_a_resp.json()["servers"][0]["command"] == "python"
        assert list_mcp_b_resp.json()["servers"][0]["command"] == "node"

        update_mcp_a_resp = requests.put(
            f"{base_url}/api/mcp/servers/shared-mcp",
            json={
                "tenant_id": tenant_id,
                "name": "shared-mcp",
                "command": "python3",
                "args": ["-m", "tenant_a_v2"],
                "env": {"TENANT": "A2"},
            },
            timeout=5,
        )
        assert update_mcp_a_resp.status_code == 200
        assert update_mcp_a_resp.json()["server"]["command"] == "python3"

        verify_mcp_b_resp = requests.get(
            f"{base_url}/api/mcp/servers",
            params={"tenant_id": tenant_id_2},
            timeout=5,
        )
        assert verify_mcp_b_resp.status_code == 200
        assert verify_mcp_b_resp.json()["servers"][0]["command"] == "node"

        delete_mcp_a_resp = requests.delete(
            f"{base_url}/api/mcp/servers/shared-mcp",
            params={"tenant_id": tenant_id},
            timeout=5,
        )
        assert delete_mcp_a_resp.status_code == 200
        assert delete_mcp_a_resp.json()["server"]["tenant_id"] == tenant_id

        list_mcp_a_after_delete_resp = requests.get(
            f"{base_url}/api/mcp/servers",
            params={"tenant_id": tenant_id},
            timeout=5,
        )
        list_mcp_b_after_delete_resp = requests.get(
            f"{base_url}/api/mcp/servers",
            params={"tenant_id": tenant_id_2},
            timeout=5,
        )
        assert list_mcp_a_after_delete_resp.status_code == 200
        assert list_mcp_a_after_delete_resp.json()["servers"] == []
        assert list_mcp_b_after_delete_resp.status_code == 200
        assert list_mcp_b_after_delete_resp.json()["servers"][0]["tenant_id"] == tenant_id_2

        tenant_user_meta = requests.get(f"{base_url}/api/platform/tenant-user-meta", timeout=5)
        assert tenant_user_meta.status_code == 200
        assert "owner" in tenant_user_meta.json()["roles"]

        create_tenant_user_resp = requests.post(
            f"{base_url}/api/platform/tenant-users",
            json={
                "tenant_id": tenant_id,
                "user_id": "alice",
                "name": "Alice",
                "role": "admin",
                "status": "active",
            },
            timeout=5,
        )
        assert create_tenant_user_resp.status_code == 200
        assert create_tenant_user_resp.json()["tenant_user"]["role"] == "admin"

        create_agent_resp = requests.post(
            f"{base_url}/api/platform/agents",
            json={
                "tenant_id": tenant_id,
                "name": "Web Console Agent",
                "model": "qwen-plus",
                "system_prompt": "你是 web-console 真实链路测试助手。",
                "tools": ["read", "write"],
            },
            timeout=5,
        )
        assert create_agent_resp.status_code == 200
        created_agent = create_agent_resp.json()["agent"]
        agent_id = created_agent["agent_id"]
        assert agent_id.startswith("agt_")
        assert len(agent_id) == 12

        shared_agent_a_resp = requests.post(
            f"{base_url}/api/platform/agents",
            json={
                "tenant_id": tenant_id,
                "agent_id": "shared-agent",
                "name": "Shared Agent A",
                "model": "qwen-plus",
            },
            timeout=5,
        )
        assert shared_agent_a_resp.status_code == 200
        assert shared_agent_a_resp.json()["agent"]["tenant_id"] == tenant_id

        shared_agent_b_resp = requests.post(
            f"{base_url}/api/platform/agents",
            json={
                "tenant_id": tenant_id_2,
                "agent_id": "shared-agent",
                "name": "Shared Agent B",
                "model": "qwen-plus",
            },
            timeout=5,
        )
        assert shared_agent_b_resp.status_code == 200
        assert shared_agent_b_resp.json()["agent"]["tenant_id"] == tenant_id_2

        get_agent_resp = requests.get(
            f"{base_url}/api/platform/agents/{agent_id}",
            params={"tenant_id": tenant_id},
            timeout=5,
        )
        assert get_agent_resp.status_code == 200
        assert get_agent_resp.json()["agent"]["name"] == "Web Console Agent"

        get_shared_agent_a_resp = requests.get(
            f"{base_url}/api/platform/agents/shared-agent",
            params={"tenant_id": tenant_id},
            timeout=5,
        )
        assert get_shared_agent_a_resp.status_code == 200
        assert get_shared_agent_a_resp.json()["agent"]["name"] == "Shared Agent A"

        get_shared_agent_b_resp = requests.get(
            f"{base_url}/api/platform/agents/shared-agent",
            params={"tenant_id": tenant_id_2},
            timeout=5,
        )
        assert get_shared_agent_b_resp.status_code == 200
        assert get_shared_agent_b_resp.json()["agent"]["name"] == "Shared Agent B"

        update_shared_agent_a_resp = requests.put(
            f"{base_url}/api/platform/agents/shared-agent",
            json={
                "tenant_id": tenant_id,
                "name": "Shared Agent A v2",
            },
            timeout=5,
        )
        assert update_shared_agent_a_resp.status_code == 200
        assert update_shared_agent_a_resp.json()["agent"]["name"] == "Shared Agent A v2"

        verify_shared_agent_b_resp = requests.get(
            f"{base_url}/api/platform/agents/shared-agent",
            params={"tenant_id": tenant_id_2},
            timeout=5,
        )
        assert verify_shared_agent_b_resp.status_code == 200
        assert verify_shared_agent_b_resp.json()["agent"]["name"] == "Shared Agent B"

        create_binding_resp = requests.post(
            f"{base_url}/api/platform/bindings",
            json={
                "tenant_id": tenant_id,
                "binding_id": binding_id,
                "name": "Web Console Binding",
                "channel_type": "web",
                "agent_id": agent_id,
                "metadata": {
                    "external_app_id": "cow-web-console",
                    "external_chat_id": "room-web-e2e",
                },
            },
            timeout=5,
        )
        assert create_binding_resp.status_code == 200
        assert create_binding_resp.json()["binding"]["agent_id"] == agent_id

        get_binding_resp = requests.get(
            f"{base_url}/api/platform/bindings/{binding_id}",
            params={"tenant_id": tenant_id},
            timeout=5,
        )
        assert get_binding_resp.status_code == 200
        assert get_binding_resp.json()["binding"]["channel_type"] == "web"

        create_identity_resp = requests.post(
            f"{base_url}/api/platform/tenant-user-identities",
            json={
                "tenant_id": tenant_id,
                "user_id": "alice",
                "channel_type": "web",
                "external_user_id": "alice-web",
            },
            timeout=5,
        )
        assert create_identity_resp.status_code == 200
        assert create_identity_resp.json()["identity"]["external_user_id"] == "alice-web"

        delete_identity_resp = requests.delete(
            f"{base_url}/api/platform/tenant-user-identities/{tenant_id}/web/alice-web",
            timeout=5,
        )
        assert delete_identity_resp.status_code == 200
        assert delete_identity_resp.json()["identity"]["external_user_id"] == "alice-web"

        delete_binding_resp = requests.delete(
            f"{base_url}/api/platform/bindings/{binding_id}",
            params={"tenant_id": tenant_id},
            timeout=5,
        )
        assert delete_binding_resp.status_code == 200
        assert delete_binding_resp.json()["status"] == "success"

        delete_agent_resp = requests.delete(
            f"{base_url}/api/platform/agents/{agent_id}",
            params={"tenant_id": tenant_id},
            timeout=5,
        )
        assert delete_agent_resp.status_code == 200
        assert delete_agent_resp.json()["agent_id"] == agent_id

        delete_shared_agent_a_resp = requests.delete(
            f"{base_url}/api/platform/agents/shared-agent",
            params={"tenant_id": tenant_id},
            timeout=5,
        )
        assert delete_shared_agent_a_resp.status_code == 200
        assert delete_shared_agent_a_resp.json()["agent_id"] == "shared-agent"

        still_get_shared_agent_b_resp = requests.get(
            f"{base_url}/api/platform/agents/shared-agent",
            params={"tenant_id": tenant_id_2},
            timeout=5,
        )
        assert still_get_shared_agent_b_resp.status_code == 200
        assert still_get_shared_agent_b_resp.json()["agent"]["tenant_id"] == tenant_id_2

        delete_shared_agent_b_resp = requests.delete(
            f"{base_url}/api/platform/agents/shared-agent",
            params={"tenant_id": tenant_id_2},
            timeout=5,
        )
        assert delete_shared_agent_b_resp.status_code == 200
        assert delete_shared_agent_b_resp.json()["agent_id"] == "shared-agent"

        delete_tenant_user_resp = requests.delete(
            f"{base_url}/api/platform/tenant-users/{tenant_id}/alice",
            timeout=5,
        )
        assert delete_tenant_user_resp.status_code == 200
        assert delete_tenant_user_resp.json()["tenant_user"]["user_id"] == "alice"
    finally:
        process.send_signal(signal.SIGTERM)
        process.wait(timeout=20)

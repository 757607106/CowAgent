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


def _register_owner(base_url: str, *, tenant_id: str) -> tuple[dict[str, str], str]:
    response = requests.post(
        f"{base_url}/api/platform/auth/register",
        json={
            "tenant_id": tenant_id,
            "tenant_name": "Acme Real Flow",
            "user_id": "alice",
            "user_name": "Alice",
            "account": f"{tenant_id}-owner",
            "password": "admin123456",
        },
        timeout=5,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    return {"Authorization": f"Bearer {body['token']}"}, body["tenant"]["tenant_id"]


def _poll_job_completed(
    base_url: str,
    job_id: str,
    *,
    headers: dict[str, str],
    timeout: float = 20.0,
) -> dict[str, object]:
    deadline = time.time() + timeout
    last_job: dict[str, object] | None = None
    while time.time() < deadline:
        response = requests.get(f"{base_url}/api/platform/jobs/{job_id}", headers=headers, timeout=5)
        payload = response.json()
        job = payload["job"]
        last_job = job
        if job["status"] in {"completed", "failed"}:
            return job
        time.sleep(0.25)
    raise AssertionError(f"job was not completed within {timeout}s: {last_job}")


@pytest.mark.e2e
def test_platform_real_http_flow_without_mock_data(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    port = find_free_port()
    base_url = f"http://127.0.0.1:{port}"
    tenant_id = f"acme-{int(time.time())}"
    day = "2026-04-23"

    env = os.environ.copy()
    env.update(
        {
            "AGENT_WORKSPACE": str(workspace),
            "MODEL": "qwen-plus",
            "COW_PLATFORM_PORT": str(port),
        }
    )

    api_process = subprocess.Popen(
        [sys.executable, "-m", "cow_platform.api.main", "--port", str(port)],
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        wait_for_http(f"{base_url}/health", timeout=30)
        headers, tenant_id = _register_owner(base_url, tenant_id=tenant_id)

        tenant_user_meta_resp = requests.get(f"{base_url}/api/platform/tenant-user-meta", headers=headers, timeout=5)
        assert tenant_user_meta_resp.status_code == 200
        assert "owner" in tenant_user_meta_resp.json()["roles"]

        create_tenant_user_resp = requests.get(
            f"{base_url}/api/platform/tenant-users/{tenant_id}/alice",
            headers=headers,
            timeout=5,
        )
        assert create_tenant_user_resp.status_code == 200
        assert create_tenant_user_resp.json()["tenant_user"]["role"] == "owner"

        create_agent_resp = requests.post(
            f"{base_url}/api/platform/agents",
            headers=headers,
            json={
                "tenant_id": tenant_id,
                "name": "Real Flow Agent",
                "model": "qwen-plus",
                "system_prompt": "你是一个真实流转测试助手。",
                "tools": ["read", "write"],
            },
            timeout=5,
        )
        assert create_agent_resp.status_code == 200
        created_agent = create_agent_resp.json()["agent"]
        auto_agent_id = created_agent["agent_id"]
        assert auto_agent_id.startswith("agt_")
        assert len(auto_agent_id) == 12

        binding_id = f"{tenant_id}-web"
        create_binding_resp = requests.post(
            f"{base_url}/api/platform/bindings",
            headers=headers,
            json={
                "tenant_id": tenant_id,
                "binding_id": binding_id,
                "name": "Real Web Entry",
                "channel_type": "web",
                "agent_id": auto_agent_id,
                "metadata": {
                    "external_app_id": "cow-web-console",
                    "external_chat_id": "room-real",
                    "external_user_id": "alice",
                },
            },
            timeout=5,
        )
        assert create_binding_resp.status_code == 200
        assert create_binding_resp.json()["binding"]["agent_id"] == auto_agent_id

        bind_identity_resp = requests.post(
            f"{base_url}/api/platform/tenant-user-identities",
            headers=headers,
            json={
                "tenant_id": tenant_id,
                "user_id": "alice",
                "channel_type": "web",
                "external_user_id": "alice-real-http-flow",
            },
            timeout=5,
        )
        assert bind_identity_resp.status_code == 200
        assert bind_identity_resp.json()["identity"]["external_user_id"] == "alice-real-http-flow"

        quota_resp = requests.post(
            f"{base_url}/api/platform/quotas",
            headers=headers,
            json={
                "scope_type": "agent",
                "tenant_id": tenant_id,
                "agent_id": auto_agent_id,
                "max_requests_per_day": 100,
                "max_tokens_per_day": 200000,
                "enabled": True,
            },
            timeout=5,
        )
        assert quota_resp.status_code == 200
        assert quota_resp.json()["quota"]["agent_id"] == auto_agent_id

        job_resp = requests.post(
            f"{base_url}/api/platform/jobs",
            headers=headers,
            json={
                "job_type": "usage_report",
                "tenant_id": tenant_id,
                "agent_id": auto_agent_id,
                "payload": {"day": day},
            },
            timeout=5,
        )
        assert job_resp.status_code == 200
        job_id = job_resp.json()["job"]["job_id"]

        worker_process = subprocess.Popen(
            [sys.executable, "-m", "cow_platform.worker.main", "--once"],
            cwd=REPO_ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        worker_process.wait(timeout=20)

        job = _poll_job_completed(base_url, job_id, headers=headers, timeout=20)
        assert job["status"] == "completed"
        artifact_path = Path(job["result"]["artifact_path"])
        assert artifact_path.exists()

        doctor_resp = requests.get(f"{base_url}/api/platform/doctor", headers=headers, timeout=5)
        assert doctor_resp.status_code == 200
        assert doctor_resp.json()["report"]["status"] == "ok"
    finally:
        api_process.send_signal(signal.SIGTERM)
        api_process.wait(timeout=20)

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests

from config import conf
from cow_platform.services.usage_service import UsageService
from tests.conftest import REPO_ROOT, find_free_port, wait_for_http


def _register_owner(base_url: str) -> tuple[dict[str, str], str]:
    response = requests.post(
        f"{base_url}/api/platform/auth/register",
        json={
            "tenant_id": "default",
            "tenant_name": "Default",
            "user_id": "owner",
            "user_name": "Owner",
            "account": "default-job-worker-owner",
            "password": "admin123456",
        },
        timeout=5,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    return {"Authorization": f"Bearer {body['token']}"}, body["tenant"]["tenant_id"]


@pytest.mark.e2e
def test_platform_app_and_worker_can_process_usage_report_job(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    monkeypatch.setitem(conf(), "agent_workspace", str(workspace))
    monkeypatch.setitem(conf(), "model", "qwen-plus")

    port = find_free_port()
    base_url = f"http://127.0.0.1:{port}"
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
        headers, tenant_id = _register_owner(base_url)

        UsageService().record_chat_usage(
            request_id="req-job-e2e-1",
            tenant_id=tenant_id,
            agent_id="default",
            model="qwen-plus",
            prompt_tokens=300,
            completion_tokens=100,
            created_at="2026-04-23T15:00:00",
        )

        create_resp = requests.post(
            f"{base_url}/api/platform/jobs",
            headers=headers,
            json={
                "job_type": "usage_report",
                "tenant_id": tenant_id,
                "agent_id": "default",
                "payload": {"day": "2026-04-23"},
            },
            timeout=5,
        )
        job_id = create_resp.json()["job"]["job_id"]

        worker_process = subprocess.Popen(
            [sys.executable, "-m", "cow_platform.worker.main", "--once"],
            cwd=REPO_ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        worker_process.wait(timeout=20)

        deadline = time.time() + 20
        payload = None
        while time.time() < deadline:
            get_resp = requests.get(
                f"{base_url}/api/platform/jobs/{job_id}",
                headers=headers,
                timeout=5,
            )
            payload = get_resp.json()["job"]
            if payload["status"] == "completed":
                break
            time.sleep(0.25)

        assert create_resp.status_code == 200
        assert payload is not None
        assert payload["status"] == "completed"
        assert payload["result"]["summary"]["request_count"] == 1
        assert Path(payload["result"]["artifact_path"]).exists()
    finally:
        api_process.send_signal(signal.SIGTERM)
        api_process.wait(timeout=20)

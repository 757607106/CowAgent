#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import requests


REPO_ROOT = Path(__file__).resolve().parents[2]


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_for_http(url: str, timeout: float = 30.0) -> requests.Response:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code < 500:
                return response
        except Exception as exc:  # pragma: no cover - polling helper
            last_error = exc
        time.sleep(0.25)
    if last_error:
        raise last_error
    raise TimeoutError(f"Timed out waiting for endpoint: {url}")


def request_json(method: str, url: str, *, timeout: float = 5.0, **kwargs) -> dict[str, object]:
    response = requests.request(method, url, timeout=timeout, **kwargs)
    response.raise_for_status()
    return response.json()


def poll_job(base_url: str, job_id: str, timeout: float = 20.0) -> dict[str, object]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        payload = request_json("GET", f"{base_url}/api/platform/jobs/{job_id}")
        job = payload["job"]
        if job["status"] in {"completed", "failed"}:
            return job
        time.sleep(0.25)
    raise TimeoutError(f"Timed out waiting for job completion: {job_id}")


def run_real_scenario(host: str, port: int, workspace: Path, model: str) -> dict[str, object]:
    base_url = f"http://{host}:{port}"
    tenant_id = f"real-{int(time.time())}"
    tenant_id_2 = f"{tenant_id}-b"
    binding_id = f"{tenant_id}-web"
    day = "2026-04-23"

    env = os.environ.copy()
    env.update(
        {
            "AGENT_WORKSPACE": str(workspace),
            "MODEL": model,
            "COW_PLATFORM_PORT": str(port),
        }
    )

    process = subprocess.Popen(
        [sys.executable, "-m", "cow_platform.api.main", "--host", host, "--port", str(port)],
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        wait_for_http(f"{base_url}/health", timeout=30)

        request_json(
            "POST",
            f"{base_url}/api/platform/tenants",
            json={"tenant_id": tenant_id, "name": "Real Scenario Tenant"},
        )
        request_json(
            "POST",
            f"{base_url}/api/platform/tenants",
            json={"tenant_id": tenant_id_2, "name": "Real Scenario Tenant B"},
        )

        tenant_user_meta = request_json("GET", f"{base_url}/api/platform/tenant-user-meta")
        if "owner" not in tenant_user_meta.get("roles", []):
            raise AssertionError(f"tenant user meta missing owner role: {tenant_user_meta}")

        request_json(
            "POST",
            f"{base_url}/api/platform/tenant-users",
            json={
                "tenant_id": tenant_id,
                "user_id": "alice",
                "name": "Alice",
                "role": "owner",
                "status": "active",
            },
        )

        created_agent = request_json(
            "POST",
            f"{base_url}/api/platform/agents",
            json={
                "tenant_id": tenant_id,
                "name": "Real Scenario Agent",
                "model": model,
                "system_prompt": "你是一个真实场景联调助手。",
                "tools": ["read", "write"],
                "skills": [],
                "knowledge_enabled": True,
            },
        )["agent"]
        auto_agent_id = str(created_agent["agent_id"])
        if not auto_agent_id.startswith("agt_"):
            raise AssertionError(f"unexpected auto agent_id format: {auto_agent_id}")

        request_json(
            "POST",
            f"{base_url}/api/platform/agents",
            json={
                "tenant_id": tenant_id,
                "agent_id": "shared-agent",
                "name": "Shared Agent A",
                "model": model,
            },
        )
        request_json(
            "POST",
            f"{base_url}/api/platform/agents",
            json={
                "tenant_id": tenant_id_2,
                "agent_id": "shared-agent",
                "name": "Shared Agent B",
                "model": model,
            },
        )

        shared_agent_a = request_json(
            "GET",
            f"{base_url}/api/platform/agents/shared-agent",
            params={"tenant_id": tenant_id},
        )["agent"]
        if shared_agent_a["name"] != "Shared Agent A":
            raise AssertionError(f"shared agent A fetch mismatch: {shared_agent_a}")

        shared_agent_b = request_json(
            "GET",
            f"{base_url}/api/platform/agents/shared-agent",
            params={"tenant_id": tenant_id_2},
        )["agent"]
        if shared_agent_b["name"] != "Shared Agent B":
            raise AssertionError(f"shared agent B fetch mismatch: {shared_agent_b}")

        request_json(
            "PUT",
            f"{base_url}/api/platform/agents/shared-agent",
            json={"tenant_id": tenant_id, "name": "Shared Agent A v2"},
        )
        shared_agent_b_after = request_json(
            "GET",
            f"{base_url}/api/platform/agents/shared-agent",
            params={"tenant_id": tenant_id_2},
        )["agent"]
        if shared_agent_b_after["name"] != "Shared Agent B":
            raise AssertionError(f"tenant isolation mismatch: {shared_agent_b_after}")

        request_json(
            "POST",
            f"{base_url}/api/platform/bindings",
            json={
                "tenant_id": tenant_id,
                "binding_id": binding_id,
                "name": "Real Scenario Binding",
                "channel_type": "web",
                "agent_id": auto_agent_id,
                "metadata": {
                    "external_app_id": "cow-web-console",
                    "external_chat_id": "room-real",
                    "external_user_id": "alice",
                },
            },
        )

        request_json(
            "POST",
            f"{base_url}/api/platform/tenant-user-identities",
            json={
                "tenant_id": tenant_id,
                "user_id": "alice",
                "channel_type": "web",
                "external_user_id": "alice-real-flow",
            },
        )

        request_json(
            "POST",
            f"{base_url}/api/platform/quotas",
            json={
                "scope_type": "agent",
                "tenant_id": tenant_id,
                "agent_id": auto_agent_id,
                "max_requests_per_day": 100,
                "max_tokens_per_day": 200000,
                "enabled": True,
            },
        )

        created_job = request_json(
            "POST",
            f"{base_url}/api/platform/jobs",
            json={
                "job_type": "usage_report",
                "tenant_id": tenant_id,
                "agent_id": auto_agent_id,
                "payload": {"day": day},
            },
        )["job"]
        job_id = str(created_job["job_id"])

        worker_process = subprocess.Popen(
            [sys.executable, "-m", "cow_platform.worker.main", "--once"],
            cwd=REPO_ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        worker_process.wait(timeout=20)

        finished_job = poll_job(base_url, job_id, timeout=20)
        if finished_job["status"] != "completed":
            raise AssertionError(f"job failed: {finished_job}")

        doctor = request_json("GET", f"{base_url}/api/platform/doctor")
        if doctor["report"]["status"] != "ok":
            raise AssertionError(f"doctor check failed: {doctor}")

        return {
            "status": "success",
            "tenant_id": tenant_id,
            "tenant_id_2": tenant_id_2,
            "agent_id": auto_agent_id,
            "binding_id": binding_id,
            "job_id": job_id,
            "artifact_path": finished_job["result"]["artifact_path"],
            "doctor_status": doctor["report"]["status"],
        }
    finally:
        process.send_signal(signal.SIGTERM)
        process.wait(timeout=20)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a real end-to-end platform scenario over HTTP.")
    parser.add_argument("--host", default="127.0.0.1", help="Host for the temporary API process.")
    parser.add_argument("--port", type=int, default=0, help="Port for the temporary API process.")
    parser.add_argument("--model", default="qwen-plus", help="Model name for agent creation.")
    parser.add_argument(
        "--workspace",
        default="",
        help="Workspace root. Defaults to a temporary directory if omitted.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    port = args.port or find_free_port()

    if args.workspace:
        workspace = Path(args.workspace).expanduser().resolve()
        workspace.mkdir(parents=True, exist_ok=True)
        summary = run_real_scenario(args.host, port, workspace, args.model)
    else:
        with tempfile.TemporaryDirectory(prefix="cow-real-scenario-") as tmp_dir:
            workspace = Path(tmp_dir) / "workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            summary = run_real_scenario(args.host, port, workspace, args.model)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

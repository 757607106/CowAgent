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


REPO_ROOT = Path(__file__).resolve().parents[1]


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_for_http(url: str, timeout: float = 40.0) -> requests.Response:
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


def run_web_console_bridge(host: str, port: int, workspace: Path, model: str) -> dict[str, object]:
    base_url = f"http://{host}:{port}"
    binding_id = f"web-bind-{int(time.time())}"
    tenant_id = f"web-tenant-{int(time.time())}"
    tenant_id_2 = f"{tenant_id}-b"

    env = os.environ.copy()
    env.update(
        {
            "agent_workspace": str(workspace),
            "model": model,
            "agent": "true",
            "channel_type": "web",
            "web_port": str(port),
            "web_password": "",
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
        wait_for_http(f"{base_url}/chat", timeout=40)

        agents_payload = request_json("GET", f"{base_url}/api/platform/agents")
        if agents_payload.get("status") != "success":
            raise AssertionError(f"unable to list agents: {agents_payload}")

        tenants_payload = request_json("GET", f"{base_url}/api/platform/tenants")
        if tenants_payload.get("status") != "success":
            raise AssertionError(f"unable to list tenants: {tenants_payload}")

        created_tenant = request_json(
            "POST",
            f"{base_url}/api/platform/tenants",
            json={"tenant_id": tenant_id, "name": "Web Console Bridge Tenant"},
        )["tenant"]
        if created_tenant["tenant_id"] != tenant_id:
            raise AssertionError(f"tenant creation mismatch: {created_tenant}")

        created_tenant_2 = request_json(
            "POST",
            f"{base_url}/api/platform/tenants",
            json={"tenant_id": tenant_id_2, "name": "Web Console Bridge Tenant B"},
        )["tenant"]
        if created_tenant_2["tenant_id"] != tenant_id_2:
            raise AssertionError(f"tenant creation mismatch: {created_tenant_2}")

        meta_payload = request_json("GET", f"{base_url}/api/platform/tenant-user-meta")
        if "owner" not in meta_payload.get("roles", []):
            raise AssertionError(f"tenant user meta invalid: {meta_payload}")

        created_tenant_user = request_json(
            "POST",
            f"{base_url}/api/platform/tenant-users",
            json={
                "tenant_id": tenant_id,
                "user_id": "alice",
                "name": "Alice",
                "role": "admin",
                "status": "active",
            },
        )["tenant_user"]
        if created_tenant_user["role"] != "admin":
            raise AssertionError(f"tenant user creation mismatch: {created_tenant_user}")

        created_agent = request_json(
            "POST",
            f"{base_url}/api/platform/agents",
            json={
                "tenant_id": tenant_id,
                "name": "Web Console Bridge Agent",
                "model": model,
                "system_prompt": "你是 web-console 对接验证助手。",
                "tools": ["read", "write"],
            },
        )["agent"]
        agent_id = str(created_agent["agent_id"])
        if not agent_id.startswith("agt_"):
            raise AssertionError(f"unexpected auto agent_id: {agent_id}")

        shared_agent_a = request_json(
            "POST",
            f"{base_url}/api/platform/agents",
            json={
                "tenant_id": tenant_id,
                "agent_id": "shared-agent",
                "name": "Shared Agent A",
                "model": model,
            },
        )["agent"]
        if shared_agent_a["tenant_id"] != tenant_id:
            raise AssertionError(f"shared agent A mismatch: {shared_agent_a}")

        shared_agent_b = request_json(
            "POST",
            f"{base_url}/api/platform/agents",
            json={
                "tenant_id": tenant_id_2,
                "agent_id": "shared-agent",
                "name": "Shared Agent B",
                "model": model,
            },
        )["agent"]
        if shared_agent_b["tenant_id"] != tenant_id_2:
            raise AssertionError(f"shared agent B mismatch: {shared_agent_b}")

        fetched_shared_agent_a = request_json(
            "GET",
            f"{base_url}/api/platform/agents/shared-agent",
            params={"tenant_id": tenant_id},
        )["agent"]
        if fetched_shared_agent_a["name"] != "Shared Agent A":
            raise AssertionError(f"shared agent A fetch mismatch: {fetched_shared_agent_a}")

        fetched_shared_agent_b = request_json(
            "GET",
            f"{base_url}/api/platform/agents/shared-agent",
            params={"tenant_id": tenant_id_2},
        )["agent"]
        if fetched_shared_agent_b["name"] != "Shared Agent B":
            raise AssertionError(f"shared agent B fetch mismatch: {fetched_shared_agent_b}")

        updated_shared_agent_a = request_json(
            "PUT",
            f"{base_url}/api/platform/agents/shared-agent",
            json={
                "tenant_id": tenant_id,
                "name": "Shared Agent A v2",
            },
        )["agent"]
        if updated_shared_agent_a["name"] != "Shared Agent A v2":
            raise AssertionError(f"shared agent A update mismatch: {updated_shared_agent_a}")

        refetched_shared_agent_b = request_json(
            "GET",
            f"{base_url}/api/platform/agents/shared-agent",
            params={"tenant_id": tenant_id_2},
        )["agent"]
        if refetched_shared_agent_b["name"] != "Shared Agent B":
            raise AssertionError(f"shared agent B should be isolated: {refetched_shared_agent_b}")

        binding = request_json(
            "POST",
            f"{base_url}/api/platform/bindings",
            json={
                "tenant_id": tenant_id,
                "binding_id": binding_id,
                "name": "Web Console Bridge Binding",
                "channel_type": "web",
                "agent_id": agent_id,
                "metadata": {
                    "external_app_id": "cow-web-console",
                    "external_chat_id": "room-web-script",
                    "external_user_id": "alice",
                },
            },
        )["binding"]
        if binding["agent_id"] != agent_id:
            raise AssertionError(f"binding agent mismatch: {binding}")

        fetched_binding = request_json(
            "GET",
            f"{base_url}/api/platform/bindings/{binding_id}",
            params={"tenant_id": tenant_id},
        )["binding"]
        if fetched_binding["binding_id"] != binding_id:
            raise AssertionError(f"binding fetch mismatch: {fetched_binding}")

        identity = request_json(
            "POST",
            f"{base_url}/api/platform/tenant-user-identities",
            json={
                "tenant_id": tenant_id,
                "user_id": "alice",
                "channel_type": "web",
                "external_user_id": "alice-web-script",
            },
        )["identity"]
        if identity["external_user_id"] != "alice-web-script":
            raise AssertionError(f"tenant identity mismatch: {identity}")

        request_json("DELETE", f"{base_url}/api/platform/tenant-user-identities/{tenant_id}/web/alice-web-script")
        request_json("DELETE", f"{base_url}/api/platform/bindings/{binding_id}", params={"tenant_id": tenant_id})
        request_json("DELETE", f"{base_url}/api/platform/agents/{agent_id}", params={"tenant_id": tenant_id})
        request_json("DELETE", f"{base_url}/api/platform/agents/shared-agent", params={"tenant_id": tenant_id})
        request_json("DELETE", f"{base_url}/api/platform/agents/shared-agent", params={"tenant_id": tenant_id_2})
        request_json("DELETE", f"{base_url}/api/platform/tenant-users/{tenant_id}/alice")

        return {
            "status": "success",
            "web_port": port,
            "tenant_id": tenant_id,
            "tenant_id_2": tenant_id_2,
            "agent_id": agent_id,
            "binding_id": binding_id,
        }
    finally:
        process.send_signal(signal.SIGTERM)
        process.wait(timeout=20)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate web console to platform API bridging with real HTTP calls.")
    parser.add_argument("--host", default="127.0.0.1", help="Host for the temporary web process.")
    parser.add_argument("--port", type=int, default=0, help="Port for the temporary web process.")
    parser.add_argument("--model", default="qwen-plus", help="Model for agent creation.")
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
        result = run_web_console_bridge(args.host, port, workspace, args.model)
    else:
        with tempfile.TemporaryDirectory(prefix="cow-web-bridge-") as tmp_dir:
            workspace = Path(tmp_dir) / "workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            result = run_web_console_bridge(args.host, port, workspace, args.model)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

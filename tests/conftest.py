from __future__ import annotations

import os
import socket
import subprocess
import time
from pathlib import Path

import pytest
import requests


REPO_ROOT = Path(__file__).resolve().parents[1]


def _reset_platform_postgres_if_configured() -> None:
    if not os.getenv("COW_PLATFORM_DATABASE_URL"):
        return
    try:
        from cow_platform.db import connect

        with connect() as conn:
            conn.execute(
                """
                TRUNCATE
                    platform_audit_logs,
                    platform_usage_records,
                    platform_jobs,
                    platform_quotas,
                    platform_pricing,
                    platform_model_configs,
                    platform_bindings,
                    platform_channel_configs,
                    platform_tenant_user_identities,
                    platform_tenant_users,
                    platform_agents,
                    platform_users,
                    platform_tenants,
                    platform_conversation_messages,
                    platform_conversation_sessions,
                    platform_memory_chunks,
                    platform_memory_files,
                    platform_settings
                RESTART IDENTITY CASCADE
                """
            )
            conn.commit()
    except Exception:
        return


@pytest.fixture(autouse=True)
def reset_platform_postgres_between_tests():
    _reset_platform_postgres_if_configured()
    yield


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
    if last_error is not None:
        raise last_error
    raise TimeoutError(f"Timed out waiting for HTTP endpoint: {url}")


def wait_for_command(
    command: list[str],
    *,
    timeout: float = 30.0,
    env: dict[str, str] | None = None,
    cwd: str | Path | None = None,
) -> subprocess.CompletedProcess[str]:
    deadline = time.time() + timeout
    last_result: subprocess.CompletedProcess[str] | None = None
    while time.time() < deadline:
        result = subprocess.run(
            command,
            cwd=cwd or REPO_ROOT,
            env=env or os.environ.copy(),
            text=True,
            capture_output=True,
        )
        last_result = result
        if result.returncode == 0:
            return result
        time.sleep(1)
    raise AssertionError(
        f"Command did not succeed within {timeout}s: {' '.join(command)}\n"
        f"stdout:\n{last_result.stdout if last_result else ''}\n"
        f"stderr:\n{last_result.stderr if last_result else ''}"
    )

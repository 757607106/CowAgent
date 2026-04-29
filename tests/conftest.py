from __future__ import annotations

import os
from functools import lru_cache
import socket
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse

import pytest
import requests


REPO_ROOT = Path(__file__).resolve().parents[1]


POSTGRES_BACKED_TESTS = {
    "tests/e2e/test_platform_doctor_cli.py",
    "tests/e2e/test_platform_health_startup.py",
    "tests/e2e/test_platform_job_worker_flow.py",
    "tests/e2e/test_platform_real_http_flow.py",
    "tests/e2e/test_web_console_platform_bridge.py",
    "tests/integration/test_agent_api_extended.py",
    "tests/integration/test_agent_bridge_usage_quota.py",
    "tests/integration/test_binding_runtime_resolution.py",
    "tests/integration/test_platform_admin_model_flow.py",
    "tests/integration/test_platform_agent_api.py",
    "tests/integration/test_platform_api_authz.py",
    "tests/integration/test_platform_app.py",
    "tests/integration/test_platform_auth_api.py",
    "tests/integration/test_platform_channel_config_flow.py",
    "tests/integration/test_platform_governance_api.py",
    "tests/integration/test_platform_job_api.py",
    "tests/integration/test_platform_tenant_binding_api.py",
    "tests/integration/test_platform_tenant_user_api.py",
    "tests/integration/test_platform_usage_quota_api.py",
    "tests/integration/test_postgres_platform_storage.py",
    "tests/integration/test_runtime_agent_isolation.py",
    "tests/integration/test_web_tenant_auth_isolation.py",
}

PLATFORM_TEST_RESET_DATABASE_ENV = "COW_PLATFORM_TEST_RESET_DATABASE"


def _truthy_env(name: str) -> bool:
    return str(os.getenv(name, "")).strip().lower() in {"1", "true", "yes", "on"}


def _platform_database_url() -> str:
    from cow_platform.db import get_database_url

    return get_database_url()


def _platform_database_name(database_url: str) -> str:
    parsed = urlparse(database_url)
    return parsed.path.rsplit("/", 1)[-1].strip()


def _is_safe_platform_test_database_url(database_url: str) -> bool:
    database_name = _platform_database_name(database_url).lower()
    return bool(database_name and "test" in database_name)


def _platform_postgres_test_database_skip_reason() -> str:
    database_url = _platform_database_url()
    if _is_safe_platform_test_database_url(database_url):
        return ""
    database_name = _platform_database_name(database_url) or "<unknown>"
    return (
        "PostgreSQL platform tests require a dedicated test database whose name contains "
        f"'test'; current database is '{database_name}'. Refusing to run against a live database."
    )


def _platform_postgres_reset_skip_reason() -> str:
    if not _truthy_env(PLATFORM_TEST_RESET_DATABASE_ENV):
        return f"{PLATFORM_TEST_RESET_DATABASE_ENV}=1 is required before tests may truncate platform tables"
    return _platform_postgres_test_database_skip_reason()


@lru_cache(maxsize=1)
def _platform_postgres_available() -> tuple[bool, str]:
    try:
        from cow_platform.db import connect

        with connect() as conn:
            conn.execute("SELECT 1").fetchone()
        return True, ""
    except Exception as exc:
        return False, str(exc)


def pytest_collection_modifyitems(config, items):
    postgres_items = []
    for item in items:
        path = Path(str(item.path)).relative_to(REPO_ROOT).as_posix()
        if path in POSTGRES_BACKED_TESTS:
            postgres_items.append(item)
    if not postgres_items:
        return
    unsafe_reason = _platform_postgres_test_database_skip_reason()
    if unsafe_reason:
        skip = pytest.mark.skip(reason=unsafe_reason)
        for item in postgres_items:
            item.add_marker(skip)
        return
    available, error = _platform_postgres_available()
    if available:
        return
    skip = pytest.mark.skip(reason=f"PostgreSQL platform database is not available: {error}")
    for item in postgres_items:
        item.add_marker(skip)


def _reset_platform_postgres_if_configured() -> None:
    reset_skip_reason = _platform_postgres_reset_skip_reason()
    if reset_skip_reason:
        if _truthy_env(PLATFORM_TEST_RESET_DATABASE_ENV):
            raise RuntimeError(reset_skip_reason)
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
                    platform_scheduled_tasks,
                    platform_channel_runtime_leases,
                    platform_quotas,
                    platform_pricing,
                    platform_model_configs,
                    platform_bindings,
                    platform_channel_configs,
                    platform_mcp_servers,
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

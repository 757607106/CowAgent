from __future__ import annotations

import os
import subprocess
import uuid

import pytest

from tests.conftest import REPO_ROOT, find_free_port, wait_for_command, wait_for_http


def _docker_available() -> bool:
    result = subprocess.run(
        ["docker", "info"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )
    return result.returncode == 0


@pytest.mark.e2e
@pytest.mark.docker
def test_compose_base_starts_platform_dependencies() -> None:
    if not _docker_available():
        pytest.skip("Docker engine is not available")

    project_name = f"cowphase0-{uuid.uuid4().hex[:8]}"
    compose_file = REPO_ROOT / "docker" / "compose.base.yml"
    env = os.environ.copy()
    env.update(
        {
            "PLATFORM_POSTGRES_PORT": str(find_free_port()),
            "PLATFORM_REDIS_PORT": str(find_free_port()),
            "PLATFORM_QDRANT_HTTP_PORT": str(find_free_port()),
            "PLATFORM_QDRANT_GRPC_PORT": str(find_free_port()),
            "PLATFORM_MINIO_API_PORT": str(find_free_port()),
            "PLATFORM_MINIO_CONSOLE_PORT": str(find_free_port()),
        }
    )
    compose_cmd = ["docker", "compose", "-p", project_name, "-f", str(compose_file)]

    try:
        up_result = subprocess.run(
            [*compose_cmd, "up", "-d", "postgres", "redis", "qdrant", "minio"],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            capture_output=True,
        )
        assert up_result.returncode == 0, up_result.stderr

        wait_for_command(
            [*compose_cmd, "exec", "-T", "postgres", "pg_isready", "-U", "cowplatform", "-d", "cowplatform"],
            timeout=90,
            env=env,
        )
        redis_result = wait_for_command(
            [*compose_cmd, "exec", "-T", "redis", "redis-cli", "ping"],
            timeout=60,
            env=env,
        )
        assert "PONG" in redis_result.stdout

        qdrant_response = wait_for_http(
            f"http://127.0.0.1:{env['PLATFORM_QDRANT_HTTP_PORT']}/collections",
            timeout=60,
        )
        minio_response = wait_for_http(
            f"http://127.0.0.1:{env['PLATFORM_MINIO_API_PORT']}/minio/health/live",
            timeout=60,
        )

        assert qdrant_response.status_code == 200
        assert minio_response.status_code == 200
    finally:
        subprocess.run(
            [*compose_cmd, "down", "-v"],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            capture_output=True,
        )

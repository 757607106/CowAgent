from __future__ import annotations

import subprocess

import pytest

from tests.conftest import REPO_ROOT


@pytest.mark.e2e
def test_platform_compose_file_is_valid() -> None:
    compose_cmd = ["docker", "compose", "-f", "docker/compose.base.yml", "-f", "docker/compose.platform.yml"]
    result = subprocess.run(
        [*compose_cmd, "config"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "platform-app:" in result.stdout
    assert "platform-worker:" in result.stdout
    assert "platform-web:" in result.stdout
    assert "COW_PLATFORM_DATABASE_URL" in result.stdout

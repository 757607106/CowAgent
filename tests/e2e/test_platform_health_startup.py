from __future__ import annotations

import os
import signal
import subprocess
import sys

import pytest

from tests.conftest import REPO_ROOT, find_free_port, wait_for_http


@pytest.mark.e2e
def test_platform_api_starts_and_serves_health_endpoints() -> None:
    port = find_free_port()
    env = os.environ.copy()
    process = subprocess.Popen(
        [sys.executable, "-m", "cow_platform.api.main", "--port", str(port)],
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        health_response = wait_for_http(f"http://127.0.0.1:{port}/health", timeout=30)
        ready_response = wait_for_http(f"http://127.0.0.1:{port}/ready", timeout=30)

        assert health_response.json()["status"] == "ok"
        assert ready_response.json()["status"] == "ready"
    finally:
        process.send_signal(signal.SIGTERM)
        process.wait(timeout=20)

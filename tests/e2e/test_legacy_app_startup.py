from __future__ import annotations

import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest

from tests.conftest import REPO_ROOT, find_free_port, wait_for_http


@pytest.mark.e2e
def test_legacy_app_starts_with_temp_config_and_serves_chat_page(tmp_path: Path) -> None:
    port = find_free_port()
    env = os.environ.copy()
    env.update(
        {
            "CHANNEL_TYPE": "web",
            "WEB_CONSOLE": "True",
            "WEB_PORT": str(port),
            "WEB_PASSWORD": "",
            "MODEL": "qwen3.6-plus",
            "AGENT": "True",
            "SPEECH_RECOGNITION": "False",
            "GROUP_SPEECH_RECOGNITION": "False",
            "VOICE_REPLY_VOICE": "False",
            "AGENT_WORKSPACE": str(tmp_path / "workspace"),
            "APPDATA_DIR": str(tmp_path / "appdata"),
        }
    )
    process = subprocess.Popen(
        [sys.executable, str(REPO_ROOT / "app.py")],
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        response = wait_for_http(f"http://127.0.0.1:{port}/chat", timeout=60)
        assert response.status_code == 200
        assert "CowAgent" in response.text
    finally:
        process.send_signal(signal.SIGTERM)
        process.wait(timeout=20)

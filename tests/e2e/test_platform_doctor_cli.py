from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.conftest import REPO_ROOT


@pytest.mark.e2e
def test_platform_doctor_cli_outputs_valid_report(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.update(
        {
            "AGENT_WORKSPACE": str(tmp_path / "workspace"),
            "MODEL": "qwen-plus",
        }
    )

    result = subprocess.run(
        [sys.executable, "-m", "cli", "platform", "doctor"],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["checks"]["patch_register"]["exists"] is True
    assert payload["checks"]["compose_platform"]["exists"] is True

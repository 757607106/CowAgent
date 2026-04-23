#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run_case(script_name: str, extra_args: list[str]) -> dict[str, object]:
    script_path = REPO_ROOT / "scripts" / script_name
    command = [sys.executable, str(script_path)] + extra_args
    result = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True)
    payload: dict[str, object] = {
        "script": script_name,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "status": "success" if result.returncode == 0 else "failed",
    }
    if result.stdout.strip():
        try:
            payload["output"] = json.loads(result.stdout)
        except Exception:
            payload["output"] = {"raw": result.stdout.strip()}
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run real end-to-end integration matrix (no mock data).")
    parser.add_argument("--model", default="qwen-plus", help="Model used by scenario scripts.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    extra_args = ["--model", args.model]
    cases = [
        run_case("platform_real_scenario_test.py", extra_args),
        run_case("web_console_platform_bridge_test.py", extra_args),
    ]
    summary = {
        "status": "success" if all(item["returncode"] == 0 for item in cases) else "failed",
        "cases": cases,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import sys

from cow_platform.deployment.checks import (
    DependencySettings,
    check_all_dependencies,
    validate_environment,
    wait_for_dependencies,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate CowAgent platform deployment dependencies.")
    parser.add_argument("--require-all", action="store_true", help="Require PostgreSQL, Redis, Qdrant, and MinIO.")
    parser.add_argument("--strict-secrets", action="store_true", help="Reject default production secrets.")
    parser.add_argument("--wait-seconds", type=float, default=0.0, help="Wait for required dependencies.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    settings = DependencySettings.from_env()
    if args.require_all:
        settings = settings.require_all()

    validation_errors = validate_environment(settings, strict_secrets=args.strict_secrets)
    report = (
        wait_for_dependencies(settings, timeout_seconds=args.wait_seconds)
        if args.wait_seconds > 0
        else check_all_dependencies(settings)
    )
    payload = {
        "status": "ok" if report["ok"] and not validation_errors else "error",
        "environment": settings.environment,
        "validation_errors": validation_errors,
        "dependencies": report,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())

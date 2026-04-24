from __future__ import annotations

import argparse

import uvicorn

from cow_platform.api.app import create_app
from cow_platform.api.settings import PlatformSettings


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the CowAgent platform API.")
    parser.add_argument("--host", default=None, help="Bind host for the platform API.")
    parser.add_argument("--port", default=None, type=int, help="Bind port for the platform API.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    settings = PlatformSettings.from_env().with_overrides(host=args.host, port=args.port)
    uvicorn.run(
        create_app(settings),
        host=settings.host,
        port=settings.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

import os
from pathlib import Path
import subprocess

from common.log import logger


LOCAL_PLATFORM_ENV_KEYS = {
    "AGENT_WORKSPACE",
    "LOCAL_WEB_PORT",
    "MODEL",
    "WEB_PORT",
    "WEB_TENANT_AUTH",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _is_false_env(value: str) -> bool:
    return value.strip().lower() in {"0", "false", "no", "off"}


def should_import_local_platform_env(root: Path) -> bool:
    if _is_false_env(os.environ.get("COW_PLATFORM_AUTO_LOCAL_ENV", "true")):
        return False
    return (root / ".env.docker").is_file() or (root / ".env.local").is_file()


def parse_null_separated_env(raw_env: bytes) -> dict[str, str]:
    values: dict[str, str] = {}
    for item in raw_env.split(b"\0"):
        if not item or b"=" not in item:
            continue
        key, value = item.split(b"=", 1)
        values[key.decode("utf-8")] = value.decode("utf-8")
    return values


def _apply_local_dependency_env() -> None:
    postgres_user = os.environ.get("PLATFORM_POSTGRES_USER", "cowplatform")
    postgres_password = os.environ.get("PLATFORM_POSTGRES_PASSWORD", "prod-smoke-db-secret")
    postgres_db = os.environ.get("PLATFORM_POSTGRES_DB", "cowplatform")
    postgres_port = os.environ.get("PLATFORM_POSTGRES_PORT", "55432")
    redis_port = os.environ.get("PLATFORM_REDIS_PORT", "56379")
    qdrant_port = os.environ.get("PLATFORM_QDRANT_HTTP_PORT", "56333")
    minio_port = os.environ.get("PLATFORM_MINIO_API_PORT", "59000")

    os.environ["COW_PLATFORM_DATABASE_URL"] = (
        f"postgresql://{postgres_user}:{postgres_password}@127.0.0.1:{postgres_port}/{postgres_db}"
    )
    os.environ["COW_PLATFORM_REDIS_URL"] = f"redis://127.0.0.1:{redis_port}/0"
    os.environ["COW_PLATFORM_QDRANT_URL"] = f"http://127.0.0.1:{qdrant_port}"
    os.environ["COW_PLATFORM_MINIO_ENDPOINT"] = f"http://127.0.0.1:{minio_port}"
    os.environ["COW_PLATFORM_MINIO_ACCESS_KEY"] = os.environ.get("PLATFORM_MINIO_ROOT_USER", "cowplatform-prod")
    os.environ["COW_PLATFORM_MINIO_SECRET_KEY"] = os.environ.get(
        "PLATFORM_MINIO_ROOT_PASSWORD",
        "prod-smoke-minio-secret",
    )
    os.environ["COW_PLATFORM_MINIO_BUCKET"] = os.environ.get("PLATFORM_MINIO_BUCKET", "coreagent")
    os.environ["COW_PLATFORM_ENV"] = "dev"
    os.environ["WEB_TENANT_AUTH"] = os.environ.get("WEB_TENANT_AUTH", "true")
    os.environ["WEB_PORT"] = os.environ.get("LOCAL_WEB_PORT", "9901")
    os.environ["MODEL"] = os.environ.get("MODEL", "qwen3.6-plus")
    os.environ["AGENT_WORKSPACE"] = os.environ.get("AGENT_WORKSPACE", str(Path.home() / "cow"))


def import_local_platform_env(root: Path | None = None, *, source: str = "Platform") -> None:
    """Load local source-code env and derive Docker dependency URLs."""
    root = root or _repo_root()
    if not should_import_local_platform_env(root):
        return

    result = subprocess.run(
        [
            "/bin/bash",
            "-lc",
            (
                "set -a; "
                "[ -f .env.docker ] && source .env.docker; "
                "[ -f .env.local ] && source .env.local; "
                "set +a; env -0"
            ),
        ],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Failed to load local platform env from .env.docker/.env.local: {message}")

    loaded_env = parse_null_separated_env(result.stdout)
    imported = 0
    for key, value in loaded_env.items():
        if key.startswith(("COW_PLATFORM_", "PLATFORM_")) or key in LOCAL_PLATFORM_ENV_KEYS:
            os.environ[key] = value
            imported += 1

    _apply_local_dependency_env()

    logger.debug(
        "[{}] Loaded local platform env from .env.local: WEB_PORT={}, MODEL={}, AGENT_WORKSPACE={}".format(
            source,
            os.environ.get("WEB_PORT", ""),
            os.environ.get("MODEL", ""),
            os.environ.get("AGENT_WORKSPACE", ""),
        )
    )
    logger.debug("[{}] Imported {} local platform environment variables".format(source, imported))

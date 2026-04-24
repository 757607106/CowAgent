from __future__ import annotations

from dataclasses import dataclass, replace
import json
import os
import socket
import time
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from cow_platform.db import connect, get_database_url


TRUTHY = {"1", "true", "yes", "on"}
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1", "0.0.0.0"}
DEFAULT_SECRET_VALUES = {"cowplatform", "cowplatform123", "password", "changeme", "change-me"}


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in TRUTHY


def _join_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


@dataclass(frozen=True)
class DependencySettings:
    environment: str
    require_dependencies: bool
    database_url: str
    redis_url: str
    qdrant_url: str
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str
    web_tenant_auth: bool

    @classmethod
    def from_env(cls) -> "DependencySettings":
        environment = (
            os.getenv("COW_PLATFORM_ENV")
            or os.getenv("COW_PLATFORM_MODE")
            or os.getenv("APP_ENV")
            or "dev"
        ).strip().lower()
        return cls(
            environment=environment,
            require_dependencies=_as_bool(os.getenv("COW_PLATFORM_REQUIRE_DEPENDENCIES"), False),
            database_url=get_database_url(),
            redis_url=os.getenv("COW_PLATFORM_REDIS_URL")
            or os.getenv("REDIS_URL")
            or "redis://127.0.0.1:56379/0",
            qdrant_url=os.getenv("COW_PLATFORM_QDRANT_URL")
            or os.getenv("QDRANT_URL")
            or "http://127.0.0.1:56333",
            minio_endpoint=os.getenv("COW_PLATFORM_MINIO_ENDPOINT")
            or os.getenv("MINIO_ENDPOINT")
            or "http://127.0.0.1:59000",
            minio_access_key=os.getenv("COW_PLATFORM_MINIO_ACCESS_KEY")
            or os.getenv("MINIO_ROOT_USER")
            or "cowplatform",
            minio_secret_key=os.getenv("COW_PLATFORM_MINIO_SECRET_KEY")
            or os.getenv("MINIO_ROOT_PASSWORD")
            or "cowplatform123",
            minio_bucket=os.getenv("COW_PLATFORM_MINIO_BUCKET") or "cowagent",
            web_tenant_auth=_as_bool(os.getenv("WEB_TENANT_AUTH"), False),
        )

    def required_dependency_names(self) -> tuple[str, ...]:
        if self.require_dependencies:
            return ("postgres", "redis", "qdrant", "minio")
        return ("postgres",)

    def require_all(self) -> "DependencySettings":
        return replace(self, require_dependencies=True)


def check_postgres(settings: DependencySettings | None = None) -> dict[str, Any]:
    resolved = settings or DependencySettings.from_env()
    try:
        with connect() as conn:
            conn.execute("SELECT 1").fetchone()
        return {"ok": True, "url": resolved.database_url}
    except Exception as exc:
        return {"ok": False, "url": resolved.database_url, "error": str(exc)}


def _redis_command(sock: socket.socket, *parts: str) -> bytes:
    payload = f"*{len(parts)}\r\n".encode("utf-8")
    for part in parts:
        encoded = part.encode("utf-8")
        payload += f"${len(encoded)}\r\n".encode("utf-8") + encoded + b"\r\n"
    sock.sendall(payload)
    return sock.recv(4096)


def check_redis(settings: DependencySettings | None = None) -> dict[str, Any]:
    resolved = settings or DependencySettings.from_env()
    parsed = urlparse(resolved.redis_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 6379
    try:
        with socket.create_connection((host, port), timeout=3) as sock:
            if parsed.password:
                auth_response = _redis_command(sock, "AUTH", parsed.password)
                if not auth_response.startswith(b"+OK"):
                    return {
                        "ok": False,
                        "url": resolved.redis_url,
                        "error": auth_response.decode("utf-8", errors="replace").strip(),
                    }
            ping_response = _redis_command(sock, "PING")
        ok = ping_response.startswith(b"+PONG")
        payload: dict[str, Any] = {"ok": ok, "url": resolved.redis_url}
        if not ok:
            payload["error"] = ping_response.decode("utf-8", errors="replace").strip()
        return payload
    except Exception as exc:
        return {"ok": False, "url": resolved.redis_url, "error": str(exc)}


def _check_http_json_or_status(name: str, base_url: str, path: str) -> dict[str, Any]:
    url = _join_url(base_url, path)
    try:
        request = Request(url, headers={"User-Agent": "cow-platform-doctor/1.0"})
        with urlopen(request, timeout=5) as response:
            body = response.read(1024)
            ok = 200 <= response.status < 300
        payload: dict[str, Any] = {"ok": ok, "url": base_url, "status_code": response.status}
        if body:
            try:
                payload["body"] = json.loads(body.decode("utf-8"))
            except Exception:
                pass
        return payload
    except Exception as exc:
        return {"ok": False, "url": base_url, "error": f"{name}:{exc}"}


def check_qdrant(settings: DependencySettings | None = None) -> dict[str, Any]:
    resolved = settings or DependencySettings.from_env()
    return _check_http_json_or_status("qdrant", resolved.qdrant_url, "/collections")


def check_minio(settings: DependencySettings | None = None) -> dict[str, Any]:
    resolved = settings or DependencySettings.from_env()
    payload = _check_http_json_or_status("minio", resolved.minio_endpoint, "/minio/health/live")
    payload["bucket"] = resolved.minio_bucket
    return payload


def check_all_dependencies(settings: DependencySettings | None = None) -> dict[str, Any]:
    resolved = settings or DependencySettings.from_env()
    required = resolved.required_dependency_names()
    checks = {"postgres": check_postgres(resolved)}
    if resolved.require_dependencies:
        checks.update(
            {
                "redis": check_redis(resolved),
                "qdrant": check_qdrant(resolved),
                "minio": check_minio(resolved),
            }
        )
    else:
        checks.update(
            {
                "redis": {"ok": None, "url": resolved.redis_url, "skipped": True},
                "qdrant": {"ok": None, "url": resolved.qdrant_url, "skipped": True},
                "minio": {
                    "ok": None,
                    "url": resolved.minio_endpoint,
                    "bucket": resolved.minio_bucket,
                    "skipped": True,
                },
            }
        )
    return {
        "ok": all(checks[name].get("ok") for name in required),
        "required": list(required),
        "checks": checks,
    }


def _url_host(value: str) -> str:
    return (urlparse(value).hostname or "").strip().lower()


def _url_password(value: str) -> str:
    return urlparse(value).password or ""


def validate_environment(
    settings: DependencySettings | None = None,
    *,
    strict_secrets: bool = False,
) -> list[str]:
    resolved = settings or DependencySettings.from_env()
    errors: list[str] = []
    is_prod = resolved.environment in {"prod", "production"}
    is_consistent_env = resolved.environment in {"test", "prod", "production"}

    if is_consistent_env and not resolved.require_dependencies:
        errors.append("COW_PLATFORM_REQUIRE_DEPENDENCIES must be true in test/production deployments")

    if is_prod:
        required_env_keys = (
            "COW_PLATFORM_DATABASE_URL",
            "COW_PLATFORM_REDIS_URL",
            "COW_PLATFORM_QDRANT_URL",
            "COW_PLATFORM_MINIO_ENDPOINT",
            "COW_PLATFORM_MINIO_ACCESS_KEY",
            "COW_PLATFORM_MINIO_SECRET_KEY",
            "COW_PLATFORM_MINIO_BUCKET",
        )
        for key in required_env_keys:
            if not os.getenv(key):
                errors.append(f"missing production environment variable: {key}")
        for key, value in (
            ("COW_PLATFORM_DATABASE_URL", resolved.database_url),
            ("COW_PLATFORM_REDIS_URL", resolved.redis_url),
            ("COW_PLATFORM_QDRANT_URL", resolved.qdrant_url),
            ("COW_PLATFORM_MINIO_ENDPOINT", resolved.minio_endpoint),
        ):
            host = _url_host(value)
            if host in LOCAL_HOSTS:
                errors.append(f"{key} must not point to localhost in production: {host}")
        if os.getenv("CHANNEL_TYPE") == "web" and not resolved.web_tenant_auth:
            errors.append("WEB_TENANT_AUTH must be true for production web deployment")

    if strict_secrets and is_prod:
        database_password = _url_password(resolved.database_url)
        secret_values = {
            "COW_PLATFORM_DATABASE_URL password": database_password,
            "COW_PLATFORM_MINIO_ACCESS_KEY": resolved.minio_access_key,
            "COW_PLATFORM_MINIO_SECRET_KEY": resolved.minio_secret_key,
        }
        for key, value in secret_values.items():
            if not value or value.lower() in DEFAULT_SECRET_VALUES:
                errors.append(f"{key} must be set to a non-default production secret")

    return errors


def wait_for_dependencies(
    settings: DependencySettings | None = None,
    *,
    timeout_seconds: float = 90.0,
    interval_seconds: float = 2.0,
) -> dict[str, Any]:
    resolved = settings or DependencySettings.from_env()
    deadline = time.time() + timeout_seconds
    last_report: dict[str, Any] | None = None
    while time.time() <= deadline:
        last_report = check_all_dependencies(resolved)
        if last_report["ok"]:
            return last_report
        time.sleep(interval_seconds)
    assert last_report is not None
    return last_report

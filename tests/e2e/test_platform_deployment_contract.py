from __future__ import annotations

import os
import subprocess
from typing import Any
from urllib.parse import urlparse

import pytest
import yaml

from tests.conftest import REPO_ROOT


def _compose_config(files: list[str], env: dict[str, str] | None = None) -> dict[str, Any]:
    command = ["docker", "compose"]
    for file_name in files:
        command.extend(["-f", file_name])
    command.append("config")
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        env={**os.environ.copy(), **(env or {})},
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "sqlite" not in result.stdout.lower()
    return yaml.safe_load(result.stdout)


def _env_map(service: dict[str, Any]) -> dict[str, str]:
    environment = service.get("environment") or {}
    if isinstance(environment, dict):
        return {str(key): str(value) for key, value in environment.items()}
    result: dict[str, str] = {}
    for item in environment:
        key, _, value = str(item).partition("=")
        result[key] = value
    return result


def _depends_on(service: dict[str, Any]) -> set[str]:
    depends_on = service.get("depends_on") or {}
    if isinstance(depends_on, dict):
        return set(depends_on)
    return set(depends_on)


def _host(value: str) -> str:
    return urlparse(value).hostname or ""


@pytest.mark.e2e
def test_test_and_production_compose_use_the_same_dependency_stack() -> None:
    files = ["docker/compose.base.yml", "docker/compose.platform.yml"]
    test_config = _compose_config([*files, "docker/compose.test.yml"])
    prod_config = _compose_config(
        [*files, "docker/compose.prod.yml"],
        env={
            "PLATFORM_POSTGRES_PASSWORD": "strong-db-secret",
            "PLATFORM_MINIO_ROOT_USER": "prod-access",
            "PLATFORM_MINIO_ROOT_PASSWORD": "prod-minio-secret",
        },
    )

    required_services = {
        "postgres",
        "redis",
        "qdrant",
        "minio",
        "platform-app",
        "platform-worker",
        "platform-channel-runtime",
        "platform-web",
    }
    assert set(test_config["services"]) == required_services
    assert set(prod_config["services"]) == required_services

    for config, expected_env in ((test_config, "test"), (prod_config, "production")):
        services = config["services"]
        for service_name in ("platform-app", "platform-worker", "platform-channel-runtime", "platform-web"):
            service = services[service_name]
            env = _env_map(service)
            assert _depends_on(service) >= {"postgres", "redis", "qdrant", "minio"}
            assert env["COW_PLATFORM_ENV"] == expected_env
            assert env["COW_PLATFORM_REQUIRE_DEPENDENCIES"] == "true"
            assert env["COW_PLATFORM_STRICT_STARTUP"] == "true"
            assert _host(env["COW_PLATFORM_DATABASE_URL"]) == "postgres"
            assert _host(env["COW_PLATFORM_REDIS_URL"]) == "redis"
            assert _host(env["COW_PLATFORM_QDRANT_URL"]) == "qdrant"
            assert _host(env["COW_PLATFORM_MINIO_ENDPOINT"]) == "minio"
            assert env["COW_PLATFORM_MINIO_BUCKET"]
        assert _env_map(services["platform-web"])["WEB_TENANT_AUTH"] == "true"
        assert _env_map(services["platform-web"])["COW_PLATFORM_START_CHANNEL_RUNTIMES"] == "false"

    for service_name in required_services:
        assert prod_config["services"][service_name].get("restart") == "unless-stopped"


def test_platform_docker_image_does_not_generate_root_config_json() -> None:
    dockerfile = (REPO_ROOT / "docker" / "Dockerfile.latest").read_text(encoding="utf-8")
    entrypoint = (REPO_ROOT / "docker" / "entrypoint.sh").read_text(encoding="utf-8")

    assert "cp config-template.json config.json" not in dockerfile
    assert "CHATGPT_ON_WECHAT_CONFIG_PATH" not in entrypoint
    assert "config.json" not in entrypoint

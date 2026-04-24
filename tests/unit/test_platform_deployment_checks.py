from __future__ import annotations

from cow_platform.deployment.checks import DependencySettings, validate_environment


def test_test_deployment_requires_full_dependency_stack() -> None:
    settings = DependencySettings(
        environment="test",
        require_dependencies=False,
        database_url="postgresql://cowplatform:cowplatform@postgres:5432/cowplatform_test",
        redis_url="redis://redis:6379/0",
        qdrant_url="http://qdrant:6333",
        minio_endpoint="http://minio:9000",
        minio_access_key="cowplatform",
        minio_secret_key="cowplatform123",
        minio_bucket="cowagent",
        web_tenant_auth=True,
    )

    assert validate_environment(settings) == [
        "COW_PLATFORM_REQUIRE_DEPENDENCIES must be true in test/production deployments"
    ]


def test_production_deployment_rejects_localhost_and_default_secrets(monkeypatch) -> None:
    monkeypatch.setenv("COW_PLATFORM_DATABASE_URL", "postgresql://cowplatform:cowplatform@127.0.0.1:55432/cowplatform")
    monkeypatch.setenv("COW_PLATFORM_REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("COW_PLATFORM_QDRANT_URL", "http://127.0.0.1:6333")
    monkeypatch.setenv("COW_PLATFORM_MINIO_ENDPOINT", "http://127.0.0.1:9000")
    monkeypatch.setenv("COW_PLATFORM_MINIO_ACCESS_KEY", "cowplatform")
    monkeypatch.setenv("COW_PLATFORM_MINIO_SECRET_KEY", "cowplatform123")
    monkeypatch.setenv("COW_PLATFORM_MINIO_BUCKET", "cowagent")

    settings = DependencySettings(
        environment="production",
        require_dependencies=True,
        database_url="postgresql://cowplatform:cowplatform@127.0.0.1:55432/cowplatform",
        redis_url="redis://localhost:6379/0",
        qdrant_url="http://127.0.0.1:6333",
        minio_endpoint="http://127.0.0.1:9000",
        minio_access_key="cowplatform",
        minio_secret_key="cowplatform123",
        minio_bucket="cowagent",
        web_tenant_auth=True,
    )

    errors = validate_environment(settings, strict_secrets=True)

    assert "COW_PLATFORM_DATABASE_URL must not point to localhost in production: 127.0.0.1" in errors
    assert "COW_PLATFORM_REDIS_URL must not point to localhost in production: localhost" in errors
    assert "COW_PLATFORM_QDRANT_URL must not point to localhost in production: 127.0.0.1" in errors
    assert "COW_PLATFORM_MINIO_ENDPOINT must not point to localhost in production: 127.0.0.1" in errors
    assert "COW_PLATFORM_DATABASE_URL password must be set to a non-default production secret" in errors
    assert "COW_PLATFORM_MINIO_SECRET_KEY must be set to a non-default production secret" in errors


def test_production_deployment_accepts_service_stack_with_strong_secrets(monkeypatch) -> None:
    monkeypatch.setenv("COW_PLATFORM_DATABASE_URL", "postgresql://cowplatform:strong-db-secret@postgres:5432/cowplatform")
    monkeypatch.setenv("COW_PLATFORM_REDIS_URL", "redis://redis:6379/0")
    monkeypatch.setenv("COW_PLATFORM_QDRANT_URL", "http://qdrant:6333")
    monkeypatch.setenv("COW_PLATFORM_MINIO_ENDPOINT", "http://minio:9000")
    monkeypatch.setenv("COW_PLATFORM_MINIO_ACCESS_KEY", "prod-access")
    monkeypatch.setenv("COW_PLATFORM_MINIO_SECRET_KEY", "prod-minio-secret")
    monkeypatch.setenv("COW_PLATFORM_MINIO_BUCKET", "cowagent-prod")

    settings = DependencySettings(
        environment="production",
        require_dependencies=True,
        database_url="postgresql://cowplatform:strong-db-secret@postgres:5432/cowplatform",
        redis_url="redis://redis:6379/0",
        qdrant_url="http://qdrant:6333",
        minio_endpoint="http://minio:9000",
        minio_access_key="prod-access",
        minio_secret_key="prod-minio-secret",
        minio_bucket="cowagent-prod",
        web_tenant_auth=True,
    )

    assert validate_environment(settings, strict_secrets=True) == []

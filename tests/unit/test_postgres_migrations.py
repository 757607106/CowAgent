from cow_platform.db import postgres


def test_platform_migration_versions_are_unique():
    versions = [migration.version for migration in postgres.list_migrations()]

    assert versions
    assert len(versions) == len(set(versions))
    assert "0001_platform_schema" in versions


def test_platform_schema_migration_contains_runtime_and_vector_tables():
    statements = "\n".join(
        statement
        for migration in postgres.list_migrations()
        for statement in migration.statements
    )

    assert "platform_scheduled_tasks" in statements
    assert "platform_channel_runtime_leases" in statements
    assert "platform_runtime_state" in statements
    assert "platform_skill_configs" in statements
    assert "embedding_vector" in statements
    assert "CREATE EXTENSION IF NOT EXISTS vector" in statements

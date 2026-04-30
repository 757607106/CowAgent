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


def test_capability_config_migration_backfills_existing_partial_table_before_indexes():
    migration = next(
        migration
        for migration in postgres.list_migrations()
        if migration.version == "0003_capability_configs"
    )
    statements = list(migration.statements)
    backfill_index = statements.index(
        "ALTER TABLE platform_capability_configs ADD COLUMN IF NOT EXISTS is_default BOOLEAN NOT NULL DEFAULT false"
    )
    default_index = next(
        index
        for index, statement in enumerate(statements)
        if "idx_platform_capability_configs_platform_default" in statement
    )

    assert backfill_index < default_index

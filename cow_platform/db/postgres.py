from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

try:
    from psycopg_pool import ConnectionPool
except Exception:  # pragma: no cover - optional dependency in legacy installs
    ConnectionPool = None


DEFAULT_DATABASE_URL = "postgresql://cowplatform:cowplatform@127.0.0.1:55432/cowplatform"

_migration_lock = threading.Lock()
_migrated_urls: set[str] = set()
_pool_lock = threading.Lock()
_pools: dict[str, object] = {}


@dataclass(frozen=True, slots=True)
class SchemaMigration:
    version: str
    statements: tuple[str, ...]


_MIGRATION_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS platform_schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL
)
"""


def get_database_url() -> str:
    return (
        os.getenv("COW_PLATFORM_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or DEFAULT_DATABASE_URL
    )


def jsonb(value):
    return Jsonb(value if value is not None else {})


@contextmanager
def connect() -> Iterator[psycopg.Connection]:
    ensure_database()
    database_url = get_database_url()
    pool = _get_pool(database_url)
    if pool is None:
        with psycopg.connect(database_url, row_factory=dict_row) as conn:
            yield conn
        return

    with pool.connection() as conn:
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def _pool_size(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, "") or default))
    except (TypeError, ValueError):
        return default


def _get_pool(database_url: str):
    if ConnectionPool is None:
        return None
    if os.getenv("COW_PLATFORM_DISABLE_DB_POOL", "").strip().lower() in {"1", "true", "yes", "on"}:
        return None
    pool = _pools.get(database_url)
    if pool is not None:
        return pool
    with _pool_lock:
        pool = _pools.get(database_url)
        if pool is not None:
            return pool
        pool = ConnectionPool(
            conninfo=database_url,
            min_size=_pool_size("COW_PLATFORM_DB_POOL_MIN_SIZE", 1),
            max_size=_pool_size("COW_PLATFORM_DB_POOL_MAX_SIZE", 8),
            kwargs={"row_factory": dict_row},
        )
        _pools[database_url] = pool
        return pool


def close_pools() -> None:
    with _pool_lock:
        pools = list(_pools.values())
        _pools.clear()
    for pool in pools:
        try:
            pool.close()
        except Exception:
            pass


def ensure_database() -> None:
    run_migrations(get_database_url())


def list_migrations() -> tuple[SchemaMigration, ...]:
    return _MIGRATIONS


def run_migrations(database_url: str | None = None) -> list[str]:
    database_url = database_url or get_database_url()
    if database_url in _migrated_urls:
        return []
    with _migration_lock:
        if database_url in _migrated_urls:
            return []
        applied_now: list[str] = []
        with psycopg.connect(database_url, autocommit=True, row_factory=dict_row) as conn:
            conn.execute(_MIGRATION_TABLE_SCHEMA)
            applied = {
                row["version"]
                for row in conn.execute("SELECT version FROM platform_schema_migrations").fetchall()
            }
            for migration in _MIGRATIONS:
                if migration.version in applied:
                    continue
                for statement in migration.statements:
                    conn.execute(statement)
                conn.execute(
                    """
                    INSERT INTO platform_schema_migrations (version, applied_at)
                    VALUES (%s, NOW()::text)
                    ON CONFLICT (version) DO NOTHING
                    """,
                    (migration.version,),
                )
                applied_now.append(migration.version)
        _migrated_urls.add(database_url)
    return applied_now


_SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS platform_settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at BIGINT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS platform_tenants (
        tenant_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active',
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at BIGINT NOT NULL,
        updated_at BIGINT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS platform_users (
        user_id TEXT PRIMARY KEY,
        name TEXT NOT NULL DEFAULT '',
        role TEXT NOT NULL DEFAULT 'platform_super_admin',
        status TEXT NOT NULL DEFAULT 'active',
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at BIGINT NOT NULL,
        updated_at BIGINT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS platform_model_configs (
        model_config_id TEXT PRIMARY KEY,
        scope TEXT NOT NULL,
        tenant_id TEXT NOT NULL DEFAULT '',
        provider TEXT NOT NULL,
        model_name TEXT NOT NULL,
        display_name TEXT NOT NULL DEFAULT '',
        api_key TEXT NOT NULL DEFAULT '',
        api_base TEXT NOT NULL DEFAULT '',
        enabled BOOLEAN NOT NULL DEFAULT true,
        is_public BOOLEAN NOT NULL DEFAULT true,
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_by TEXT NOT NULL DEFAULT '',
        created_at BIGINT NOT NULL,
        updated_at BIGINT NOT NULL,
        CHECK (scope IN ('platform', 'tenant')),
        CHECK (scope != 'tenant' OR tenant_id != '')
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_platform_model_configs_scope ON platform_model_configs (scope, tenant_id, enabled)",
    """
    CREATE TABLE IF NOT EXISTS platform_channel_configs (
        tenant_id TEXT NOT NULL REFERENCES platform_tenants(tenant_id) ON DELETE CASCADE,
        channel_config_id TEXT NOT NULL,
        name TEXT NOT NULL,
        channel_type TEXT NOT NULL,
        config JSONB NOT NULL DEFAULT '{}'::jsonb,
        enabled BOOLEAN NOT NULL DEFAULT true,
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_by TEXT NOT NULL DEFAULT '',
        created_at BIGINT NOT NULL,
        updated_at BIGINT NOT NULL,
        PRIMARY KEY (tenant_id, channel_config_id),
        UNIQUE (channel_config_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_platform_channel_configs_scope ON platform_channel_configs (tenant_id, channel_type, enabled)",
    """
    CREATE TABLE IF NOT EXISTS platform_agents (
        tenant_id TEXT NOT NULL REFERENCES platform_tenants(tenant_id) ON DELETE CASCADE,
        agent_id TEXT NOT NULL,
        name TEXT NOT NULL,
        version INTEGER NOT NULL DEFAULT 1,
        model TEXT NOT NULL DEFAULT '',
        model_config_id TEXT NOT NULL DEFAULT '',
        system_prompt TEXT NOT NULL DEFAULT '',
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        tools JSONB NOT NULL DEFAULT '[]'::jsonb,
        skills JSONB NOT NULL DEFAULT '[]'::jsonb,
        knowledge_enabled BOOLEAN NOT NULL DEFAULT false,
        mcp_servers JSONB NOT NULL DEFAULT '{}'::jsonb,
        versions JSONB NOT NULL DEFAULT '[]'::jsonb,
        created_at BIGINT NOT NULL,
        updated_at BIGINT NOT NULL,
        PRIMARY KEY (tenant_id, agent_id)
    )
    """,
    "ALTER TABLE platform_agents ADD COLUMN IF NOT EXISTS model_config_id TEXT NOT NULL DEFAULT ''",
    """
    CREATE TABLE IF NOT EXISTS platform_mcp_servers (
        tenant_id TEXT NOT NULL REFERENCES platform_tenants(tenant_id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        command TEXT NOT NULL,
        args JSONB NOT NULL DEFAULT '[]'::jsonb,
        env JSONB NOT NULL DEFAULT '{}'::jsonb,
        enabled BOOLEAN NOT NULL DEFAULT true,
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at BIGINT NOT NULL,
        updated_at BIGINT NOT NULL,
        PRIMARY KEY (tenant_id, name)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_platform_mcp_servers_scope ON platform_mcp_servers (tenant_id, enabled)",
    """
    CREATE TABLE IF NOT EXISTS platform_tenant_users (
        tenant_id TEXT NOT NULL REFERENCES platform_tenants(tenant_id) ON DELETE CASCADE,
        user_id TEXT NOT NULL,
        name TEXT NOT NULL DEFAULT '',
        role TEXT NOT NULL DEFAULT 'member',
        status TEXT NOT NULL DEFAULT 'active',
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at BIGINT NOT NULL,
        updated_at BIGINT NOT NULL,
        PRIMARY KEY (tenant_id, user_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS platform_tenant_user_identities (
        tenant_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        channel_type TEXT NOT NULL,
        external_user_id TEXT NOT NULL,
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at BIGINT NOT NULL,
        updated_at BIGINT NOT NULL,
        PRIMARY KEY (tenant_id, channel_type, external_user_id),
        FOREIGN KEY (tenant_id, user_id)
            REFERENCES platform_tenant_users(tenant_id, user_id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS platform_bindings (
        tenant_id TEXT NOT NULL REFERENCES platform_tenants(tenant_id) ON DELETE CASCADE,
        binding_id TEXT NOT NULL,
        name TEXT NOT NULL,
        channel_type TEXT NOT NULL,
        channel_config_id TEXT NOT NULL DEFAULT '',
        agent_id TEXT NOT NULL,
        version INTEGER NOT NULL DEFAULT 1,
        enabled BOOLEAN NOT NULL DEFAULT true,
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at BIGINT NOT NULL,
        updated_at BIGINT NOT NULL,
        PRIMARY KEY (tenant_id, binding_id),
        UNIQUE (binding_id),
        FOREIGN KEY (tenant_id, agent_id)
            REFERENCES platform_agents(tenant_id, agent_id) ON DELETE CASCADE
    )
    """,
    "ALTER TABLE platform_bindings ADD COLUMN IF NOT EXISTS channel_config_id TEXT NOT NULL DEFAULT ''",
    "CREATE INDEX IF NOT EXISTS idx_platform_bindings_channel_config ON platform_bindings (channel_config_id)",
    """
    CREATE TABLE IF NOT EXISTS platform_pricing (
        model TEXT PRIMARY KEY,
        input_price_per_million DOUBLE PRECISION NOT NULL DEFAULT 0,
        output_price_per_million DOUBLE PRECISION NOT NULL DEFAULT 0,
        currency TEXT NOT NULL DEFAULT 'CNY',
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS platform_quotas (
        scope_type TEXT NOT NULL,
        tenant_id TEXT NOT NULL REFERENCES platform_tenants(tenant_id) ON DELETE CASCADE,
        agent_id TEXT NOT NULL DEFAULT '',
        max_requests_per_day INTEGER NOT NULL DEFAULT 0,
        max_tokens_per_day INTEGER NOT NULL DEFAULT 0,
        enabled BOOLEAN NOT NULL DEFAULT true,
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        PRIMARY KEY (scope_type, tenant_id, agent_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS platform_usage_records (
        event_id TEXT PRIMARY KEY,
        request_id TEXT NOT NULL,
        tenant_id TEXT NOT NULL,
        agent_id TEXT NOT NULL,
        binding_id TEXT NOT NULL DEFAULT '',
        session_id TEXT NOT NULL DEFAULT '',
        channel_type TEXT NOT NULL DEFAULT '',
        model TEXT NOT NULL DEFAULT '',
        prompt_tokens INTEGER NOT NULL DEFAULT 0,
        completion_tokens INTEGER NOT NULL DEFAULT 0,
        total_tokens INTEGER NOT NULL DEFAULT 0,
        token_source TEXT NOT NULL DEFAULT 'estimated',
        request_count INTEGER NOT NULL DEFAULT 1,
        tool_call_count INTEGER NOT NULL DEFAULT 0,
        mcp_call_count INTEGER NOT NULL DEFAULT 0,
        tool_error_count INTEGER NOT NULL DEFAULT 0,
        tool_execution_time_ms INTEGER NOT NULL DEFAULT 0,
        estimated_cost DOUBLE PRECISION NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_platform_usage_scope ON platform_usage_records (tenant_id, agent_id, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_platform_usage_tenant_time ON platform_usage_records (tenant_id, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_platform_usage_model_time ON platform_usage_records (tenant_id, model, created_at)",
    """
    CREATE TABLE IF NOT EXISTS platform_jobs (
        job_id TEXT PRIMARY KEY,
        job_type TEXT NOT NULL,
        tenant_id TEXT NOT NULL,
        agent_id TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL DEFAULT 'pending',
        payload JSONB NOT NULL DEFAULT '{}'::jsonb,
        result JSONB NOT NULL DEFAULT '{}'::jsonb,
        error_message TEXT NOT NULL DEFAULT '',
        attempts INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        started_at TEXT NOT NULL DEFAULT '',
        completed_at TEXT NOT NULL DEFAULT '',
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_platform_jobs_claim ON platform_jobs (status, job_type, created_at)",
    """
    CREATE TABLE IF NOT EXISTS platform_scheduled_tasks (
        tenant_id TEXT NOT NULL,
        agent_id TEXT NOT NULL DEFAULT '',
        task_id TEXT NOT NULL,
        binding_id TEXT NOT NULL DEFAULT '',
        channel_config_id TEXT NOT NULL DEFAULT '',
        session_id TEXT NOT NULL DEFAULT '',
        name TEXT NOT NULL DEFAULT '',
        enabled BOOLEAN NOT NULL DEFAULT true,
        schedule JSONB NOT NULL DEFAULT '{}'::jsonb,
        action JSONB NOT NULL DEFAULT '{}'::jsonb,
        next_run_at TEXT NOT NULL DEFAULT '',
        last_run_at TEXT NOT NULL DEFAULT '',
        last_error TEXT NOT NULL DEFAULT '',
        last_error_at TEXT NOT NULL DEFAULT '',
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        PRIMARY KEY (tenant_id, agent_id, task_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_platform_scheduled_tasks_due ON platform_scheduled_tasks (enabled, next_run_at)",
    "CREATE INDEX IF NOT EXISTS idx_platform_scheduled_tasks_scope ON platform_scheduled_tasks (tenant_id, agent_id, enabled)",
    "CREATE INDEX IF NOT EXISTS idx_platform_scheduled_tasks_binding ON platform_scheduled_tasks (binding_id)",
    "CREATE INDEX IF NOT EXISTS idx_platform_scheduled_tasks_channel_config ON platform_scheduled_tasks (channel_config_id)",
    """
    CREATE TABLE IF NOT EXISTS platform_channel_runtime_leases (
        channel_config_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        channel_type TEXT NOT NULL,
        owner_id TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'running',
        lease_until TEXT NOT NULL,
        heartbeat_at TEXT NOT NULL,
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_platform_channel_runtime_leases_owner ON platform_channel_runtime_leases (owner_id, status)",
    "CREATE INDEX IF NOT EXISTS idx_platform_channel_runtime_leases_expiry ON platform_channel_runtime_leases (status, lease_until)",
    """
    CREATE TABLE IF NOT EXISTS platform_audit_logs (
        audit_id TEXT PRIMARY KEY,
        action TEXT NOT NULL,
        resource_type TEXT NOT NULL,
        resource_id TEXT NOT NULL,
        status TEXT NOT NULL,
        tenant_id TEXT NOT NULL DEFAULT '',
        agent_id TEXT NOT NULL DEFAULT '',
        actor TEXT NOT NULL DEFAULT 'system',
        created_at TEXT NOT NULL,
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_platform_audit_scope ON platform_audit_logs (tenant_id, agent_id, created_at)",
    """
    CREATE TABLE IF NOT EXISTS platform_conversation_sessions (
        tenant_id TEXT NOT NULL,
        agent_id TEXT NOT NULL,
        session_id TEXT NOT NULL,
        channel_type TEXT NOT NULL DEFAULT '',
        title TEXT NOT NULL DEFAULT '',
        context_start_seq INTEGER NOT NULL DEFAULT 0,
        created_at BIGINT NOT NULL,
        last_active BIGINT NOT NULL,
        msg_count INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (tenant_id, agent_id, session_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS platform_conversation_messages (
        id BIGSERIAL PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        agent_id TEXT NOT NULL,
        session_id TEXT NOT NULL,
        seq INTEGER NOT NULL,
        role TEXT NOT NULL,
        content JSONB NOT NULL,
        created_at BIGINT NOT NULL,
        UNIQUE (tenant_id, agent_id, session_id, seq),
        FOREIGN KEY (tenant_id, agent_id, session_id)
            REFERENCES platform_conversation_sessions(tenant_id, agent_id, session_id)
            ON DELETE CASCADE
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_platform_messages_session ON platform_conversation_messages (tenant_id, agent_id, session_id, seq)",
    "CREATE INDEX IF NOT EXISTS idx_platform_sessions_last_active ON platform_conversation_sessions (tenant_id, agent_id, last_active)",
    """
    CREATE TABLE IF NOT EXISTS platform_memory_chunks (
        namespace TEXT NOT NULL,
        id TEXT NOT NULL,
        user_id TEXT,
        scope TEXT NOT NULL DEFAULT 'shared',
        source TEXT NOT NULL DEFAULT 'memory',
        path TEXT NOT NULL,
        start_line INTEGER NOT NULL,
        end_line INTEGER NOT NULL,
        text TEXT NOT NULL,
        embedding JSONB,
        hash TEXT NOT NULL,
        metadata JSONB,
        created_at BIGINT NOT NULL,
        updated_at BIGINT NOT NULL,
        PRIMARY KEY (namespace, id)
    )
    """,
    """
    DO $$
    BEGIN
        CREATE EXTENSION IF NOT EXISTS vector;
    EXCEPTION
        WHEN undefined_file OR insufficient_privilege OR feature_not_supported THEN
            RAISE NOTICE 'pgvector extension is not available; keep JSONB embedding fallback';
    END $$;
    """,
    """
    DO $$
    BEGIN
        IF to_regtype('vector') IS NOT NULL THEN
            EXECUTE 'ALTER TABLE platform_memory_chunks ADD COLUMN IF NOT EXISTS embedding_vector vector';
        END IF;
    END $$;
    """,
    """
    DO $$
    BEGIN
        IF to_regtype('vector') IS NOT NULL
           AND EXISTS (
               SELECT 1
               FROM information_schema.columns
               WHERE table_name = 'platform_memory_chunks'
                 AND column_name = 'embedding_vector'
           ) THEN
            BEGIN
                EXECUTE 'UPDATE platform_memory_chunks
                         SET embedding_vector = embedding::text::vector
                         WHERE embedding IS NOT NULL
                           AND embedding_vector IS NULL
                           AND jsonb_typeof(embedding) = ''array''';
            EXCEPTION
                WHEN invalid_text_representation OR data_exception OR undefined_object OR undefined_column THEN
                    RAISE NOTICE 'skip memory embedding_vector backfill; JSONB embedding fallback remains available';
            END;
        END IF;
    END $$;
    """,
    """
    DO $$
    BEGIN
        IF to_regtype('vector') IS NOT NULL
           AND EXISTS (
               SELECT 1
               FROM information_schema.columns
               WHERE table_name = 'platform_memory_chunks'
                 AND column_name = 'embedding_vector'
           ) THEN
            BEGIN
                EXECUTE 'CREATE INDEX IF NOT EXISTS idx_platform_memory_embedding_vector
                         ON platform_memory_chunks
                         USING hnsw (embedding_vector vector_cosine_ops)
                         WHERE embedding_vector IS NOT NULL';
            EXCEPTION
                WHEN undefined_object OR undefined_column OR feature_not_supported OR insufficient_privilege OR data_exception THEN
                    RAISE NOTICE 'skip pgvector HNSW index; memory search can use JSONB fallback';
            END;
        END IF;
    END $$;
    """,
    "CREATE INDEX IF NOT EXISTS idx_platform_memory_user ON platform_memory_chunks (namespace, user_id)",
    "CREATE INDEX IF NOT EXISTS idx_platform_memory_scope ON platform_memory_chunks (namespace, scope)",
    "CREATE INDEX IF NOT EXISTS idx_platform_memory_hash ON platform_memory_chunks (namespace, path, hash)",
    """
    CREATE TABLE IF NOT EXISTS platform_memory_files (
        namespace TEXT NOT NULL,
        path TEXT NOT NULL,
        source TEXT NOT NULL DEFAULT 'memory',
        hash TEXT NOT NULL,
        mtime BIGINT NOT NULL,
        size BIGINT NOT NULL,
        updated_at BIGINT NOT NULL,
        PRIMARY KEY (namespace, path)
    )
    """,
]


_RUNTIME_STATE_SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS platform_runtime_state (
        scope_key TEXT PRIMARY KEY,
        resource_type TEXT NOT NULL,
        tenant_id TEXT NOT NULL DEFAULT '',
        agent_id TEXT NOT NULL DEFAULT '',
        config_version BIGINT NOT NULL DEFAULT 0,
        desired_state JSONB NOT NULL DEFAULT '{}'::jsonb,
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        invalidated_at TEXT NOT NULL DEFAULT '',
        updated_at TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_platform_runtime_state_scope ON platform_runtime_state (resource_type, tenant_id, agent_id)",
    """
    CREATE TABLE IF NOT EXISTS platform_skill_configs (
        tenant_id TEXT NOT NULL,
        agent_id TEXT NOT NULL,
        skill_name TEXT NOT NULL,
        config JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at BIGINT NOT NULL,
        updated_at BIGINT NOT NULL,
        PRIMARY KEY (tenant_id, agent_id, skill_name),
        FOREIGN KEY (tenant_id, agent_id)
            REFERENCES platform_agents(tenant_id, agent_id) ON DELETE CASCADE
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_platform_skill_configs_agent ON platform_skill_configs (tenant_id, agent_id)",
]


_CAPABILITY_CONFIG_SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS platform_capability_configs (
        capability_config_id TEXT PRIMARY KEY,
        scope TEXT NOT NULL,
        tenant_id TEXT NOT NULL DEFAULT '',
        capability TEXT NOT NULL,
        provider TEXT NOT NULL,
        model_name TEXT NOT NULL,
        display_name TEXT NOT NULL DEFAULT '',
        api_key TEXT NOT NULL DEFAULT '',
        api_base TEXT NOT NULL DEFAULT '',
        enabled BOOLEAN NOT NULL DEFAULT true,
        is_public BOOLEAN NOT NULL DEFAULT true,
        is_default BOOLEAN NOT NULL DEFAULT false,
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_by TEXT NOT NULL DEFAULT '',
        created_at BIGINT NOT NULL,
        updated_at BIGINT NOT NULL,
        CHECK (scope IN ('platform', 'tenant')),
        CHECK (scope != 'tenant' OR tenant_id != '')
    )
    """,
    "ALTER TABLE platform_capability_configs ADD COLUMN IF NOT EXISTS scope TEXT NOT NULL DEFAULT 'platform'",
    "ALTER TABLE platform_capability_configs ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE platform_capability_configs ADD COLUMN IF NOT EXISTS capability TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE platform_capability_configs ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'custom'",
    "ALTER TABLE platform_capability_configs ADD COLUMN IF NOT EXISTS model_name TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE platform_capability_configs ADD COLUMN IF NOT EXISTS display_name TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE platform_capability_configs ADD COLUMN IF NOT EXISTS api_key TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE platform_capability_configs ADD COLUMN IF NOT EXISTS api_base TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE platform_capability_configs ADD COLUMN IF NOT EXISTS enabled BOOLEAN NOT NULL DEFAULT true",
    "ALTER TABLE platform_capability_configs ADD COLUMN IF NOT EXISTS is_public BOOLEAN NOT NULL DEFAULT true",
    "ALTER TABLE platform_capability_configs ADD COLUMN IF NOT EXISTS is_default BOOLEAN NOT NULL DEFAULT false",
    "ALTER TABLE platform_capability_configs ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb",
    "ALTER TABLE platform_capability_configs ADD COLUMN IF NOT EXISTS created_by TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE platform_capability_configs ADD COLUMN IF NOT EXISTS created_at BIGINT NOT NULL DEFAULT 0",
    "ALTER TABLE platform_capability_configs ADD COLUMN IF NOT EXISTS updated_at BIGINT NOT NULL DEFAULT 0",
    "CREATE INDEX IF NOT EXISTS idx_platform_capability_configs_scope ON platform_capability_configs (scope, tenant_id, capability, enabled)",
    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_platform_capability_configs_platform_default
    ON platform_capability_configs (capability)
    WHERE scope = 'platform' AND is_default = true
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_platform_capability_configs_tenant_default
    ON platform_capability_configs (tenant_id, capability)
    WHERE scope = 'tenant' AND is_default = true
    """,
]


_MIGRATIONS = (
    SchemaMigration("0001_platform_schema", tuple(_SCHEMA)),
    SchemaMigration("0002_runtime_state_and_skill_configs", tuple(_RUNTIME_STATE_SCHEMA)),
    SchemaMigration("0003_capability_configs", tuple(_CAPABILITY_CONFIG_SCHEMA)),
)

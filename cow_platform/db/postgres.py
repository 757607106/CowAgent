from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


DEFAULT_DATABASE_URL = "postgresql://cowplatform:cowplatform@127.0.0.1:55432/cowplatform"

_migration_lock = threading.Lock()
_migrated_urls: set[str] = set()


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
    with psycopg.connect(get_database_url(), row_factory=dict_row) as conn:
        yield conn


def ensure_database() -> None:
    database_url = get_database_url()
    if database_url in _migrated_urls:
        return
    with _migration_lock:
        if database_url in _migrated_urls:
            return
        with psycopg.connect(database_url, autocommit=True) as conn:
            for statement in _SCHEMA:
                conn.execute(statement)
        _migrated_urls.add(database_url)


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
    CREATE TABLE IF NOT EXISTS platform_agents (
        tenant_id TEXT NOT NULL REFERENCES platform_tenants(tenant_id) ON DELETE CASCADE,
        agent_id TEXT NOT NULL,
        name TEXT NOT NULL,
        version INTEGER NOT NULL DEFAULT 1,
        model TEXT NOT NULL DEFAULT '',
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

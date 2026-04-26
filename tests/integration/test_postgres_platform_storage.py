from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import pytest

from agent.memory.conversation_store import ConversationStore
from agent.memory.storage import MemoryChunk, MemoryStorage
from config import conf
from cow_platform.db import connect
from cow_platform.services.agent_service import AgentService
from cow_platform.services.auth_service import TenantAuthService
from cow_platform.services.audit_service import AuditService
from cow_platform.services.binding_service import ChannelBindingService
from cow_platform.services.job_service import JobService
from cow_platform.services.pricing_service import PricingService
from cow_platform.services.quota_service import QuotaService
from cow_platform.services.tenant_service import TenantService
from cow_platform.services.tenant_user_service import TenantUserService
from tests.conftest import _platform_postgres_reset_skip_reason
from cow_platform.services.usage_service import UsageService


pytestmark = pytest.mark.integration


def _require_postgres() -> None:
    if not os.getenv("COW_PLATFORM_DATABASE_URL"):
        pytest.skip("COW_PLATFORM_DATABASE_URL is required for PostgreSQL integration tests")
    try:
        with connect() as conn:
            conn.execute("SELECT 1").fetchone()
    except Exception as exc:
        pytest.skip(f"PostgreSQL is not available: {exc}")


def _reset_platform_tables() -> None:
    reset_skip_reason = _platform_postgres_reset_skip_reason()
    if reset_skip_reason:
        pytest.skip(reset_skip_reason)
    with connect() as conn:
        conn.execute(
            """
            TRUNCATE
                platform_audit_logs,
                platform_usage_records,
                platform_jobs,
                platform_quotas,
                platform_pricing,
                platform_bindings,
                platform_tenant_user_identities,
                platform_tenant_users,
                platform_agents,
                platform_tenants,
                platform_conversation_messages,
                platform_conversation_sessions,
                platform_memory_chunks,
                platform_memory_files,
                platform_settings
            RESTART IDENTITY CASCADE
            """
        )
        conn.commit()


@pytest.fixture(autouse=True)
def postgres_clean_state(tmp_path: Path, monkeypatch):
    _require_postgres()
    _reset_platform_tables()
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "cow"))
    monkeypatch.setitem(conf(), "model", "test-model")
    monkeypatch.setitem(conf(), "knowledge", True)
    yield
    _reset_platform_tables()


def test_platform_control_plane_uses_postgresql_end_to_end() -> None:
    tenant_service = TenantService()
    tenant_user_service = TenantUserService(tenant_service=tenant_service)
    agent_service = AgentService(tenant_service=tenant_service)
    auth_service = TenantAuthService(
        tenant_service=tenant_service,
        tenant_user_service=tenant_user_service,
        agent_service=agent_service,
    )
    pricing_service = PricingService()
    usage_service = UsageService(pricing_service=pricing_service)
    quota_service = QuotaService(usage_service=usage_service)
    audit_service = AuditService()
    binding_service = ChannelBindingService(agent_service=agent_service, tenant_service=tenant_service)
    job_service = JobService(
        usage_service=usage_service,
        agent_service=agent_service,
        audit_service=audit_service,
    )

    registration = auth_service.register_tenant(
        tenant_id="tenant_pg",
        tenant_name="PostgreSQL Tenant",
        user_id="owner",
        password="strong-pass-123",
        name="Owner",
    )
    assert registration["tenant"]["tenant_id"] == "tenant_pg"
    assert registration["default_agent"]["tenant_id"] == "tenant_pg"

    session = auth_service.authenticate(
        tenant_id="tenant_pg",
        user_id="owner",
        password="strong-pass-123",
    )
    assert session.tenant_id == "tenant_pg"
    assert session.user_id == "owner"

    agent = agent_service.create_agent(
        tenant_id="tenant_pg",
        agent_id="support",
        name="Support Agent",
        model="model-pg",
        system_prompt="You are support.",
        tools=["read_file"],
        skills=["support_skill"],
        knowledge_enabled=True,
    )
    assert agent["tools"] == ["read_file"]
    assert agent["skills"] == ["support_skill"]

    binding = binding_service.create_binding(
        tenant_id="tenant_pg",
        binding_id="web-support",
        name="Web Support",
        channel_type="web",
        agent_id="support",
    )
    assert binding["binding_id"] == "web-support"

    pricing_service.upsert_pricing(
        model="model-pg",
        input_price_per_million=2,
        output_price_per_million=6,
    )
    quota_service.upsert_quota(
        scope_type="agent",
        tenant_id="tenant_pg",
        agent_id="support",
        max_requests_per_day=10,
        max_tokens_per_day=1000,
    )
    today = datetime.now().strftime("%Y-%m-%d")
    usage = usage_service.record_chat_usage(
        request_id="req-pg-1",
        tenant_id="tenant_pg",
        agent_id="support",
        binding_id="web-support",
        session_id="session-1",
        channel_type="web",
        model="model-pg",
        prompt_tokens=10,
        completion_tokens=20,
        token_source="provider",
        created_at=f"{today}T00:00:00",
    )
    assert usage["total_tokens"] == 30
    assert quota_service.check_request_allowed(
        tenant_id="tenant_pg",
        agent_id="support",
        prompt_tokens=1,
        day=today,
    )["allowed"] is True

    job = job_service.create_job(
        job_type="usage_report",
        tenant_id="tenant_pg",
        agent_id="support",
        payload={"day": today},
    )
    processed = job_service.run_once()
    assert processed["job_id"] == job["job_id"]
    assert processed["status"] == "completed"
    assert Path(processed["result"]["artifact_path"]).exists()

    audit_logs = audit_service.list_records(tenant_id="tenant_pg")
    assert any(item["resource_type"] == "job" for item in audit_logs)

    with connect() as conn:
        counts = {
            table: conn.execute(f"SELECT COUNT(*) AS cnt FROM {table}").fetchone()["cnt"]
            for table in (
                "platform_tenants",
                "platform_agents",
                "platform_tenant_users",
                "platform_bindings",
                "platform_usage_records",
                "platform_jobs",
                "platform_audit_logs",
            )
        }
    assert counts == {
        "platform_tenants": 2,
        "platform_agents": 2,
        "platform_tenant_users": 1,
        "platform_bindings": 1,
        "platform_usage_records": 1,
        "platform_jobs": 1,
        "platform_audit_logs": 1,
    }


def test_postgresql_conversation_and_memory_isolate_by_scope(tmp_path: Path) -> None:
    store_a = ConversationStore(tenant_id="tenant_pg", agent_id="agent_a")
    store_b = ConversationStore(tenant_id="tenant_pg", agent_id="agent_b")

    store_a.append_messages(
        "shared-session",
        [{"role": "user", "content": [{"type": "text", "text": "A only"}]}],
        channel_type="web",
    )
    store_b.append_messages(
        "shared-session",
        [{"role": "user", "content": [{"type": "text", "text": "B only"}]}],
        channel_type="web",
    )

    assert store_a.load_history_page("shared-session")["messages"][0]["content"] == "A only"
    assert store_b.load_history_page("shared-session")["messages"][0]["content"] == "B only"

    memory_a = MemoryStorage(tmp_path / "agent_a" / "memory" / "index.pg")
    memory_b = MemoryStorage(tmp_path / "agent_b" / "memory" / "index.pg")
    memory_a.save_chunk(
        MemoryChunk(
            id="chunk-1",
            user_id=None,
            scope="shared",
            source="memory",
            path="MEMORY.md",
            start_line=1,
            end_line=1,
            text="alpha tenant memory",
            embedding=[1.0, 0.0],
            hash=MemoryStorage.compute_hash("alpha tenant memory"),
        )
    )
    memory_b.save_chunk(
        MemoryChunk(
            id="chunk-1",
            user_id=None,
            scope="shared",
            source="memory",
            path="MEMORY.md",
            start_line=1,
            end_line=1,
            text="beta tenant memory",
            embedding=[0.0, 1.0],
            hash=MemoryStorage.compute_hash("beta tenant memory"),
        )
    )

    assert memory_a.search_keyword("alpha", limit=5)[0].snippet == "alpha tenant memory"
    assert memory_b.search_keyword("beta", limit=5)[0].snippet == "beta tenant memory"
    assert memory_a.search_vector([1.0, 0.0], limit=5)[0].snippet == "alpha tenant memory"
    assert memory_b.search_vector([0.0, 1.0], limit=5)[0].snippet == "beta tenant memory"

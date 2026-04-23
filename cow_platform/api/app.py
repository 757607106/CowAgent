from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from cow_platform.api.settings import PlatformSettings
from cow_platform.services.agent_service import AgentService, DEFAULT_TENANT_ID
from cow_platform.services.audit_service import AuditService
from cow_platform.services.binding_service import ChannelBindingService
from cow_platform.services.doctor_service import DoctorService
from cow_platform.services.job_service import JobService
from cow_platform.services.pricing_service import PricingService
from cow_platform.services.quota_service import QuotaService
from cow_platform.services.tenant_service import TenantService
from cow_platform.services.tenant_user_service import TenantUserService
from cow_platform.services.usage_service import UsageService


class AgentCreateRequest(BaseModel):
    tenant_id: str = Field(default=DEFAULT_TENANT_ID)
    agent_id: str | None = None
    name: str
    model: str = ""
    system_prompt: str = ""
    tools: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    knowledge_enabled: bool = False
    mcp_servers: dict[str, object] = Field(default_factory=dict)


class AgentUpdateRequest(BaseModel):
    tenant_id: str = Field(default=DEFAULT_TENANT_ID)
    name: str | None = None
    model: str | None = None
    system_prompt: str | None = None
    tools: list[str] | None = None
    skills: list[str] | None = None
    knowledge_enabled: bool | None = None
    mcp_servers: dict[str, object] | None = None


class TenantCreateRequest(BaseModel):
    tenant_id: str
    name: str
    status: str = "active"


class TenantUpdateRequest(BaseModel):
    name: str | None = None
    status: str | None = None


class TenantUserCreateRequest(BaseModel):
    tenant_id: str
    user_id: str
    name: str = ""
    role: str = "member"
    status: str = "active"
    metadata: dict[str, object] = Field(default_factory=dict)


class TenantUserUpdateRequest(BaseModel):
    name: str | None = None
    role: str | None = None
    status: str | None = None
    metadata: dict[str, object] | None = None


class TenantUserIdentityUpsertRequest(BaseModel):
    tenant_id: str
    user_id: str
    channel_type: str
    external_user_id: str
    metadata: dict[str, object] = Field(default_factory=dict)


class BindingCreateRequest(BaseModel):
    tenant_id: str = Field(default=DEFAULT_TENANT_ID)
    binding_id: str
    name: str
    channel_type: str
    agent_id: str
    enabled: bool = True
    metadata: dict[str, object] = Field(default_factory=dict)


class BindingUpdateRequest(BaseModel):
    tenant_id: str | None = None
    name: str | None = None
    channel_type: str | None = None
    agent_id: str | None = None
    enabled: bool | None = None
    metadata: dict[str, object] | None = None


class PricingUpsertRequest(BaseModel):
    model: str
    input_price_per_million: float = 0.0
    output_price_per_million: float = 0.0
    currency: str = "CNY"


class QuotaUpsertRequest(BaseModel):
    scope_type: str
    tenant_id: str
    agent_id: str = ""
    max_requests_per_day: int = 0
    max_tokens_per_day: int = 0
    enabled: bool = True


class JobCreateRequest(BaseModel):
    job_type: str
    tenant_id: str = Field(default=DEFAULT_TENANT_ID)
    agent_id: str = Field(default="default")
    payload: dict[str, object] = Field(default_factory=dict)


def create_app(settings: PlatformSettings | None = None) -> FastAPI:
    resolved_settings = settings or PlatformSettings.from_env()
    audit_service = AuditService()
    tenant_service = TenantService()
    agent_service = AgentService(tenant_service=tenant_service)
    tenant_user_service = TenantUserService(tenant_service=tenant_service)
    binding_service = ChannelBindingService(agent_service=agent_service, tenant_service=tenant_service)
    pricing_service = PricingService()
    usage_service = UsageService(pricing_service=pricing_service)
    quota_service = QuotaService(usage_service=usage_service)
    job_service = JobService(
        usage_service=usage_service,
        agent_service=agent_service,
        audit_service=audit_service,
    )
    doctor_service = DoctorService()
    app = FastAPI(
        title="CowAgent Platform",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
    )
    app.state.settings = resolved_settings

    def record_audit(
        *,
        action: str,
        resource_type: str,
        resource_id: str,
        tenant_id: str = "",
        agent_id: str = "",
        metadata: dict[str, object] | None = None,
    ) -> None:
        audit_service.record_event(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            tenant_id=tenant_id,
            agent_id=agent_id,
            metadata=metadata or {},
        )

    @app.get("/health")
    def health() -> dict[str, object]:
        return {
            "status": "ok",
            "service": "cow-platform",
            "mode": resolved_settings.mode,
        }

    @app.get("/ready")
    def ready() -> dict[str, object]:
        return {
            "status": "ready",
            "service": "cow-platform",
            "dependencies": {},
        }

    @app.get("/api/platform/tenants")
    def list_tenants() -> dict[str, object]:
        return {
            "status": "success",
            "tenants": tenant_service.list_tenant_records(),
        }

    @app.get("/api/platform/tenants/{tenant_id}")
    def get_tenant(tenant_id: str) -> dict[str, object]:
        definition = tenant_service.resolve_tenant(tenant_id)
        return {
            "status": "success",
            "tenant": tenant_service.serialize_tenant(definition),
        }

    @app.post("/api/platform/tenants")
    def create_tenant(payload: TenantCreateRequest) -> dict[str, object]:
        result = {
            "status": "success",
            "tenant": tenant_service.create_tenant(
                tenant_id=payload.tenant_id,
                name=payload.name,
                status=payload.status,
            ),
        }
        record_audit(
            action="create_tenant",
            resource_type="tenant",
            resource_id=result["tenant"]["tenant_id"],
            tenant_id=result["tenant"]["tenant_id"],
        )
        return result

    @app.put("/api/platform/tenants/{tenant_id}")
    def update_tenant(tenant_id: str, payload: TenantUpdateRequest) -> dict[str, object]:
        result = {
            "status": "success",
            "tenant": tenant_service.update_tenant(
                tenant_id=tenant_id,
                name=payload.name,
                status=payload.status,
            ),
        }
        record_audit(
            action="update_tenant",
            resource_type="tenant",
            resource_id=tenant_id,
            tenant_id=tenant_id,
        )
        return result

    @app.get("/api/platform/tenant-user-meta")
    def tenant_user_meta() -> dict[str, object]:
        return {
            "status": "success",
            "roles": list(tenant_user_service.list_roles()),
            "statuses": list(tenant_user_service.list_statuses()),
        }

    @app.get("/api/platform/tenant-users")
    def list_tenant_users(
        tenant_id: str = "",
        role: str = "",
        status: str = "",
    ) -> dict[str, object]:
        return {
            "status": "success",
            "tenant_users": tenant_user_service.list_user_records(
                tenant_id=tenant_id,
                role=role,
                status=status,
            ),
        }

    @app.get("/api/platform/tenants/{tenant_id}/users")
    def list_tenant_users_by_tenant(tenant_id: str, role: str = "", status: str = "") -> dict[str, object]:
        return {
            "status": "success",
            "tenant_users": tenant_user_service.list_user_records(
                tenant_id=tenant_id,
                role=role,
                status=status,
            ),
        }

    @app.get("/api/platform/tenant-users/{tenant_id}/{user_id}")
    def get_tenant_user(tenant_id: str, user_id: str) -> dict[str, object]:
        definition = tenant_user_service.resolve_user(tenant_id=tenant_id, user_id=user_id)
        return {
            "status": "success",
            "tenant_user": tenant_user_service.serialize_user(definition),
        }

    @app.post("/api/platform/tenant-users")
    def create_tenant_user(payload: TenantUserCreateRequest) -> dict[str, object]:
        result = {
            "status": "success",
            "tenant_user": tenant_user_service.create_user(
                tenant_id=payload.tenant_id,
                user_id=payload.user_id,
                name=payload.name,
                role=payload.role,
                status=payload.status,
                metadata=payload.metadata,
            ),
        }
        record_audit(
            action="create_tenant_user",
            resource_type="tenant_user",
            resource_id=f"{payload.tenant_id}:{payload.user_id}",
            tenant_id=payload.tenant_id,
            metadata={"role": result["tenant_user"]["role"]},
        )
        return result

    @app.put("/api/platform/tenant-users/{tenant_id}/{user_id}")
    def update_tenant_user(tenant_id: str, user_id: str, payload: TenantUserUpdateRequest) -> dict[str, object]:
        result = {
            "status": "success",
            "tenant_user": tenant_user_service.update_user(
                tenant_id=tenant_id,
                user_id=user_id,
                name=payload.name,
                role=payload.role,
                status=payload.status,
                metadata=payload.metadata,
            ),
        }
        record_audit(
            action="update_tenant_user",
            resource_type="tenant_user",
            resource_id=f"{tenant_id}:{user_id}",
            tenant_id=tenant_id,
            metadata={
                "role": result["tenant_user"]["role"],
                "status": result["tenant_user"]["status"],
            },
        )
        return result

    @app.delete("/api/platform/tenant-users/{tenant_id}/{user_id}")
    def delete_tenant_user(tenant_id: str, user_id: str) -> dict[str, object]:
        result = {
            "status": "success",
            "tenant_user": tenant_user_service.delete_user(
                tenant_id=tenant_id,
                user_id=user_id,
            ),
        }
        record_audit(
            action="delete_tenant_user",
            resource_type="tenant_user",
            resource_id=f"{tenant_id}:{user_id}",
            tenant_id=tenant_id,
        )
        return result

    @app.get("/api/platform/tenant-user-identities")
    def list_tenant_user_identities(
        tenant_id: str = "",
        user_id: str = "",
        channel_type: str = "",
    ) -> dict[str, object]:
        return {
            "status": "success",
            "identities": tenant_user_service.list_identity_records(
                tenant_id=tenant_id,
                user_id=user_id,
                channel_type=channel_type,
            ),
        }

    @app.post("/api/platform/tenant-user-identities")
    def upsert_tenant_user_identity(payload: TenantUserIdentityUpsertRequest) -> dict[str, object]:
        result = {
            "status": "success",
            "identity": tenant_user_service.bind_identity(
                tenant_id=payload.tenant_id,
                user_id=payload.user_id,
                channel_type=payload.channel_type,
                external_user_id=payload.external_user_id,
                metadata=payload.metadata,
            ),
        }
        record_audit(
            action="bind_tenant_user_identity",
            resource_type="tenant_user_identity",
            resource_id=f"{payload.tenant_id}:{payload.channel_type}:{payload.external_user_id}",
            tenant_id=payload.tenant_id,
            metadata={"user_id": payload.user_id},
        )
        return result

    @app.delete("/api/platform/tenant-user-identities/{tenant_id}/{channel_type}/{external_user_id}")
    def delete_tenant_user_identity(tenant_id: str, channel_type: str, external_user_id: str) -> dict[str, object]:
        result = {
            "status": "success",
            "identity": tenant_user_service.unbind_identity(
                tenant_id=tenant_id,
                channel_type=channel_type,
                external_user_id=external_user_id,
            ),
        }
        record_audit(
            action="unbind_tenant_user_identity",
            resource_type="tenant_user_identity",
            resource_id=f"{tenant_id}:{channel_type}:{external_user_id}",
            tenant_id=tenant_id,
        )
        return result

    @app.get("/api/platform/agents")
    def list_agents(tenant_id: str = DEFAULT_TENANT_ID) -> dict[str, object]:
        tenant_service.resolve_tenant(tenant_id)
        return {
            "status": "success",
            "agents": agent_service.list_agent_records(tenant_id),
        }

    @app.get("/api/platform/agents/{agent_id}")
    def get_agent(agent_id: str, tenant_id: str = DEFAULT_TENANT_ID) -> dict[str, object]:
        tenant_service.resolve_tenant(tenant_id)
        definition = agent_service.resolve_agent(tenant_id=tenant_id, agent_id=agent_id)
        return {
            "status": "success",
            "agent": agent_service.serialize_agent(definition),
        }

    @app.post("/api/platform/agents")
    def create_agent(payload: AgentCreateRequest) -> dict[str, object]:
        result = {
            "status": "success",
            "agent": agent_service.create_agent(
                tenant_id=payload.tenant_id,
                agent_id=payload.agent_id,
                name=payload.name,
                model=payload.model,
                system_prompt=payload.system_prompt,
                tools=payload.tools,
                skills=payload.skills,
                knowledge_enabled=payload.knowledge_enabled,
                mcp_servers=payload.mcp_servers,
            ),
        }
        record_audit(
            action="create_agent",
            resource_type="agent",
            resource_id=result["agent"]["agent_id"],
            tenant_id=result["agent"]["tenant_id"],
            agent_id=result["agent"]["agent_id"],
        )
        return result

    @app.put("/api/platform/agents/{agent_id}")
    def update_agent(agent_id: str, payload: AgentUpdateRequest) -> dict[str, object]:
        tenant_service.resolve_tenant(payload.tenant_id)
        result = {
            "status": "success",
            "agent": agent_service.update_agent(
                agent_id=agent_id,
                tenant_id=payload.tenant_id,
                name=payload.name,
                model=payload.model,
                system_prompt=payload.system_prompt,
                tools=payload.tools,
                skills=payload.skills,
                knowledge_enabled=payload.knowledge_enabled,
                mcp_servers=payload.mcp_servers,
            ),
        }
        # Runtime config changed: invalidate cached agent instances for this tenant-agent
        # so the next message uses the latest prompt/tool/skill/knowledge/mcp settings.
        try:
            from bridge.bridge import Bridge
            Bridge().get_agent_bridge().clear_agent_sessions(
                tenant_id=result["agent"]["tenant_id"],
                agent_id=agent_id,
            )
        except Exception:
            pass
        record_audit(
            action="update_agent",
            resource_type="agent",
            resource_id=agent_id,
            tenant_id=result["agent"]["tenant_id"],
            agent_id=agent_id,
        )
        return result

    @app.delete("/api/platform/agents/{agent_id}")
    def delete_agent(agent_id: str, tenant_id: str = DEFAULT_TENANT_ID) -> dict[str, object]:
        tenant_service.resolve_tenant(tenant_id)
        agent_service.resolve_agent(tenant_id=tenant_id, agent_id=agent_id)
        from cow_platform.repositories.agent_repository import FileAgentRepository
        repository = agent_service.repository
        key = repository._build_key(tenant_id, agent_id)
        with repository._lock:
            store = repository._load_store()
            if key not in store["agents"]:
                raise KeyError(f"agent not found: {agent_id}")
            del store["agents"][key]
            repository._save_store(store)
        record_audit(
            action="delete_agent",
            resource_type="agent",
            resource_id=agent_id,
            tenant_id=tenant_id,
            agent_id=agent_id,
        )
        return {"status": "success", "agent_id": agent_id}

    @app.get("/api/platform/bindings")
    def list_bindings(tenant_id: str = "", channel_type: str = "") -> dict[str, object]:
        return {
            "status": "success",
            "bindings": binding_service.list_binding_records(
                tenant_id=tenant_id,
                channel_type=channel_type,
            ),
        }

    @app.get("/api/platform/bindings/{binding_id}")
    def get_binding(binding_id: str, tenant_id: str = "") -> dict[str, object]:
        definition = binding_service.resolve_binding(binding_id=binding_id, tenant_id=tenant_id)
        return {
            "status": "success",
            "binding": binding_service.serialize_binding(definition),
        }

    @app.post("/api/platform/bindings")
    def create_binding(payload: BindingCreateRequest) -> dict[str, object]:
        result = {
            "status": "success",
            "binding": binding_service.create_binding(
                tenant_id=payload.tenant_id,
                binding_id=payload.binding_id,
                name=payload.name,
                channel_type=payload.channel_type,
                agent_id=payload.agent_id,
                enabled=payload.enabled,
                metadata=payload.metadata,
            ),
        }
        record_audit(
            action="create_binding",
            resource_type="binding",
            resource_id=result["binding"]["binding_id"],
            tenant_id=result["binding"]["tenant_id"],
            agent_id=result["binding"]["agent_id"],
        )
        return result

    @app.put("/api/platform/bindings/{binding_id}")
    def update_binding(binding_id: str, payload: BindingUpdateRequest) -> dict[str, object]:
        result = {
            "status": "success",
            "binding": binding_service.update_binding(
                binding_id=binding_id,
                tenant_id=payload.tenant_id or "",
                name=payload.name,
                channel_type=payload.channel_type,
                agent_id=payload.agent_id,
                enabled=payload.enabled,
                metadata=payload.metadata,
            ),
        }
        record_audit(
            action="update_binding",
            resource_type="binding",
            resource_id=binding_id,
            tenant_id=result["binding"]["tenant_id"],
            agent_id=result["binding"]["agent_id"],
        )
        return result

    @app.delete("/api/platform/bindings/{binding_id}")
    def delete_binding(binding_id: str, tenant_id: str = "") -> dict[str, object]:
        result = {
            "status": "success",
            "binding": binding_service.delete_binding(binding_id=binding_id, tenant_id=tenant_id),
        }
        record_audit(
            action="delete_binding",
            resource_type="binding",
            resource_id=binding_id,
            tenant_id=result["binding"]["tenant_id"],
            agent_id=result["binding"]["agent_id"],
        )
        return result

    @app.get("/api/platform/pricing")
    def list_pricing() -> dict[str, object]:
        return {
            "status": "success",
            "pricing": pricing_service.list_pricing_records(),
        }

    @app.post("/api/platform/pricing")
    def upsert_pricing(payload: PricingUpsertRequest) -> dict[str, object]:
        result = {
            "status": "success",
            "pricing": pricing_service.upsert_pricing(
                model=payload.model,
                input_price_per_million=payload.input_price_per_million,
                output_price_per_million=payload.output_price_per_million,
                currency=payload.currency,
            ),
        }
        record_audit(
            action="upsert_pricing",
            resource_type="pricing",
            resource_id=result["pricing"]["model"],
            metadata={"currency": result["pricing"]["currency"]},
        )
        return result

    @app.get("/api/platform/quotas")
    def list_quotas(scope_type: str = "", tenant_id: str = "", agent_id: str = "") -> dict[str, object]:
        return {
            "status": "success",
            "quotas": quota_service.list_quota_records(
                scope_type=scope_type,
                tenant_id=tenant_id,
                agent_id=agent_id,
            ),
        }

    @app.post("/api/platform/quotas")
    def upsert_quota(payload: QuotaUpsertRequest) -> dict[str, object]:
        result = {
            "status": "success",
            "quota": quota_service.upsert_quota(
                scope_type=payload.scope_type,
                tenant_id=payload.tenant_id,
                agent_id=payload.agent_id,
                max_requests_per_day=payload.max_requests_per_day,
                max_tokens_per_day=payload.max_tokens_per_day,
                enabled=payload.enabled,
            ),
        }
        record_audit(
            action="upsert_quota",
            resource_type="quota",
            resource_id=f"{payload.scope_type}:{payload.tenant_id}:{payload.agent_id}",
            tenant_id=payload.tenant_id,
            agent_id=payload.agent_id,
            metadata={"scope_type": payload.scope_type},
        )
        return result

    @app.get("/api/platform/usage")
    def list_usage(
        tenant_id: str = "",
        agent_id: str = "",
        day: str = "",
        request_id: str = "",
        limit: int = 100,
    ) -> dict[str, object]:
        return {
            "status": "success",
            "usage": usage_service.list_usage_records(
                tenant_id=tenant_id,
                agent_id=agent_id,
                day=day,
                request_id=request_id,
                limit=limit,
            ),
        }

    @app.get("/api/platform/costs")
    def get_cost_summary(tenant_id: str = "", agent_id: str = "", day: str = "") -> dict[str, object]:
        return {
            "status": "success",
            "summary": usage_service.summarize_usage(
                tenant_id=tenant_id,
                agent_id=agent_id,
                day=day,
            ),
        }

    @app.get("/api/platform/jobs")
    def list_jobs(
        status: str = "",
        tenant_id: str = "",
        agent_id: str = "",
        limit: int = 100,
    ) -> dict[str, object]:
        return {
            "status": "success",
            "jobs": job_service.list_job_records(
                status=status,
                tenant_id=tenant_id,
                agent_id=agent_id,
                limit=limit,
            ),
        }

    @app.get("/api/platform/jobs/{job_id}")
    def get_job(job_id: str) -> dict[str, object]:
        definition = job_service.get_job(job_id)
        return {
            "status": "success",
            "job": job_service.serialize_job(definition),
        }

    @app.post("/api/platform/jobs")
    def create_job(payload: JobCreateRequest) -> dict[str, object]:
        result = {
            "status": "success",
            "job": job_service.create_job(
                job_type=payload.job_type,
                tenant_id=payload.tenant_id,
                agent_id=payload.agent_id,
                payload=dict(payload.payload),
            ),
        }
        record_audit(
            action="create_job",
            resource_type="job",
            resource_id=result["job"]["job_id"],
            tenant_id=result["job"]["tenant_id"],
            agent_id=result["job"]["agent_id"],
            metadata={"job_type": result["job"]["job_type"]},
        )
        return result

    @app.get("/api/platform/audit-logs")
    def list_audit_logs(
        action: str = "",
        resource_type: str = "",
        tenant_id: str = "",
        agent_id: str = "",
        limit: int = 100,
    ) -> dict[str, object]:
        return {
            "status": "success",
            "audit_logs": audit_service.list_records(
                action=action,
                resource_type=resource_type,
                tenant_id=tenant_id,
                agent_id=agent_id,
                limit=limit,
            ),
        }

    @app.get("/api/platform/doctor")
    def get_doctor_report() -> dict[str, object]:
        return {
            "status": "success",
            "report": doctor_service.get_report(),
        }

    return app

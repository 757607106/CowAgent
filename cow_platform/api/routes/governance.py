from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI, Request

from cow_platform.api.security import MANAGE_ROLES, PlatformAuthorizer
from cow_platform.api.schemas import JobCreateRequest, PricingUpsertRequest, QuotaUpsertRequest
from cow_platform.services.audit_service import AuditService
from cow_platform.services.job_service import JobService
from cow_platform.services.pricing_service import PricingService
from cow_platform.services.quota_service import QuotaService
from cow_platform.services.usage_service import UsageService


def register_governance_routes(
    app: FastAPI,
    *,
    pricing_service: PricingService,
    quota_service: QuotaService,
    usage_service: UsageService,
    job_service: JobService,
    audit_service: AuditService,
    authorizer: PlatformAuthorizer,
    record_audit: Callable[..., None],
) -> None:
    @app.get("/api/platform/pricing")
    def list_pricing(request: Request) -> dict[str, object]:
        authorizer.require_session(request)
        return {
            "status": "success",
            "pricing": pricing_service.list_pricing_records(),
        }

    @app.post("/api/platform/pricing")
    def upsert_pricing(payload: PricingUpsertRequest, request: Request) -> dict[str, object]:
        authorizer.require_session(request, roles=MANAGE_ROLES)
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
    def list_quotas(request: Request, scope_type: str = "", tenant_id: str = "", agent_id: str = "") -> dict[str, object]:
        session = authorizer.require_session(request)
        tenant_id = authorizer.scope_tenant_id(session, tenant_id)
        return {
            "status": "success",
            "quotas": quota_service.list_quota_records(
                scope_type=scope_type,
                tenant_id=tenant_id,
                agent_id=agent_id,
            ),
        }

    @app.post("/api/platform/quotas")
    def upsert_quota(payload: QuotaUpsertRequest, request: Request) -> dict[str, object]:
        session = authorizer.require_session(request, roles=MANAGE_ROLES)
        tenant_id = authorizer.scope_tenant_id(session, payload.tenant_id)
        result = {
            "status": "success",
            "quota": quota_service.upsert_quota(
                scope_type=payload.scope_type,
                tenant_id=tenant_id,
                agent_id=payload.agent_id,
                max_requests_per_day=payload.max_requests_per_day,
                max_tokens_per_day=payload.max_tokens_per_day,
                enabled=payload.enabled,
            ),
        }
        record_audit(
            action="upsert_quota",
            resource_type="quota",
            resource_id=f"{payload.scope_type}:{tenant_id}:{payload.agent_id}",
            tenant_id=tenant_id,
            agent_id=payload.agent_id,
            metadata={"scope_type": payload.scope_type},
        )
        return result

    @app.get("/api/platform/usage")
    def list_usage(
        request: Request,
        tenant_id: str = "",
        agent_id: str = "",
        day: str = "",
        request_id: str = "",
        limit: int = 100,
    ) -> dict[str, object]:
        session = authorizer.require_session(request)
        tenant_id = authorizer.scope_tenant_id(session, tenant_id)
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
    def get_cost_summary(request: Request, tenant_id: str = "", agent_id: str = "", day: str = "") -> dict[str, object]:
        session = authorizer.require_session(request)
        tenant_id = authorizer.scope_tenant_id(session, tenant_id)
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
        request: Request,
        status: str = "",
        tenant_id: str = "",
        agent_id: str = "",
        limit: int = 100,
    ) -> dict[str, object]:
        session = authorizer.require_session(request)
        tenant_id = authorizer.scope_tenant_id(session, tenant_id)
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
    def get_job(job_id: str, request: Request) -> dict[str, object]:
        session = authorizer.require_session(request)
        definition = job_service.get_job(job_id)
        authorizer.scope_tenant_id(session, definition.tenant_id)
        return {
            "status": "success",
            "job": job_service.serialize_job(definition),
        }

    @app.post("/api/platform/jobs")
    def create_job(payload: JobCreateRequest, request: Request) -> dict[str, object]:
        session = authorizer.require_session(request, roles=MANAGE_ROLES)
        tenant_id = authorizer.scope_tenant_id(session, payload.tenant_id)
        result = {
            "status": "success",
            "job": job_service.create_job(
                job_type=payload.job_type,
                tenant_id=tenant_id,
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
        request: Request,
        action: str = "",
        resource_type: str = "",
        tenant_id: str = "",
        agent_id: str = "",
        limit: int = 100,
    ) -> dict[str, object]:
        session = authorizer.require_session(request, roles=MANAGE_ROLES)
        tenant_id = authorizer.scope_tenant_id(session, tenant_id)
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

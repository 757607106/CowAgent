from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI

from cow_platform.api.routes import (
    register_agent_binding_routes,
    register_auth_routes,
    register_channel_config_routes,
    register_governance_routes,
    register_model_config_routes,
    register_platform_admin_routes,
    register_system_routes,
    register_tenant_routes,
)
from cow_platform.api.security import PlatformAuthorizer
from cow_platform.api.settings import PlatformSettings
from cow_platform.services.agent_service import AgentService
from cow_platform.services.auth_service import TenantAuthService
from cow_platform.services.audit_service import AuditService
from cow_platform.services.binding_service import ChannelBindingService
from cow_platform.services.channel_config_service import ChannelConfigService
from cow_platform.services.doctor_service import DoctorService
from cow_platform.services.job_service import JobService
from cow_platform.services.model_config_service import ModelConfigService
from cow_platform.services.pricing_service import PricingService
from cow_platform.services.quota_service import QuotaService
from cow_platform.services.tenant_service import TenantService
from cow_platform.services.tenant_user_service import TenantUserService
from cow_platform.services.usage_service import UsageService


def create_app(settings: PlatformSettings | None = None) -> FastAPI:
    resolved_settings = settings or PlatformSettings.from_env()
    audit_service = AuditService()
    tenant_service = TenantService()
    agent_service = AgentService(tenant_service=tenant_service)
    tenant_user_service = TenantUserService(tenant_service=tenant_service)
    model_config_service = ModelConfigService(tenant_service=tenant_service)
    channel_config_service = ChannelConfigService(tenant_service=tenant_service)
    auth_service = TenantAuthService(
        tenant_service=tenant_service,
        tenant_user_service=tenant_user_service,
        agent_service=agent_service,
    )
    authorizer = PlatformAuthorizer(auth_service)
    binding_service = ChannelBindingService(
        agent_service=agent_service,
        tenant_service=tenant_service,
        channel_config_service=channel_config_service,
    )
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

    audit_callback: Callable[..., None] = record_audit

    register_system_routes(
        app,
        mode=resolved_settings.mode,
        doctor_service=doctor_service,
        authorizer=authorizer,
    )
    register_auth_routes(
        app,
        auth_service=auth_service,
        record_audit=audit_callback,
    )
    register_tenant_routes(
        app,
        tenant_service=tenant_service,
        tenant_user_service=tenant_user_service,
        authorizer=authorizer,
        record_audit=audit_callback,
    )
    register_platform_admin_routes(
        app,
        tenant_service=tenant_service,
        agent_service=agent_service,
        model_config_service=model_config_service,
        authorizer=authorizer,
        record_audit=audit_callback,
    )
    register_model_config_routes(
        app,
        model_config_service=model_config_service,
        authorizer=authorizer,
        record_audit=audit_callback,
    )
    register_channel_config_routes(
        app,
        channel_config_service=channel_config_service,
        authorizer=authorizer,
        record_audit=audit_callback,
    )
    register_agent_binding_routes(
        app,
        tenant_service=tenant_service,
        agent_service=agent_service,
        binding_service=binding_service,
        authorizer=authorizer,
        record_audit=audit_callback,
    )
    register_governance_routes(
        app,
        pricing_service=pricing_service,
        quota_service=quota_service,
        usage_service=usage_service,
        job_service=job_service,
        audit_service=audit_service,
        authorizer=authorizer,
        record_audit=audit_callback,
    )

    return app

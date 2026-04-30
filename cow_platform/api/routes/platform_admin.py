from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI, HTTPException, Request

from cow_platform.api.schemas import (
    CapabilityConfigCreateRequest,
    CapabilityConfigUpdateRequest,
    ModelConfigCreateRequest,
    ModelConfigUpdateRequest,
    TenantCreateRequest,
    TenantUpdateRequest,
)
from cow_platform.api.security import MANAGE_ROLES, PlatformAuthorizer
from cow_platform.services.agent_service import AgentService
from cow_platform.services.capability_config_service import CapabilityConfigService
from cow_platform.services.model_config_service import ModelConfigService
from cow_platform.services.tenant_service import TenantService


def register_platform_admin_routes(
    app: FastAPI,
    *,
    tenant_service: TenantService,
    agent_service: AgentService,
    model_config_service: ModelConfigService,
    capability_config_service: CapabilityConfigService,
    authorizer: PlatformAuthorizer,
    record_audit: Callable[..., None],
) -> None:
    @app.get("/api/platform/admin/tenants")
    def admin_list_tenants(request: Request) -> dict[str, object]:
        authorizer.require_platform_admin(request)
        return {"status": "success", "tenants": tenant_service.list_tenant_records()}

    @app.post("/api/platform/admin/tenants")
    def admin_create_tenant(payload: TenantCreateRequest, request: Request) -> dict[str, object]:
        authorizer.require_platform_admin(request)
        try:
            tenant = tenant_service.create_tenant(
                tenant_id=payload.tenant_id,
                name=payload.name,
                status=payload.status,
                metadata=payload.metadata,
            )
            agent_service.ensure_default_agent(tenant["tenant_id"])
            record_audit(
                action="platform_create_tenant",
                resource_type="tenant",
                resource_id=tenant["tenant_id"],
                tenant_id=tenant["tenant_id"],
            )
            return {"status": "success", "tenant": tenant}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.put("/api/platform/admin/tenants/{tenant_id}")
    def admin_update_tenant(tenant_id: str, payload: TenantUpdateRequest, request: Request) -> dict[str, object]:
        authorizer.require_platform_admin(request)
        try:
            tenant = tenant_service.update_tenant(
                tenant_id=tenant_id,
                name=payload.name,
                status=payload.status,
                metadata=payload.metadata,
            )
            record_audit(
                action="platform_update_tenant",
                resource_type="tenant",
                resource_id=tenant_id,
                tenant_id=tenant_id,
            )
            return {"status": "success", "tenant": tenant}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.delete("/api/platform/admin/tenants/{tenant_id}")
    def admin_delete_tenant(tenant_id: str, request: Request) -> dict[str, object]:
        authorizer.require_platform_admin(request)
        try:
            tenant = tenant_service.delete_tenant(tenant_id)
            record_audit(
                action="platform_delete_tenant",
                resource_type="tenant",
                resource_id=tenant_id,
                tenant_id=tenant_id,
            )
            return {"status": "success", "tenant": tenant}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/platform/admin/models")
    def admin_list_models(request: Request) -> dict[str, object]:
        authorizer.require_platform_admin(request)
        return {
            "status": "success",
            "providers": model_config_service.list_provider_options(scope="platform"),
            "models": [model_config_service.serialize_model(item) for item in model_config_service.list_platform_models()],
        }

    @app.post("/api/platform/admin/models")
    def admin_create_model(payload: ModelConfigCreateRequest, request: Request) -> dict[str, object]:
        session = authorizer.require_platform_admin(request)
        try:
            model = model_config_service.create_platform_model(
                provider=payload.provider,
                model_name=payload.model_name,
                display_name=payload.display_name,
                api_key=payload.api_key,
                api_base=payload.api_base,
                enabled=payload.enabled,
                is_public=payload.is_public,
                metadata=payload.metadata,
                created_by=session.user_id,
            )
            record_audit(
                action="platform_create_model",
                resource_type="model_config",
                resource_id=model["model_config_id"],
                metadata={"scope": "platform", "provider": model["provider"]},
            )
            return {"status": "success", "model": model}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.put("/api/platform/admin/models/{model_config_id}")
    def admin_update_model(model_config_id: str, payload: ModelConfigUpdateRequest, request: Request) -> dict[str, object]:
        authorizer.require_platform_admin(request)
        try:
            model = model_config_service.update_model(
                model_config_id,
                expected_scope="platform",
                provider=payload.provider,
                model_name=payload.model_name,
                display_name=payload.display_name,
                api_key=payload.api_key,
                api_base=payload.api_base,
                enabled=payload.enabled,
                is_public=payload.is_public,
                metadata=payload.metadata,
            )
            record_audit(
                action="platform_update_model",
                resource_type="model_config",
                resource_id=model_config_id,
                metadata={"scope": "platform"},
            )
            return {"status": "success", "model": model}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.delete("/api/platform/admin/models/{model_config_id}")
    def admin_delete_model(model_config_id: str, request: Request) -> dict[str, object]:
        authorizer.require_platform_admin(request)
        try:
            model = model_config_service.delete_model(model_config_id, expected_scope="platform")
            record_audit(
                action="platform_delete_model",
                resource_type="model_config",
                resource_id=model_config_id,
                metadata={"scope": "platform"},
            )
            return {"status": "success", "model": model}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/platform/admin/capability-configs")
    def admin_list_capability_configs(request: Request) -> dict[str, object]:
        authorizer.require_platform_admin(request)
        return {
            "status": "success",
            "capabilities": capability_config_service.list_capability_types(),
            "providers": capability_config_service.list_provider_options(),
            "configs": [
                capability_config_service.serialize_config(item)
                for item in capability_config_service.list_platform_configs()
            ],
        }

    @app.post("/api/platform/admin/capability-configs")
    def admin_create_capability_config(payload: CapabilityConfigCreateRequest, request: Request) -> dict[str, object]:
        session = authorizer.require_platform_admin(request)
        try:
            config = capability_config_service.create_platform_config(
                capability=payload.capability,
                provider=payload.provider,
                model_name=payload.model_name,
                display_name=payload.display_name,
                api_key=payload.api_key,
                api_base=payload.api_base,
                enabled=payload.enabled,
                is_public=payload.is_public,
                is_default=payload.is_default,
                metadata=payload.metadata,
                created_by=session.user_id,
            )
            record_audit(
                action="platform_create_capability_config",
                resource_type="capability_config",
                resource_id=config["capability_config_id"],
                metadata={"scope": "platform", "capability": config["capability"], "provider": config["provider"]},
            )
            return {"status": "success", "config": config}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.put("/api/platform/admin/capability-configs/{capability_config_id}")
    def admin_update_capability_config(
        capability_config_id: str,
        payload: CapabilityConfigUpdateRequest,
        request: Request,
    ) -> dict[str, object]:
        authorizer.require_platform_admin(request)
        try:
            config = capability_config_service.update_config(
                capability_config_id,
                expected_scope="platform",
                capability=payload.capability,
                provider=payload.provider,
                model_name=payload.model_name,
                display_name=payload.display_name,
                api_key=payload.api_key,
                api_base=payload.api_base,
                enabled=payload.enabled,
                is_public=payload.is_public,
                is_default=payload.is_default,
                metadata=payload.metadata,
            )
            record_audit(
                action="platform_update_capability_config",
                resource_type="capability_config",
                resource_id=capability_config_id,
                metadata={"scope": "platform"},
            )
            return {"status": "success", "config": config}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.delete("/api/platform/admin/capability-configs/{capability_config_id}")
    def admin_delete_capability_config(capability_config_id: str, request: Request) -> dict[str, object]:
        authorizer.require_platform_admin(request)
        try:
            config = capability_config_service.delete_config(capability_config_id, expected_scope="platform")
            record_audit(
                action="platform_delete_capability_config",
                resource_type="capability_config",
                resource_id=capability_config_id,
                metadata={"scope": "platform"},
            )
            return {"status": "success", "config": config}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


def register_model_config_routes(
    app: FastAPI,
    *,
    model_config_service: ModelConfigService,
    capability_config_service: CapabilityConfigService,
    authorizer: PlatformAuthorizer,
    record_audit: Callable[..., None],
) -> None:
    @app.get("/api/platform/models/available")
    def list_available_models(request: Request, tenant_id: str = "") -> dict[str, object]:
        session = authorizer.require_session(request)
        scoped_tenant_id = authorizer.scope_tenant_id(session, tenant_id)
        return {
            "status": "success",
            "models": [
                model_config_service.serialize_model(item)
                for item in model_config_service.list_available_models(scoped_tenant_id)
            ],
        }

    @app.get("/api/platform/tenant-models")
    def list_tenant_models(request: Request, tenant_id: str = "") -> dict[str, object]:
        session = authorizer.require_session(request)
        scoped_tenant_id = authorizer.scope_tenant_id(session, tenant_id)
        return {
            "status": "success",
            "providers": model_config_service.list_provider_options(scope="tenant"),
            "models": [
                model_config_service.serialize_model(item)
                for item in model_config_service.list_tenant_models(scoped_tenant_id)
            ],
        }

    @app.post("/api/platform/tenant-models")
    def create_tenant_model(payload: ModelConfigCreateRequest, request: Request, tenant_id: str = "") -> dict[str, object]:
        session = authorizer.require_session(request, roles=MANAGE_ROLES)
        scoped_tenant_id = authorizer.scope_tenant_id(session, tenant_id)
        try:
            model = model_config_service.create_tenant_model(
                tenant_id=scoped_tenant_id,
                provider=payload.provider,
                model_name=payload.model_name,
                display_name=payload.display_name,
                api_key=payload.api_key,
                api_base=payload.api_base,
                enabled=payload.enabled,
                metadata=payload.metadata,
                created_by=session.user_id,
            )
            record_audit(
                action="tenant_create_model",
                resource_type="model_config",
                resource_id=model["model_config_id"],
                tenant_id=scoped_tenant_id,
                metadata={"scope": "tenant", "provider": model["provider"]},
            )
            return {"status": "success", "model": model}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.put("/api/platform/tenant-models/{model_config_id}")
    def update_tenant_model(model_config_id: str, payload: ModelConfigUpdateRequest, request: Request) -> dict[str, object]:
        session = authorizer.require_session(request, roles=MANAGE_ROLES)
        try:
            model = model_config_service.update_model(
                model_config_id,
                expected_scope="tenant",
                tenant_id=session.tenant_id,
                provider=payload.provider,
                model_name=payload.model_name,
                display_name=payload.display_name,
                api_key=payload.api_key,
                api_base=payload.api_base,
                enabled=payload.enabled,
                is_public=False,
                metadata=payload.metadata,
            )
            record_audit(
                action="tenant_update_model",
                resource_type="model_config",
                resource_id=model_config_id,
                tenant_id=session.tenant_id,
                metadata={"scope": "tenant"},
            )
            return {"status": "success", "model": model}
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.delete("/api/platform/tenant-models/{model_config_id}")
    def delete_tenant_model(model_config_id: str, request: Request) -> dict[str, object]:
        session = authorizer.require_session(request, roles=MANAGE_ROLES)
        try:
            model = model_config_service.delete_model(
                model_config_id,
                expected_scope="tenant",
                tenant_id=session.tenant_id,
            )
            record_audit(
                action="tenant_delete_model",
                resource_type="model_config",
                resource_id=model_config_id,
                tenant_id=session.tenant_id,
                metadata={"scope": "tenant"},
            )
            return {"status": "success", "model": model}
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/platform/capability-configs/available")
    def list_available_capability_configs(request: Request, tenant_id: str = "") -> dict[str, object]:
        session = authorizer.require_session(request)
        scoped_tenant_id = authorizer.scope_tenant_id(session, tenant_id)
        return {
            "status": "success",
            "configs": [
                capability_config_service.serialize_config(item)
                for item in capability_config_service.list_available_configs(scoped_tenant_id)
            ],
        }

    @app.get("/api/platform/tenant-capability-configs")
    def list_tenant_capability_configs(request: Request, tenant_id: str = "") -> dict[str, object]:
        session = authorizer.require_session(request)
        scoped_tenant_id = authorizer.scope_tenant_id(session, tenant_id)
        return {
            "status": "success",
            "capabilities": capability_config_service.list_capability_types(),
            "providers": capability_config_service.list_provider_options(),
            "configs": [
                capability_config_service.serialize_config(item)
                for item in capability_config_service.list_tenant_configs(scoped_tenant_id)
            ],
        }

    @app.post("/api/platform/tenant-capability-configs")
    def create_tenant_capability_config(
        payload: CapabilityConfigCreateRequest,
        request: Request,
        tenant_id: str = "",
    ) -> dict[str, object]:
        session = authorizer.require_session(request, roles=MANAGE_ROLES)
        scoped_tenant_id = authorizer.scope_tenant_id(session, tenant_id)
        try:
            config = capability_config_service.create_tenant_config(
                tenant_id=scoped_tenant_id,
                capability=payload.capability,
                provider=payload.provider,
                model_name=payload.model_name,
                display_name=payload.display_name,
                api_key=payload.api_key,
                api_base=payload.api_base,
                enabled=payload.enabled,
                is_default=payload.is_default,
                metadata=payload.metadata,
                created_by=session.user_id,
            )
            record_audit(
                action="tenant_create_capability_config",
                resource_type="capability_config",
                resource_id=config["capability_config_id"],
                tenant_id=scoped_tenant_id,
                metadata={"scope": "tenant", "capability": config["capability"], "provider": config["provider"]},
            )
            return {"status": "success", "config": config}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.put("/api/platform/tenant-capability-configs/{capability_config_id}")
    def update_tenant_capability_config(
        capability_config_id: str,
        payload: CapabilityConfigUpdateRequest,
        request: Request,
    ) -> dict[str, object]:
        session = authorizer.require_session(request, roles=MANAGE_ROLES)
        try:
            config = capability_config_service.update_config(
                capability_config_id,
                expected_scope="tenant",
                tenant_id=session.tenant_id,
                capability=payload.capability,
                provider=payload.provider,
                model_name=payload.model_name,
                display_name=payload.display_name,
                api_key=payload.api_key,
                api_base=payload.api_base,
                enabled=payload.enabled,
                is_public=False,
                is_default=payload.is_default,
                metadata=payload.metadata,
            )
            record_audit(
                action="tenant_update_capability_config",
                resource_type="capability_config",
                resource_id=capability_config_id,
                tenant_id=session.tenant_id,
                metadata={"scope": "tenant"},
            )
            return {"status": "success", "config": config}
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.delete("/api/platform/tenant-capability-configs/{capability_config_id}")
    def delete_tenant_capability_config(capability_config_id: str, request: Request) -> dict[str, object]:
        session = authorizer.require_session(request, roles=MANAGE_ROLES)
        try:
            config = capability_config_service.delete_config(
                capability_config_id,
                expected_scope="tenant",
                tenant_id=session.tenant_id,
            )
            record_audit(
                action="tenant_delete_capability_config",
                resource_type="capability_config",
                resource_id=capability_config_id,
                tenant_id=session.tenant_id,
                metadata={"scope": "tenant"},
            )
            return {"status": "success", "config": config}
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

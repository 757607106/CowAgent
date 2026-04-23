from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI

from cow_platform.api.schemas import (
    TenantCreateRequest,
    TenantUpdateRequest,
    TenantUserCreateRequest,
    TenantUserIdentityUpsertRequest,
    TenantUserUpdateRequest,
)
from cow_platform.services.tenant_service import TenantService
from cow_platform.services.tenant_user_service import TenantUserService


def register_tenant_routes(
    app: FastAPI,
    *,
    tenant_service: TenantService,
    tenant_user_service: TenantUserService,
    record_audit: Callable[..., None],
) -> None:
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

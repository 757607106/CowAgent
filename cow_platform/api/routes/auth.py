from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI, HTTPException, Request

from cow_platform.api.schemas import PlatformAdminRegisterRequest, TenantLoginRequest, TenantRegisterRequest
from cow_platform.services.auth_service import TenantAuthService


def register_auth_routes(
    app: FastAPI,
    *,
    auth_service: TenantAuthService,
    record_audit: Callable[..., None] | None = None,
) -> None:
    @app.post("/api/platform/auth/register")
    def register_tenant(payload: TenantRegisterRequest) -> dict[str, object]:
        try:
            result = auth_service.register_tenant(
                tenant_id=payload.tenant_id,
                tenant_name=payload.tenant_name,
                user_id=payload.user_id,
                account=payload.account,
                name=payload.user_name,
                password=payload.password,
            )
            if payload.account:
                session = auth_service.authenticate_account(
                    account=payload.account,
                    password=payload.password,
                )
            else:
                session = auth_service.authenticate(
                    tenant_id=result["tenant"]["tenant_id"],
                    user_id=result["tenant_user"]["user_id"],
                    password=payload.password,
                )
            _record_registration_audit(result, record_audit)
            return {
                "status": "success",
                **result,
                "user": session.to_public_dict(),
                "token": auth_service.create_session_token(session),
            }
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/platform/auth/register-platform-admin")
    def register_platform_admin(payload: PlatformAdminRegisterRequest) -> dict[str, object]:
        try:
            result = auth_service.register_platform_admin(
                account=payload.account,
                password=payload.password,
                name=payload.name,
            )
            session = auth_service.authenticate_account(
                account=payload.account,
                password=payload.password,
            )
            if record_audit:
                record_audit(
                    action="create_platform_admin",
                    resource_type="platform_user",
                    resource_id=str(result["platform_user"]["user_id"]),
                    metadata={"account": payload.account},
                )
            return {
                "status": "success",
                **result,
                "user": session.to_public_dict(),
                "token": auth_service.create_session_token(session),
            }
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/platform/auth/login")
    def login(payload: TenantLoginRequest) -> dict[str, object]:
        try:
            if payload.account:
                session = auth_service.authenticate_account(
                    account=payload.account,
                    password=payload.password,
                )
            else:
                session = auth_service.authenticate(
                    tenant_id=payload.tenant_id,
                    user_id=payload.user_id,
                    password=payload.password,
                )
        except Exception as exc:
            raise HTTPException(status_code=401, detail="invalid account or password") from exc
        return {
            "status": "success",
            "user": session.to_public_dict(),
            "token": auth_service.create_session_token(session),
        }

    @app.get("/api/platform/auth/me")
    def me(request: Request) -> dict[str, object]:
        auth_header = request.headers.get("authorization", "")
        token = auth_header.removeprefix("Bearer ").strip()
        session = auth_service.verify_session_token(token)
        if session is None:
            raise HTTPException(status_code=401, detail="unauthorized")
        return {"status": "success", "user": session.to_public_dict()}


def _record_registration_audit(result: dict[str, object], record_audit: Callable[..., None] | None) -> None:
    if record_audit is None:
        return

    tenant = result.get("tenant") if isinstance(result, dict) else None
    tenant_user = result.get("tenant_user") if isinstance(result, dict) else None
    default_agent = result.get("default_agent") if isinstance(result, dict) else None
    if not isinstance(tenant, dict):
        return

    tenant_id = str(tenant.get("tenant_id", "") or "")
    if not tenant_id:
        return

    record_audit(
        action="create_tenant",
        resource_type="tenant",
        resource_id=tenant_id,
        tenant_id=tenant_id,
        metadata={"source": "auth_register"},
    )
    if isinstance(tenant_user, dict):
        user_id = str(tenant_user.get("user_id", "") or "")
        if user_id:
            record_audit(
                action="create_tenant_user",
                resource_type="tenant_user",
                resource_id=f"{tenant_id}:{user_id}",
                tenant_id=tenant_id,
                metadata={"role": tenant_user.get("role", "")},
            )
    if isinstance(default_agent, dict):
        agent_id = str(default_agent.get("agent_id", "") or "")
        if agent_id:
            record_audit(
                action="create_agent",
                resource_type="agent",
                resource_id=agent_id,
                tenant_id=tenant_id,
                agent_id=agent_id,
                metadata={"source": "default_agent"},
            )

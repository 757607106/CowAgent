from __future__ import annotations

from fastapi import HTTPException, Request

from cow_platform.services.agent_service import DEFAULT_TENANT_ID
from cow_platform.services.auth_service import TenantAuthService, TenantAuthSession


READ_ROLES = {"owner", "admin", "member", "viewer"}
MANAGE_ROLES = {"owner", "admin"}


class PlatformAuthorizer:
    """Small auth/RBAC helper for the platform API."""

    def __init__(self, auth_service: TenantAuthService):
        self.auth_service = auth_service

    def require_session(self, request: Request, *, roles: set[str] | None = None) -> TenantAuthSession:
        auth_header = request.headers.get("authorization", "")
        token = auth_header.removeprefix("Bearer ").strip()
        session = self.auth_service.verify_session_token(token)
        if session is None:
            raise HTTPException(status_code=401, detail="unauthorized")
        if session.principal_type != "tenant":
            raise HTTPException(status_code=403, detail="tenant session required")

        allowed_roles = roles or READ_ROLES
        if session.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="forbidden")
        return session

    def require_platform_admin(self, request: Request) -> TenantAuthSession:
        auth_header = request.headers.get("authorization", "")
        token = auth_header.removeprefix("Bearer ").strip()
        session = self.auth_service.verify_session_token(token)
        if session is None:
            raise HTTPException(status_code=401, detail="unauthorized")
        if session.principal_type != "platform" or session.role != "platform_super_admin":
            raise HTTPException(status_code=403, detail="platform admin required")
        return session

    @staticmethod
    def scope_tenant_id(session: TenantAuthSession, tenant_id: str = "") -> str:
        requested = (tenant_id or "").strip()
        if not requested:
            return session.tenant_id
        if requested == DEFAULT_TENANT_ID and session.tenant_id != DEFAULT_TENANT_ID:
            return session.tenant_id
        if requested != session.tenant_id:
            raise HTTPException(status_code=403, detail="cannot access another tenant")
        return requested

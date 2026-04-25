from __future__ import annotations

from fastapi import HTTPException, Request

from cow_platform.runtime.tenant_scope import TenantScopeError, resolve_tenant_scope
from cow_platform.services.agent_service import DEFAULT_TENANT_ID
from cow_platform.services.auth_service import TenantAuthService, TenantAuthSession


READ_ROLES = {"owner", "admin", "member", "viewer"}
MANAGE_ROLES = {"owner", "admin"}


class PlatformAuthorizer:
    """Small auth/RBAC helper for the platform API."""

    def __init__(self, auth_service: TenantAuthService):
        self.auth_service = auth_service

    def _verify_bearer_session(self, request: Request) -> TenantAuthSession:
        auth_header = request.headers.get("authorization", "")
        token = auth_header.removeprefix("Bearer ").strip()
        session = self.auth_service.verify_session_token(token)
        if session is None:
            raise HTTPException(status_code=401, detail="unauthorized")
        return session

    def require_session(self, request: Request, *, roles: set[str] | None = None) -> TenantAuthSession:
        session = self._verify_bearer_session(request)
        if session.principal_type != "tenant":
            raise HTTPException(status_code=403, detail="tenant session required")

        allowed_roles = roles or READ_ROLES
        if session.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="forbidden")
        return session

    def require_platform_admin(self, request: Request) -> TenantAuthSession:
        session = self._verify_bearer_session(request)
        if session.principal_type != "platform" or session.role != "platform_super_admin":
            raise HTTPException(status_code=403, detail="platform admin required")
        return session

    @staticmethod
    def scope_tenant_id(session: TenantAuthSession, tenant_id: str = "") -> str:
        try:
            return resolve_tenant_scope(
                session_tenant_id=session.tenant_id,
                requested_tenant_id=tenant_id,
                default_tenant_id=DEFAULT_TENANT_ID,
            )
        except TenantScopeError as exc:
            raise HTTPException(status_code=403, detail="cannot access another tenant") from exc

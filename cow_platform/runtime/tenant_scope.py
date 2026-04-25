from __future__ import annotations


class TenantScopeError(PermissionError):
    """Raised when a request tries to access another tenant scope."""


def normalize_tenant_id(tenant_id: str = "", *, default: str = "default") -> str:
    return (tenant_id or default).strip() or default


def resolve_tenant_scope(
    *,
    session_tenant_id: str = "",
    requested_tenant_id: str = "",
    default_tenant_id: str = "default",
    preserve_blank_without_session: bool = False,
) -> str:
    """Resolve a requested tenant id under an optional authenticated tenant session.

    In tenant-auth mode, the historical Web API may still send ``default`` when
    it really means "current tenant". Treat that as an alias for the session
    tenant so old defaults do not become false cross-tenant denials.
    """

    current = (session_tenant_id or "").strip()
    requested = (requested_tenant_id or "").strip()
    default = normalize_tenant_id(default_tenant_id)

    if current:
        if not requested:
            return current
        if requested == default and current != default:
            return current
        if requested != current:
            raise TenantScopeError("cannot access another tenant")
        return requested

    if preserve_blank_without_session and not requested:
        return ""
    return normalize_tenant_id(requested or default, default=default)

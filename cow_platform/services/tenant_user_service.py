from __future__ import annotations

from typing import Any

from cow_platform.domain.models import TenantUserDefinition, TenantUserIdentityDefinition
from cow_platform.repositories.tenant_user_repository import FileTenantUserRepository
from cow_platform.services.tenant_service import TenantService


DEFAULT_TENANT_USER_ROLE = "member"
DEFAULT_TENANT_USER_STATUS = "active"
TENANT_USER_ROLES: tuple[str, ...] = ("owner", "admin", "member", "viewer")
TENANT_USER_STATUSES: tuple[str, ...] = ("active", "disabled", "invited")


class TenantUserService:
    """租户用户与角色管理服务。"""

    def __init__(
        self,
        repository: FileTenantUserRepository | None = None,
        tenant_service: TenantService | None = None,
    ):
        self.repository = repository or FileTenantUserRepository()
        self.tenant_service = tenant_service or TenantService()

    def list_users(
        self,
        *,
        tenant_id: str = "",
        role: str = "",
        status: str = "",
    ) -> list[TenantUserDefinition]:
        resolved_role = self._normalize_role(role) if role else ""
        resolved_status = self._normalize_status(status) if status else ""
        return self.repository.list_users(
            tenant_id=(tenant_id or "").strip(),
            role=resolved_role,
            status=resolved_status,
        )

    def resolve_user(self, *, tenant_id: str, user_id: str) -> TenantUserDefinition:
        definition = self.repository.get_user(tenant_id, user_id)
        if definition is None:
            raise KeyError(f"tenant user not found: {tenant_id}/{user_id}")
        return definition

    def create_user(
        self,
        *,
        tenant_id: str,
        user_id: str,
        name: str = "",
        role: str = DEFAULT_TENANT_USER_ROLE,
        status: str = DEFAULT_TENANT_USER_STATUS,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        resolved_tenant_id = (tenant_id or "").strip()
        resolved_user_id = (user_id or "").strip()
        resolved_name = (name or "").strip()
        resolved_role = self._normalize_role(role)
        resolved_status = self._normalize_status(status)

        self.tenant_service.resolve_tenant(resolved_tenant_id)
        definition = self.repository.create_user(
            tenant_id=resolved_tenant_id,
            user_id=resolved_user_id,
            name=resolved_name,
            role=resolved_role,
            status=resolved_status,
            metadata=metadata or {},
        )
        return self.serialize_user(definition)

    def update_user(
        self,
        *,
        tenant_id: str,
        user_id: str,
        name: str | None = None,
        role: str | None = None,
        status: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        existing = self.resolve_user(tenant_id=tenant_id, user_id=user_id)
        resolved_role = self._normalize_role(role) if role is not None else existing.role
        resolved_status = self._normalize_status(status) if status is not None else existing.status
        if existing.role == "owner" and existing.status == "active":
            if resolved_role != "owner" or resolved_status != "active":
                if not self._has_other_active_owner(existing.tenant_id, excluded_user_id=existing.user_id):
                    raise ValueError("tenant must keep at least one active owner")

        definition = self.repository.update_user(
            tenant_id=tenant_id,
            user_id=user_id,
            name=(name or "").strip() if name is not None else None,
            role=resolved_role if role is not None else None,
            status=resolved_status if status is not None else None,
            metadata=metadata,
        )
        return self.serialize_user(definition)

    def delete_user(self, *, tenant_id: str, user_id: str) -> dict[str, Any]:
        existing = self.resolve_user(tenant_id=tenant_id, user_id=user_id)
        if existing.role == "owner" and existing.status == "active":
            if not self._has_other_active_owner(existing.tenant_id, excluded_user_id=existing.user_id):
                raise ValueError("tenant must keep at least one active owner")
        definition = self.repository.delete_user(tenant_id=tenant_id, user_id=user_id)
        return self.serialize_user(definition)

    def list_identities(
        self,
        *,
        tenant_id: str = "",
        user_id: str = "",
        channel_type: str = "",
    ) -> list[TenantUserIdentityDefinition]:
        return self.repository.list_identities(
            tenant_id=(tenant_id or "").strip(),
            user_id=(user_id or "").strip(),
            channel_type=(channel_type or "").strip(),
        )

    def bind_identity(
        self,
        *,
        tenant_id: str,
        user_id: str,
        channel_type: str,
        external_user_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        resolved_tenant_id = (tenant_id or "").strip()
        resolved_user_id = (user_id or "").strip()
        resolved_channel_type = (channel_type or "").strip()
        resolved_external_user_id = (external_user_id or "").strip()
        if not resolved_channel_type:
            raise ValueError("channel_type must not be empty")
        if not resolved_external_user_id:
            raise ValueError("external_user_id must not be empty")

        user = self.resolve_user(tenant_id=resolved_tenant_id, user_id=resolved_user_id)
        if user.status != "active":
            raise ValueError("identity can only be bound to active tenant users")
        definition = self.repository.upsert_identity(
            tenant_id=resolved_tenant_id,
            user_id=resolved_user_id,
            channel_type=resolved_channel_type,
            external_user_id=resolved_external_user_id,
            metadata=metadata or {},
        )
        return self.serialize_identity(definition)

    def unbind_identity(
        self,
        *,
        tenant_id: str,
        channel_type: str,
        external_user_id: str,
    ) -> dict[str, Any]:
        definition = self.repository.delete_identity(
            tenant_id=(tenant_id or "").strip(),
            channel_type=(channel_type or "").strip(),
            external_user_id=(external_user_id or "").strip(),
        )
        return self.serialize_identity(definition)

    def resolve_user_by_identity(
        self,
        *,
        tenant_id: str,
        channel_type: str,
        external_user_id: str,
    ) -> TenantUserDefinition | None:
        return self.repository.find_user_by_identity(
            tenant_id=(tenant_id or "").strip(),
            channel_type=(channel_type or "").strip(),
            external_user_id=(external_user_id or "").strip(),
        )

    def serialize_user(self, definition: TenantUserDefinition) -> dict[str, Any]:
        return self.repository.export_user_record(definition)

    def serialize_identity(self, definition: TenantUserIdentityDefinition) -> dict[str, Any]:
        return self.repository.export_identity_record(definition)

    def list_user_records(
        self,
        *,
        tenant_id: str = "",
        role: str = "",
        status: str = "",
    ) -> list[dict[str, Any]]:
        return [
            self.serialize_user(item)
            for item in self.list_users(
                tenant_id=tenant_id,
                role=role,
                status=status,
            )
        ]

    def list_identity_records(
        self,
        *,
        tenant_id: str = "",
        user_id: str = "",
        channel_type: str = "",
    ) -> list[dict[str, Any]]:
        return [
            self.serialize_identity(item)
            for item in self.list_identities(
                tenant_id=tenant_id,
                user_id=user_id,
                channel_type=channel_type,
            )
        ]

    @staticmethod
    def list_roles() -> tuple[str, ...]:
        return TENANT_USER_ROLES

    @staticmethod
    def list_statuses() -> tuple[str, ...]:
        return TENANT_USER_STATUSES

    def _has_other_active_owner(self, tenant_id: str, *, excluded_user_id: str) -> bool:
        owners = self.repository.list_users(tenant_id=tenant_id, role="owner", status="active")
        return any(item.user_id != excluded_user_id for item in owners)

    @staticmethod
    def _normalize_role(role: str) -> str:
        resolved = (role or "").strip().lower()
        if not resolved:
            raise ValueError("role must not be empty")
        if resolved not in TENANT_USER_ROLES:
            raise ValueError(f"unsupported role: {resolved}")
        return resolved

    @staticmethod
    def _normalize_status(status: str) -> str:
        resolved = (status or "").strip().lower()
        if not resolved:
            raise ValueError("status must not be empty")
        if resolved not in TENANT_USER_STATUSES:
            raise ValueError(f"unsupported status: {resolved}")
        return resolved

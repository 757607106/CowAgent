from __future__ import annotations

from typing import Any

import pytest

from cow_platform.domain.models import TenantDefinition, TenantUserDefinition
from cow_platform.services.auth_service import TenantAuthService
from cow_platform.services.tenant_user_service import TenantUserService


class _TenantService:
    def __init__(self) -> None:
        self.tenants = {
            "acme": TenantDefinition(tenant_id="acme", name="Acme"),
        }

    def resolve_tenant(self, tenant_id: str) -> TenantDefinition:
        tenant = self.tenants.get(tenant_id)
        if tenant is None:
            raise KeyError(tenant_id)
        return tenant


class _TenantUserRepository:
    def __init__(self) -> None:
        self.users: dict[tuple[str, str], TenantUserDefinition] = {}

    def list_users(
        self,
        *,
        tenant_id: str = "",
        role: str = "",
        status: str = "",
    ) -> list[TenantUserDefinition]:
        users = list(self.users.values())
        if tenant_id:
            users = [user for user in users if user.tenant_id == tenant_id]
        if role:
            users = [user for user in users if user.role == role]
        if status:
            users = [user for user in users if user.status == status]
        return users

    def get_user(self, tenant_id: str, user_id: str) -> TenantUserDefinition | None:
        return self.users.get((tenant_id, user_id))

    def create_user(
        self,
        *,
        tenant_id: str,
        user_id: str,
        name: str = "",
        role: str,
        status: str = "active",
        metadata: dict[str, Any] | None = None,
    ) -> TenantUserDefinition:
        key = (tenant_id, user_id)
        if key in self.users:
            raise ValueError(f"tenant user already exists: {tenant_id}/{user_id}")
        user = TenantUserDefinition(
            tenant_id=tenant_id,
            user_id=user_id,
            name=name,
            role=role,
            status=status,
            metadata=dict(metadata or {}),
        )
        self.users[key] = user
        return user

    @staticmethod
    def export_user_record(definition: TenantUserDefinition) -> dict[str, Any]:
        return {
            "tenant_id": definition.tenant_id,
            "user_id": definition.user_id,
            "name": definition.name,
            "role": definition.role,
            "status": definition.status,
            "metadata": dict(definition.metadata),
            "created_at": None,
            "updated_at": None,
        }


class _PlatformUserService:
    @staticmethod
    def list_users(*, role: str = "", status: str = "") -> list[Any]:
        return []

    @staticmethod
    def has_platform_admin() -> bool:
        return False

    @staticmethod
    def resolve_user(user_id: str) -> Any:
        raise KeyError(user_id)


def test_tenant_user_service_create_user_writes_login_credentials() -> None:
    tenant_service = _TenantService()
    platform_user_service = _PlatformUserService()
    tenant_user_service = TenantUserService(
        repository=_TenantUserRepository(),
        tenant_service=tenant_service,
        platform_user_service=platform_user_service,
    )
    auth_service = TenantAuthService(
        tenant_service=tenant_service,
        tenant_user_service=tenant_user_service,
        platform_user_service=platform_user_service,
        session_expire_seconds=3600,
    )

    created = tenant_user_service.create_user(
        tenant_id="acme",
        user_id="bob",
        name="Bob",
        role="member",
        status="active",
        account="Member@Example.COM",
        password="password-123",
    )
    user = tenant_user_service.resolve_user(tenant_id="acme", user_id="bob")
    session = auth_service.authenticate_account(
        account="member@example.com",
        password="password-123",
    )

    assert created["metadata"] == {"auth_enabled": True}
    assert user.metadata["auth"]["account"] == "member@example.com"
    assert TenantAuthService.verify_password(
        "password-123",
        user.metadata["auth"]["password_hash"],
    )
    assert session.tenant_id == "acme"
    assert session.user_id == "bob"

    with pytest.raises(ValueError, match="account already registered"):
        tenant_user_service.create_user(
            tenant_id="acme",
            user_id="charlie",
            name="Charlie",
            account="member@example.com",
            password="password-456",
        )

    with pytest.raises(ValueError, match="password is required"):
        tenant_user_service.create_user(
            tenant_id="acme",
            user_id="dana",
            name="Dana",
            account="dana@example.com",
        )

    generated = tenant_user_service.create_user(
        tenant_id="acme",
        name="Eve",
        password="password-789",
    )
    generated_user = tenant_user_service.resolve_user(
        tenant_id="acme",
        user_id=generated["user_id"],
    )
    assert generated_user.metadata["auth"]["account"] == generated["user_id"]

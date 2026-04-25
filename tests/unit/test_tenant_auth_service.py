from __future__ import annotations

from typing import Any

import pytest

from cow_platform.domain.models import AgentDefinition, TenantDefinition, TenantUserDefinition
from cow_platform.services.auth_credentials import sanitize_user_record
from cow_platform.services.auth_service import TenantAuthService


class _TenantService:
    def __init__(self) -> None:
        self.tenants: dict[str, TenantDefinition] = {}

    def create_tenant(
        self,
        *,
        tenant_id: str = "",
        name: str,
        status: str = "active",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if tenant_id in self.tenants:
            raise ValueError(f"tenant already exists: {tenant_id}")
        self.tenants[tenant_id] = TenantDefinition(
            tenant_id=tenant_id,
            name=name,
            status=status,
            metadata=dict(metadata or {}),
        )
        return {
            "tenant_id": tenant_id,
            "name": name,
            "status": status,
            "metadata": dict(metadata or {}),
        }

    def resolve_tenant(self, tenant_id: str) -> TenantDefinition:
        tenant = self.tenants.get(tenant_id)
        if tenant is None:
            raise KeyError(tenant_id)
        return tenant


class _TenantUserService:
    def __init__(self) -> None:
        self.users: dict[tuple[str, str], TenantUserDefinition] = {}

    def create_user(
        self,
        *,
        tenant_id: str,
        user_id: str = "",
        name: str = "",
        role: str = "member",
        status: str = "active",
        metadata: dict[str, Any] | None = None,
        account: str = "",
        password: str = "",
    ) -> dict[str, Any]:
        del account, password
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
        return self.serialize_user(user)

    def update_user(
        self,
        *,
        tenant_id: str,
        user_id: str,
        metadata: dict[str, Any] | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        user = self.resolve_user(tenant_id=tenant_id, user_id=user_id)
        next_metadata = dict(metadata or {})
        existing_auth = dict(user.metadata).get("auth")
        if existing_auth:
            next_metadata["auth"] = existing_auth
        self.users[(tenant_id, user_id)] = TenantUserDefinition(
            tenant_id=user.tenant_id,
            user_id=user.user_id,
            name=user.name,
            role=user.role,
            status=user.status,
            metadata=next_metadata,
        )
        return self.serialize_user(self.users[(tenant_id, user_id)])

    def resolve_user(self, *, tenant_id: str, user_id: str) -> TenantUserDefinition:
        user = self.users.get((tenant_id, user_id))
        if user is None:
            raise KeyError(f"{tenant_id}/{user_id}")
        return user

    def list_users(self, *, tenant_id: str = "", role: str = "", status: str = "") -> list[TenantUserDefinition]:
        users = list(self.users.values())
        if tenant_id:
            users = [user for user in users if user.tenant_id == tenant_id]
        if role:
            users = [user for user in users if user.role == role]
        if status:
            users = [user for user in users if user.status == status]
        return users

    @staticmethod
    def serialize_user(definition: TenantUserDefinition) -> dict[str, Any]:
        return sanitize_user_record(
            {
                "tenant_id": definition.tenant_id,
                "user_id": definition.user_id,
                "name": definition.name,
                "role": definition.role,
                "status": definition.status,
                "metadata": dict(definition.metadata),
                "created_at": None,
                "updated_at": None,
            }
        )


class _AgentService:
    def __init__(self) -> None:
        self.agents: dict[tuple[str, str], AgentDefinition] = {}

    def ensure_default_agent(self, tenant_id: str) -> AgentDefinition:
        key = (tenant_id, "default")
        if key not in self.agents:
            self.agents[key] = AgentDefinition(
                tenant_id=tenant_id,
                agent_id="default",
                name="通用 Agent",
                metadata={"source": "legacy-default"},
            )
        return self.agents[key]

    @staticmethod
    def serialize_agent(definition: AgentDefinition) -> dict[str, Any]:
        return {
            "tenant_id": definition.tenant_id,
            "agent_id": definition.agent_id,
            "name": definition.name,
            "version": definition.version,
            "model": definition.model,
            "model_config_id": definition.model_config_id,
            "system_prompt": definition.system_prompt,
            "metadata": dict(definition.metadata),
            "tools": list(definition.tools),
            "skills": list(definition.skills),
            "knowledge_enabled": definition.knowledge_enabled,
            "mcp_servers": dict(definition.mcp_servers),
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


def _build_service() -> TenantAuthService:
    tenant_service = _TenantService()
    tenant_user_service = _TenantUserService()
    platform_user_service = _PlatformUserService()
    service = TenantAuthService(
        tenant_service=tenant_service,
        tenant_user_service=tenant_user_service,
        agent_service=_AgentService(),
        platform_user_service=platform_user_service,
        session_expire_seconds=3600,
    )
    service._get_signing_secret = lambda: b"unit-test-signing-secret"  # type: ignore[method-assign]
    return service


def test_tenant_auth_registers_owner_default_agent_and_token() -> None:
    service = _build_service()

    result = service.register_tenant(
        tenant_id="acme",
        tenant_name="Acme",
        user_id="alice",
        name="Alice",
        password="password-123",
    )
    session = service.authenticate(
        tenant_id="acme",
        user_id="alice",
        password="password-123",
    )
    token = service.create_session_token(session)
    verified = service.verify_session_token(token)
    user = service.tenant_user_service.resolve_user(tenant_id="acme", user_id="alice")
    user_record = service.tenant_user_service.serialize_user(user)

    assert result["tenant"]["tenant_id"] == "acme"
    assert result["tenant_user"]["role"] == "owner"
    assert result["default_agent"]["tenant_id"] == "acme"
    assert result["default_agent"]["agent_id"] == "default"
    assert service.has_credentials() is True
    assert verified is not None
    assert verified.tenant_id == "acme"
    assert verified.user_id == "alice"
    assert "auth" not in user_record["metadata"]
    assert user_record["metadata"]["auth_enabled"] is True

    with pytest.raises(PermissionError):
        service.authenticate(tenant_id="acme", user_id="alice", password="wrong-password")


def test_tenant_user_metadata_update_preserves_password_hash() -> None:
    service = _build_service()
    service.register_tenant(
        tenant_id="tenant-a",
        tenant_name="Tenant A",
        user_id="owner",
        password="password-123",
    )

    service.tenant_user_service.update_user(
        tenant_id="tenant-a",
        user_id="owner",
        metadata={"department": "ops", "auth": {}},
    )

    session = service.authenticate(
        tenant_id="tenant-a",
        user_id="owner",
        password="password-123",
    )
    user = service.tenant_user_service.resolve_user(tenant_id="tenant-a", user_id="owner")
    public_record = service.tenant_user_service.serialize_user(user)

    assert session.tenant_id == "tenant-a"
    assert public_record["metadata"] == {
        "department": "ops",
        "auth_enabled": True,
    }


def test_tenant_auth_registers_with_account_and_generated_internal_ids() -> None:
    service = _build_service()

    result = service.register_tenant(
        tenant_name="用户成功团队",
        account="Owner@Example.COM",
        name="Owner",
        password="password-123",
    )
    session = service.authenticate_account(
        account="owner@example.com",
        password="password-123",
    )

    assert result["tenant"]["tenant_id"].startswith("tenant-")
    assert result["tenant_user"]["user_id"].startswith("user-owner-example-com-")
    assert result["tenant_user"]["metadata"]["auth_enabled"] is True
    assert session.tenant_id == result["tenant"]["tenant_id"]
    assert session.user_id == result["tenant_user"]["user_id"]
    assert session.tenant_name == "用户成功团队"
    assert session.user_name == "Owner"
    assert session.account == "owner@example.com"
    assert session.to_public_dict()["tenant_name"] == "用户成功团队"
    assert session.to_public_dict()["user_name"] == "Owner"
    assert session.to_public_dict()["account"] == "owner@example.com"

    with pytest.raises(ValueError, match="account already registered"):
        service.register_tenant(
            tenant_name="另一个团队",
            account="owner@example.com",
            password="password-456",
        )

    with pytest.raises(PermissionError):
        service.authenticate_account(account="owner@example.com", password="wrong-password")

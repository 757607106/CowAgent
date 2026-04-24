import pytest

from config import conf
from cow_platform.services.tenant_service import TenantService
from cow_platform.services.tenant_user_service import TenantUserService


def test_tenant_user_service_supports_role_and_identity_management(tmp_path, monkeypatch) -> None:
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))
    monkeypatch.setitem(conf(), "model", "legacy-model")

    tenant_service = TenantService()
    tenant_user_service = TenantUserService(tenant_service=tenant_service)

    tenant_service.create_tenant(tenant_id="acme", name="Acme")

    owner = tenant_user_service.create_user(
        tenant_id="acme",
        user_id="alice",
        name="Alice",
        role="owner",
        status="active",
    )
    member = tenant_user_service.create_user(
        tenant_id="acme",
        user_id="bob",
        name="Bob",
        role="member",
        status="active",
    )

    assert owner["role"] == "owner"
    assert member["role"] == "member"

    updated_member = tenant_user_service.update_user(
        tenant_id="acme",
        user_id="bob",
        role="admin",
        status="active",
    )
    assert updated_member["role"] == "admin"

    identity = tenant_user_service.bind_identity(
        tenant_id="acme",
        user_id="bob",
        channel_type="feishu",
        external_user_id="ou_123",
        metadata={"source": "manual"},
    )
    assert identity["channel_type"] == "feishu"

    resolved_user = tenant_user_service.resolve_user_by_identity(
        tenant_id="acme",
        channel_type="feishu",
        external_user_id="ou_123",
    )
    assert resolved_user is not None
    assert resolved_user.user_id == "bob"

    deleted_member = tenant_user_service.delete_user(tenant_id="acme", user_id="bob")
    assert deleted_member["user_id"] == "bob"
    assert tenant_user_service.resolve_user_by_identity(
        tenant_id="acme",
        channel_type="feishu",
        external_user_id="ou_123",
    ) is None

    with pytest.raises(ValueError, match="at least one active owner"):
        tenant_user_service.delete_user(tenant_id="acme", user_id="alice")

    tenant_user_service.create_user(
        tenant_id="acme",
        user_id="charlie",
        name="Charlie",
        role="owner",
        status="active",
    )
    demoted_owner = tenant_user_service.update_user(
        tenant_id="acme",
        user_id="alice",
        role="admin",
    )
    assert demoted_owner["role"] == "admin"

    generated_tenant = tenant_service.create_tenant(name="用户成功团队")
    generated_user = tenant_user_service.create_user(
        tenant_id=generated_tenant["tenant_id"],
        name="Dana",
        role="member",
        status="active",
    )
    assert generated_tenant["tenant_id"].startswith("tenant-")
    assert generated_user["user_id"].startswith("user-dana-")


def test_tenant_user_service_rejects_invalid_role_and_status(tmp_path, monkeypatch) -> None:
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))
    monkeypatch.setitem(conf(), "model", "legacy-model")

    tenant_service = TenantService()
    tenant_user_service = TenantUserService(tenant_service=tenant_service)
    tenant_service.create_tenant(tenant_id="acme", name="Acme")

    with pytest.raises(ValueError, match="unsupported role"):
        tenant_user_service.create_user(
            tenant_id="acme",
            user_id="eve",
            role="super_admin",
        )

    with pytest.raises(ValueError, match="unsupported status"):
        tenant_user_service.create_user(
            tenant_id="acme",
            user_id="eve",
            role="viewer",
            status="blocked",
        )

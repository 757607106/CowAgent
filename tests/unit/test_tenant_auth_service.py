from pathlib import Path

import pytest

from config import conf
from cow_platform.services.auth_service import TenantAuthService


def test_tenant_auth_registers_owner_default_agent_and_token(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))
    monkeypatch.setitem(conf(), "model", "legacy-model")

    service = TenantAuthService(session_expire_seconds=3600)

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


def test_tenant_user_metadata_update_preserves_password_hash(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))

    service = TenantAuthService(session_expire_seconds=3600)
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


def test_tenant_auth_registers_with_account_and_generated_internal_ids(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))
    monkeypatch.setitem(conf(), "model", "legacy-model")

    service = TenantAuthService(session_expire_seconds=3600)

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

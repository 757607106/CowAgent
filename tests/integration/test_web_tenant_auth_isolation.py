from pathlib import Path

import pytest

from config import conf
from channel.web import web_channel
from cow_platform.services.auth_service import TenantAuthService


@pytest.mark.integration
def test_web_tenant_auth_scopes_default_agent_and_rejects_cross_tenant(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))
    monkeypatch.setitem(conf(), "model", "legacy-model")
    monkeypatch.setitem(conf(), "web_tenant_auth", True)

    service = TenantAuthService(session_expire_seconds=3600)
    service.register_tenant(
        tenant_id="tenant-a",
        tenant_name="Tenant A",
        user_id="alice",
        password="password-123",
    )
    service.register_tenant(
        tenant_id="tenant-b",
        tenant_name="Tenant B",
        user_id="bob",
        password="password-456",
    )

    session_a = service.authenticate(
        tenant_id="tenant-a",
        user_id="alice",
        password="password-123",
    )
    token_a = service.create_session_token(session_a)
    monkeypatch.setattr(
        web_channel.web,
        "cookies",
        lambda: {web_channel._TENANT_AUTH_COOKIE: token_a},
    )

    target = web_channel._resolve_runtime_target()
    workspace_a = Path(web_channel._get_workspace_root())

    assert target == {
        "tenant_id": "tenant-a",
        "agent_id": "default",
        "binding_id": "",
    }
    assert workspace_a == tmp_path / "legacy" / "workspaces" / "tenant-a" / "default"
    own_file = workspace_a / "tmp" / "own.txt"
    own_file.parent.mkdir(parents=True, exist_ok=True)
    own_file.write_text("own", encoding="utf-8")

    other_file = tmp_path / "legacy" / "workspaces" / "tenant-b" / "default" / "tmp" / "other.txt"
    other_file.parent.mkdir(parents=True, exist_ok=True)
    other_file.write_text("other", encoding="utf-8")
    assert web_channel._is_file_access_allowed(str(own_file)) is True
    assert web_channel._is_file_access_allowed(str(other_file)) is False

    monkeypatch.setattr(
        web_channel,
        "_raise_forbidden",
        lambda message="Forbidden": (_ for _ in ()).throw(PermissionError(message)),
    )
    with pytest.raises(PermissionError):
        web_channel._resolve_runtime_target(agent_id="default", tenant_id="tenant-b")

    session_b = service.authenticate(
        tenant_id="tenant-b",
        user_id="bob",
        password="password-456",
    )
    token_b = service.create_session_token(session_b)
    monkeypatch.setattr(
        web_channel.web,
        "cookies",
        lambda: {web_channel._TENANT_AUTH_COOKIE: token_b},
    )
    workspace_b = Path(web_channel._get_workspace_root())

    assert workspace_b == tmp_path / "legacy" / "workspaces" / "tenant-b" / "default"
    assert workspace_b != workspace_a

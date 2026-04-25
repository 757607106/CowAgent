from types import SimpleNamespace

import pytest

from cow_platform.runtime.tenant_scope import TenantScopeError, normalize_tenant_id, resolve_tenant_scope


def test_normalize_tenant_id_uses_default_for_blank_values() -> None:
    assert normalize_tenant_id("") == "default"
    assert normalize_tenant_id("  ") == "default"
    assert normalize_tenant_id(" acme ") == "acme"


def test_resolve_tenant_scope_without_session_preserves_optional_blank_filters() -> None:
    assert resolve_tenant_scope(requested_tenant_id="") == "default"
    assert resolve_tenant_scope(requested_tenant_id="", preserve_blank_without_session=True) == ""
    assert resolve_tenant_scope(requested_tenant_id="acme", preserve_blank_without_session=True) == "acme"


def test_resolve_tenant_scope_maps_legacy_default_to_current_session_tenant() -> None:
    assert resolve_tenant_scope(session_tenant_id="tenant-a", requested_tenant_id="") == "tenant-a"
    assert resolve_tenant_scope(session_tenant_id="tenant-a", requested_tenant_id="default") == "tenant-a"
    assert resolve_tenant_scope(session_tenant_id="tenant-a", requested_tenant_id="tenant-a") == "tenant-a"


def test_resolve_tenant_scope_rejects_cross_tenant_requests() -> None:
    with pytest.raises(TenantScopeError):
        resolve_tenant_scope(session_tenant_id="tenant-a", requested_tenant_id="tenant-b")


def test_web_scope_helpers_share_default_alias_behavior(monkeypatch) -> None:
    from channel.web import web_channel

    session = SimpleNamespace(principal_type="tenant", tenant_id="tenant-a")
    monkeypatch.setattr(web_channel, "_get_authenticated_tenant_session", lambda: session)
    monkeypatch.setattr(
        web_channel,
        "_raise_forbidden",
        lambda message="Forbidden": (_ for _ in ()).throw(PermissionError(message)),
    )

    assert web_channel._scope_tenant_id("default") == "tenant-a"
    assert web_channel._scope_optional_tenant_id("default") == "tenant-a"

    with pytest.raises(PermissionError):
        web_channel._scope_tenant_id("tenant-b")

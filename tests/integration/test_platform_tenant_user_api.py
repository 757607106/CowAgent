import pytest
from fastapi.testclient import TestClient

from config import conf

from cow_platform.api.app import create_app
from cow_platform.api.settings import PlatformSettings
from tests.integration.platform_auth_helpers import register_owner


@pytest.mark.integration
def test_platform_tenant_user_api_supports_crud_and_identity_binding(tmp_path, monkeypatch) -> None:
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))
    monkeypatch.setitem(conf(), "model", "legacy-model")

    app = create_app(PlatformSettings(host="127.0.0.1", port=9917, mode="test"))
    client = TestClient(app)
    headers, tenant_id, register_resp = register_owner(
        client,
        tenant_id="acme",
        tenant_name="Acme",
        user_id="alice",
        user_name="Alice",
    )

    meta_resp = client.get("/api/platform/tenant-user-meta", headers=headers)
    create_owner_resp = client.get(f"/api/platform/tenant-users/{tenant_id}/alice", headers=headers)
    create_admin_resp = client.post(
        "/api/platform/tenant-users",
        headers=headers,
        json={
            "tenant_id": tenant_id,
            "user_id": "bob",
            "account": "bob@example.com",
            "name": "Bob",
            "role": "member",
            "status": "active",
            "password": "password-456",
        },
    )
    bob_login_resp = client.post(
        "/api/platform/auth/login",
        json={"account": "bob@example.com", "password": "password-456"},
    )
    update_admin_resp = client.put(
        f"/api/platform/tenant-users/{tenant_id}/bob",
        headers=headers,
        json={"role": "admin", "status": "active"},
    )
    list_users_resp = client.get("/api/platform/tenant-users", headers=headers, params={"tenant_id": tenant_id})
    get_user_resp = client.get(f"/api/platform/tenant-users/{tenant_id}/bob", headers=headers)
    upsert_identity_resp = client.post(
        "/api/platform/tenant-user-identities",
        headers=headers,
        json={
            "tenant_id": tenant_id,
            "user_id": "bob",
            "channel_type": "feishu",
            "external_user_id": "ou_001",
            "metadata": {"source": "integration-test"},
        },
    )
    list_identities_resp = client.get(
        "/api/platform/tenant-user-identities",
        headers=headers,
        params={"tenant_id": tenant_id, "user_id": "bob"},
    )
    delete_identity_resp = client.delete(f"/api/platform/tenant-user-identities/{tenant_id}/feishu/ou_001", headers=headers)
    delete_user_resp = client.delete(f"/api/platform/tenant-users/{tenant_id}/bob", headers=headers)
    list_users_after_delete = client.get("/api/platform/tenant-users", headers=headers, params={"tenant_id": tenant_id})

    assert register_resp["tenant"]["tenant_id"] == tenant_id

    assert meta_resp.status_code == 200
    assert "owner" in meta_resp.json()["roles"]
    assert "active" in meta_resp.json()["statuses"]

    assert create_owner_resp.status_code == 200
    assert create_owner_resp.json()["tenant_user"]["role"] == "owner"

    assert create_admin_resp.status_code == 200
    assert create_admin_resp.json()["tenant_user"]["user_id"] == "bob"
    assert create_admin_resp.json()["tenant_user"]["metadata"]["auth_enabled"] is True

    assert bob_login_resp.status_code == 200
    assert bob_login_resp.json()["user"]["user_id"] == "bob"

    assert update_admin_resp.status_code == 200
    assert update_admin_resp.json()["tenant_user"]["role"] == "admin"

    assert list_users_resp.status_code == 200
    assert len(list_users_resp.json()["tenant_users"]) == 2

    assert get_user_resp.status_code == 200
    assert get_user_resp.json()["tenant_user"]["user_id"] == "bob"

    assert upsert_identity_resp.status_code == 200
    assert upsert_identity_resp.json()["identity"]["external_user_id"] == "ou_001"

    assert list_identities_resp.status_code == 200
    assert len(list_identities_resp.json()["identities"]) == 1
    assert list_identities_resp.json()["identities"][0]["channel_type"] == "feishu"

    assert delete_identity_resp.status_code == 200
    assert delete_identity_resp.json()["identity"]["external_user_id"] == "ou_001"

    assert delete_user_resp.status_code == 200
    assert delete_user_resp.json()["tenant_user"]["user_id"] == "bob"

    assert list_users_after_delete.status_code == 200
    assert len(list_users_after_delete.json()["tenant_users"]) == 1
    assert list_users_after_delete.json()["tenant_users"][0]["user_id"] == "alice"


@pytest.mark.integration
def test_platform_tenant_user_api_generates_internal_ids(tmp_path, monkeypatch) -> None:
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))
    monkeypatch.setitem(conf(), "model", "legacy-model")

    app = create_app(PlatformSettings(host="127.0.0.1", port=9917, mode="test"))
    client = TestClient(app)

    headers, tenant_id, register_resp = register_owner(
        client,
        tenant_id="",
        tenant_name="用户成功团队",
        user_id="owner",
        user_name="Owner",
        account="success-owner",
    )
    create_user_resp = client.post(
        "/api/platform/tenant-users",
        headers=headers,
        json={
            "tenant_id": tenant_id,
            "name": "Dana",
            "role": "member",
            "status": "active",
        },
    )

    assert tenant_id.startswith("tenant-")
    assert register_resp["tenant"]["metadata"]["source"] == "tenant-register"

    assert create_user_resp.status_code == 200
    assert create_user_resp.json()["tenant_user"]["tenant_id"] == tenant_id
    assert create_user_resp.json()["tenant_user"]["user_id"].startswith("user-dana-")

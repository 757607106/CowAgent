import pytest
from fastapi.testclient import TestClient

from config import conf

from cow_platform.api.app import create_app
from cow_platform.api.settings import PlatformSettings


@pytest.mark.integration
def test_platform_tenant_user_api_supports_crud_and_identity_binding(tmp_path, monkeypatch) -> None:
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))
    monkeypatch.setitem(conf(), "model", "legacy-model")

    app = create_app(PlatformSettings(host="127.0.0.1", port=9917, mode="test"))
    client = TestClient(app)

    create_tenant_resp = client.post("/api/platform/tenants", json={"tenant_id": "acme", "name": "Acme"})
    meta_resp = client.get("/api/platform/tenant-user-meta")
    create_owner_resp = client.post(
        "/api/platform/tenant-users",
        json={
            "tenant_id": "acme",
            "user_id": "alice",
            "name": "Alice",
            "role": "owner",
            "status": "active",
        },
    )
    create_admin_resp = client.post(
        "/api/platform/tenant-users",
        json={
            "tenant_id": "acme",
            "user_id": "bob",
            "name": "Bob",
            "role": "member",
            "status": "active",
        },
    )
    update_admin_resp = client.put(
        "/api/platform/tenant-users/acme/bob",
        json={"role": "admin", "status": "active"},
    )
    list_users_resp = client.get("/api/platform/tenant-users", params={"tenant_id": "acme"})
    get_user_resp = client.get("/api/platform/tenant-users/acme/bob")
    upsert_identity_resp = client.post(
        "/api/platform/tenant-user-identities",
        json={
            "tenant_id": "acme",
            "user_id": "bob",
            "channel_type": "feishu",
            "external_user_id": "ou_001",
            "metadata": {"source": "integration-test"},
        },
    )
    list_identities_resp = client.get(
        "/api/platform/tenant-user-identities",
        params={"tenant_id": "acme", "user_id": "bob"},
    )
    delete_identity_resp = client.delete("/api/platform/tenant-user-identities/acme/feishu/ou_001")
    delete_user_resp = client.delete("/api/platform/tenant-users/acme/bob")
    list_users_after_delete = client.get("/api/platform/tenant-users", params={"tenant_id": "acme"})

    assert create_tenant_resp.status_code == 200
    assert create_tenant_resp.json()["tenant"]["tenant_id"] == "acme"

    assert meta_resp.status_code == 200
    assert "owner" in meta_resp.json()["roles"]
    assert "active" in meta_resp.json()["statuses"]

    assert create_owner_resp.status_code == 200
    assert create_owner_resp.json()["tenant_user"]["role"] == "owner"

    assert create_admin_resp.status_code == 200
    assert create_admin_resp.json()["tenant_user"]["user_id"] == "bob"

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

    create_tenant_resp = client.post(
        "/api/platform/tenants",
        json={"name": "用户成功团队", "status": "active", "metadata": {"source": "test"}},
    )
    tenant_id = create_tenant_resp.json()["tenant"]["tenant_id"]
    create_user_resp = client.post(
        "/api/platform/tenant-users",
        json={
            "tenant_id": tenant_id,
            "name": "Dana",
            "role": "member",
            "status": "active",
        },
    )

    assert create_tenant_resp.status_code == 200
    assert tenant_id.startswith("tenant-")
    assert create_tenant_resp.json()["tenant"]["metadata"]["source"] == "test"

    assert create_user_resp.status_code == 200
    assert create_user_resp.json()["tenant_user"]["tenant_id"] == tenant_id
    assert create_user_resp.json()["tenant_user"]["user_id"].startswith("user-dana-")

import pytest
from fastapi.testclient import TestClient

from config import conf
from cow_platform.api.app import create_app
from cow_platform.api.settings import PlatformSettings


@pytest.mark.integration
def test_platform_auth_api_registers_and_logs_in_tenant(tmp_path, monkeypatch) -> None:
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))
    monkeypatch.setitem(conf(), "model", "legacy-model")

    app = create_app(PlatformSettings(host="127.0.0.1", port=9938, mode="test"))
    client = TestClient(app)

    register_resp = client.post(
        "/api/platform/auth/register",
        json={
            "tenant_id": "acme",
            "tenant_name": "Acme",
            "user_id": "alice",
            "user_name": "Alice",
            "password": "password-123",
        },
    )
    login_resp = client.post(
        "/api/platform/auth/login",
        json={
            "tenant_id": "acme",
            "user_id": "alice",
            "password": "password-123",
        },
    )
    token = login_resp.json()["token"]
    me_resp = client.get(
        "/api/platform/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    bad_login_resp = client.post(
        "/api/platform/auth/login",
        json={
            "tenant_id": "acme",
            "user_id": "alice",
            "password": "wrong-password",
        },
    )

    assert register_resp.status_code == 200
    assert register_resp.json()["tenant"]["tenant_id"] == "acme"
    assert register_resp.json()["tenant_user"]["role"] == "owner"
    assert register_resp.json()["default_agent"]["agent_id"] == "default"
    assert "auth" not in register_resp.json()["tenant_user"]["metadata"]

    assert login_resp.status_code == 200
    assert login_resp.json()["user"]["tenant_id"] == "acme"
    assert token

    assert me_resp.status_code == 200
    assert me_resp.json()["user"]["user_id"] == "alice"

    assert bad_login_resp.status_code == 401


@pytest.mark.integration
def test_platform_auth_api_registers_with_account_and_generated_ids(tmp_path, monkeypatch) -> None:
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))
    monkeypatch.setitem(conf(), "model", "legacy-model")

    app = create_app(PlatformSettings(host="127.0.0.1", port=9938, mode="test"))
    client = TestClient(app)

    register_resp = client.post(
        "/api/platform/auth/register",
        json={
            "tenant_name": "用户成功团队",
            "account": "owner@example.com",
            "user_name": "Owner",
            "password": "password-123",
        },
    )
    login_resp = client.post(
        "/api/platform/auth/login",
        json={
            "account": "owner@example.com",
            "password": "password-123",
        },
    )
    duplicate_resp = client.post(
        "/api/platform/auth/register",
        json={
            "tenant_name": "重复团队",
            "account": "OWNER@example.com",
            "password": "password-456",
        },
    )
    bad_login_resp = client.post(
        "/api/platform/auth/login",
        json={
            "account": "owner@example.com",
            "password": "wrong-password",
        },
    )

    assert register_resp.status_code == 200
    assert register_resp.json()["tenant"]["tenant_id"].startswith("tenant-")
    assert register_resp.json()["tenant_user"]["user_id"].startswith("user-owner-example-com-")
    assert register_resp.json()["user"]["tenant_name"] == "用户成功团队"
    assert register_resp.json()["user"]["user_name"] == "Owner"
    assert register_resp.json()["user"]["account"] == "owner@example.com"
    assert "auth" not in register_resp.json()["tenant_user"]["metadata"]

    assert login_resp.status_code == 200
    assert login_resp.json()["user"]["tenant_id"] == register_resp.json()["tenant"]["tenant_id"]
    assert login_resp.json()["user"]["user_id"] == register_resp.json()["tenant_user"]["user_id"]
    assert login_resp.json()["token"]

    assert duplicate_resp.status_code == 400
    assert "account already registered" in duplicate_resp.json()["detail"]

    assert bad_login_resp.status_code == 401

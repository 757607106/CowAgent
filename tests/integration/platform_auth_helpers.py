from __future__ import annotations

from fastapi.testclient import TestClient


DEFAULT_TEST_PASSWORD = "admin123456"


def register_owner(
    client: TestClient,
    *,
    tenant_id: str = "acme",
    tenant_name: str | None = None,
    user_id: str = "owner",
    user_name: str = "Owner",
    account: str | None = None,
    password: str = DEFAULT_TEST_PASSWORD,
) -> tuple[dict[str, str], str, dict[str, object]]:
    """Register a tenant owner and return auth headers plus the tenant id."""

    payload = {
        "tenant_id": tenant_id,
        "tenant_name": tenant_name or tenant_id,
        "user_id": user_id,
        "user_name": user_name,
        "account": account or f"{tenant_id}-owner",
        "password": password,
    }
    response = client.post("/api/platform/auth/register", json=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    headers = {"Authorization": f"Bearer {body['token']}"}
    return headers, body["tenant"]["tenant_id"], body

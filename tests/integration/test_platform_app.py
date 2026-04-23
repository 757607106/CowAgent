import pytest
from fastapi.testclient import TestClient

from cow_platform.api.app import create_app
from cow_platform.api.settings import PlatformSettings


@pytest.mark.integration
def test_platform_app_health_and_ready_endpoints() -> None:
    app = create_app(PlatformSettings(host="127.0.0.1", port=9910, mode="test"))
    client = TestClient(app)

    health_response = client.get("/health")
    ready_response = client.get("/ready")

    assert health_response.status_code == 200
    assert health_response.json() == {
        "status": "ok",
        "service": "cow-platform",
        "mode": "test",
    }
    assert ready_response.status_code == 200
    assert ready_response.json() == {
        "status": "ready",
        "service": "cow-platform",
        "dependencies": {},
    }

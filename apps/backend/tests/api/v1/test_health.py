import pytest
from fastapi.testclient import TestClient

from app.api.v1.health import health_check
from app.main import create_app


@pytest.mark.asyncio
async def test_health_check_returns_ok() -> None:
    assert await health_check() == {"status": "ok"}


def test_root_health_endpoint() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_headers_on_health_endpoint() -> None:
    client = TestClient(create_app())
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"

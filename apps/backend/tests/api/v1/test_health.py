import pytest

from app.api.v1.health import health_check


@pytest.mark.asyncio
async def test_health_check_returns_ok() -> None:
    assert await health_check() == {"status": "ok"}

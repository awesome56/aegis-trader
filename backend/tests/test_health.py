"""Health endpoint tests."""

from __future__ import annotations

from httpx import AsyncClient


async def test_health_reports_components(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"healthy", "degraded", "unhealthy"}
    components = {c["name"]: c["status"] for c in body["components"]}
    assert components["database"] == "healthy"
    # No Redis is available in the isolated test environment.
    assert components["redis"] == "unhealthy"


async def test_liveness(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


async def test_readiness(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


async def test_root_banner(client: AsyncClient) -> None:
    response = await client.get("/")
    assert response.status_code == 200
    assert response.json()["service"]

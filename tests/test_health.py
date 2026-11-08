import pytest
from httpx import ASGITransport, AsyncClient

from src.health import create_health_app


@pytest.mark.asyncio
async def test_health_check_endpoint():
    app = create_health_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "verity-backend"
        assert "timestamp" in data

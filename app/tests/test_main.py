import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

"""
Test Block for Health requests
"""


@pytest.mark.asyncio
async def test_health_returns_200():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_returns_correct_body():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.json() == {"status": "ok"}


"""
#TODO esperando as classes AppError
@pytest.mark.asyncio
async def test_app_error_handler(some_route_that_raises_app_error):
    # Once you have routes that raise AppError subclasses, test them here
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/some-route-that-raises")
    assert response.status_code == 404  # or whatever your AppError maps to
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_read_root():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/")
    assert r.status_code == 200
    assert r.json() == {"message": "Hello from FastAPI"}

@pytest.mark.asyncio
async def test_create_and_get_item():
    item = {"id": 1, "name": "Test", "description": "desc"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/items", json=item)
        assert r.status_code == 201
        assert r.json() == item
        r2 = await ac.get("/items/1")
        assert r2.status_code == 200
        assert r2.json() == item

@pytest.mark.asyncio
async def test_create_duplicate_item():
    item = {"id": 2, "name": "Dup", "description": "dup"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/items", json=item)
        assert r.status_code == 201
        r_dup = await ac.post("/items", json=item)
        assert r_dup.status_code == 400

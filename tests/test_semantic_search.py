import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import AsyncSessionLocal
from app.models.product import ProductModel
from sqlalchemy import delete
import asyncio

from app.models.user import UserModel
from app.core.event_bus import event_bus
from worker import main as worker_main

@pytest.mark.asyncio
async def test_semantic_search_flow():
    async with AsyncSessionLocal() as session:
        await session.execute(delete(ProductModel))
        await session.execute(delete(UserModel))
        await session.commit()

    await event_bus.connect()

    worker_task = asyncio.create_task(worker_main())
    await asyncio.sleep(0.5)

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            register_resp = await ac.post("/api/v1/auth/register", json={
                "email": "test@example.com",
                "password": "testpassword123",
                "full_name": "Test User"
            })
            assert register_resp.status_code == 201

            login_resp = await ac.post("/api/v1/auth/login", json={
                "email": "test@example.com",
                "password": "testpassword123"
            })
            assert login_resp.status_code == 200
            token = login_resp.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            resp = await ac.post("/api/v1/products/create-product", json={
                "name": "Extreme Winter Sleeping Bag",
                "description": "A heavy-duty sleeping bag designed for sub-zero temperatures and mountain camping.",
                "price": 99.99,
                "stock": 10
            }, headers=headers)
            assert resp.status_code == 200
            product_bag = resp.json()

            resp = await ac.post("/api/v1/products/create-product", json={
                "name": "Professional Chef Knife",
                "description": "High carbon stainless steel kitchen knife for slicing and dicing vegetables and meats.",
                "price": 49.99,
                "stock": 15
            }, headers=headers)
            assert resp.status_code == 200
            product_knife = resp.json()

            await asyncio.sleep(3)

            resp = await ac.get("/api/v1/products/search", params={"query": "camping gear for cold weather", "limit": 2})
            assert resp.status_code == 200
            results = resp.json()
            assert len(results) > 0
            assert results[0]["id"] == product_bag["id"]

            resp = await ac.get("/api/v1/products/search", params={"query": "sharp kitchen utensil for chef", "limit": 2})
            assert resp.status_code == 200
            results = resp.json()
            assert len(results) > 0
            assert results[0]["id"] == product_knife["id"]

            chat_resp = await ac.post("/api/v1/products/chat", json={
                "query": "Do you have any warm gear for snow camping?",
                "limit": 2
            })
            assert chat_resp.status_code == 200
            chat_data = chat_resp.json()
            assert "Extreme Winter Sleeping Bag" in chat_data["answer"]
            assert len(chat_data["retrieved_products"]) > 0
            assert chat_data["retrieved_products"][0]["id"] == product_bag["id"]

            chat_resp = await ac.post("/api/v1/products/chat", json={
                "query": "Looking for a sharp chef knife",
                "limit": 2
            })
            assert chat_resp.status_code == 200
            chat_data = chat_resp.json()
            assert "Professional Chef Knife" in chat_data["answer"]
            assert len(chat_data["retrieved_products"]) > 0
            assert chat_data["retrieved_products"][0]["id"] == product_knife["id"]
    finally:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
        await event_bus.close()

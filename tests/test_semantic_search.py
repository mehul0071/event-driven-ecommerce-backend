import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import AsyncSessionLocal
from app.models.product import ProductModel
from sqlalchemy import delete
import asyncio

@pytest.mark.asyncio
async def test_semantic_search_flow():
    # Clean products table first
    async with AsyncSessionLocal() as session:
        await session.execute(delete(ProductModel))
        await session.commit()

    # Seed products via API
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create a product about sleeping bags
        resp = await ac.post("/api/v1/products/create-product", json={
            "name": "Extreme Winter Sleeping Bag",
            "description": "A heavy-duty sleeping bag designed for sub-zero temperatures and mountain camping.",
            "price": 99.99,
            "stock": 10
        })
        assert resp.status_code == 200
        product_bag = resp.json()

        # Create a product about kitchen knives
        resp = await ac.post("/api/v1/products/create-product", json={
            "name": "Professional Chef Knife",
            "description": "High carbon stainless steel kitchen knife for slicing and dicing vegetables and meats.",
            "price": 49.99,
            "stock": 15
        })
        assert resp.status_code == 200
        product_knife = resp.json()

        # Give the background task a moment to generate the embeddings
        await asyncio.sleep(2)

        # Search for something camping related
        resp = await ac.get("/api/v1/products/search", params={"query": "camping gear for cold weather", "limit": 2})
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) > 0
        # The sleeping bag should be the top hit, not the chef knife!
        assert results[0]["id"] == product_bag["id"]

        # Search for something cooking related
        resp = await ac.get("/api/v1/products/search", params={"query": "sharp kitchen utensil for chef", "limit": 2})
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) > 0
        # The chef knife should be the top hit!
        assert results[0]["id"] == product_knife["id"]

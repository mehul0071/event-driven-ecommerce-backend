from fastapi import APIRouter
from app.api.v1.routes import health, products, orders

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])

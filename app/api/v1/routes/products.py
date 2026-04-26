from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.product import ProductCreate, ProductList, ProductResponse
from app.services.product_service import create_product, list_of_products

router = APIRouter()


@router.post("/create-product", response_model=ProductResponse)
async def create_product_endpoint(
    product: ProductCreate,
    db: AsyncSession = Depends(get_db)
):
    return await create_product(db, product)


@router.get("/list-products", response_model=List[ProductList])
async def list_products_endpoint(
    db: AsyncSession = Depends(get_db)
):
    return await list_of_products(db)
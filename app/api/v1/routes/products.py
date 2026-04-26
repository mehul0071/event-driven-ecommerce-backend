from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.product import ProductCreate, ProductList, ProductResponse
from app.services.product_service import create_product, list_of_products, list_product_endpoint_by_id

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


@router.get("/list-product/{product_id}", response_model=ProductList)
async def list_product_endpoint(
    product_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    return await list_product_endpoint_by_id(db, product_id)
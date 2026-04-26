from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.product import ProductModel
from app.schemas.product import ProductCreate, ProductList


async def create_product(
    db: AsyncSession,
    product: ProductCreate
):
    product = ProductModel(
        name=product.name,
        description=product.description,
        price=product.price,
        stock=product.stock,
)   
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


async def list_of_products(db: AsyncSession) -> list[ProductModel]:
    stmt = select(ProductModel).order_by(ProductModel.name)
    result = await db.execute(stmt)
    return result.scalars().all()


async def list_product_endpoint_by_id(
    db: AsyncSession,
    product_id: UUID
) -> ProductList:

    stmt = select(ProductModel).where(
        ProductModel.id == product_id
    )

    result = await db.execute(stmt)
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    return product
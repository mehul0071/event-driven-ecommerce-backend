from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.product import ProductModel
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate


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
) -> ProductResponse:

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


async def update_product_by_id(
    db: AsyncSession,
    product_id: UUID,
    product_update: ProductUpdate
) -> ProductUpdate:
    
    stmt = select(ProductModel).where(ProductModel.id == product_id)
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )
    
    update_data = product_update.model_dump(exclude_unset=True)

    filtered_data = {
        key:value
        for key, value in update_data.items()
        if value is not None
    }

    for key, value in filtered_data.items():
        setattr(product, key, value)

    await db.commit()
    await db.refresh(product)

    return product


async def delete_product_by_id(
    db: AsyncSession,
    product_id: UUID
):
    stmt = select(ProductModel).where(ProductModel.id == product_id)
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    await db.delete(product)
    await db.commit()
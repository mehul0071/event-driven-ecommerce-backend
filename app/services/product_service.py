from uuid import UUID
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
from uuid import UUID
from fastapi import HTTPException, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.product import ProductModel
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.core.database import AsyncSessionLocal
from app.services.embedding_service import embedding_service


from app.core.event_bus import event_bus


async def update_product_embedding_bg(product_id: UUID, text_to_embed: str):
    async with AsyncSessionLocal() as db:
        embedding = await embedding_service.generate_embedding(text_to_embed)
        stmt = select(ProductModel).where(ProductModel.id == product_id)
        result = await db.execute(stmt)
        product = result.scalar_one_or_none()
        if product:
            product.embedding = embedding
            await db.commit()
            print(f"[AI Ingestion] Generated and saved embedding for product {product.id}")


async def create_product(
    db: AsyncSession,
    product: ProductCreate,
    background_tasks: BackgroundTasks
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
    
    text_to_embed = f"{product.name} {product.description or ''}"
    published = await event_bus.publish(
        channel="product_events",
        event_type="product_created",
        data={"product_id": str(product.id), "text_to_embed": text_to_embed}
    )
    if not published:
        background_tasks.add_task(update_product_embedding_bg, product.id, text_to_embed)
    
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
    product_update: ProductUpdate,
    background_tasks: BackgroundTasks
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

    text_to_embed = f"{product.name} {product.description or ''}"
    published = await event_bus.publish(
        channel="product_events",
        event_type="product_updated",
        data={"product_id": str(product.id), "text_to_embed": text_to_embed}
    )
    if not published:
        background_tasks.add_task(update_product_embedding_bg, product.id, text_to_embed)

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


async def semantic_search_products(
    db: AsyncSession,
    query_text: str,
    limit: int = 5
) -> list[ProductModel]:
    query_vector = await embedding_service.generate_embedding(query_text)
    stmt = (
        select(ProductModel)
        .where(ProductModel.embedding.isnot(None))
        .order_by(ProductModel.embedding.cosine_distance(query_vector))
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()
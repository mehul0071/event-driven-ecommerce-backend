from typing import List, Optional
from uuid import UUID
from sqlalchemy import delete, select, update
from app.models.product import ProductModel
from domain.products.entities import Product
from domain.products.repository import ProductRepository
from sqlalchemy.ext.asyncio import AsyncSession


class SQLProductRepository(ProductRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id: UUID) -> Optional[Product]:
        stmt = select(ProductModel).where(ProductModel.id == id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none
        if model:
            return Product(
                id = model.id,
                name = model.name,
                description=model.description,
                price = model.price,
                stock = model.stock
            )
        return None
        
    async def get_all(self) -> List[Product]:
        stmt = select(ProductModel)
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [Product(
            id=m.id,
            name=m.name,
            description=m.description,
            price=m.price,
            stock=m.stock
        ) for m in models]
    
    async def add_product(self, product:Product) -> Product:
        model = ProductModel(
             name = product.name,
             description = product.description,
             price = product.price,
             stock = product.stock
        )
        self.session.add(model)
        await self.session.flush()
        product.id = model.id
        return product

    async def update_product(self, product:Product) -> Product:
        stmt = update(ProductModel).where(ProductModel.id == product.id).values(
            name=product.name,
            description=product.description,
            price=product.price,
            stock=product.stock
        ).returning(ProductModel)
        result = await self.session.execute(stmt)
        updated_model = result.scalar_one()
        return Product(
            id=updated_model.id,
            name=updated_model.name,
            description=updated_model.description,
            price=updated_model.price,
            stock=updated_model.stock
        )
    
    async def delete(self, id: UUID) -> None:
        stmt = delete(ProductModel).where(ProductModel.id == id)
        await self.session.execute(stmt)
from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from src.domain.products.entities import Product

class ProductRepository(ABC):
    @abstractmethod
    async def get_by_id(self, id: UUID) -> Optional[Product]:
        pass

    @abstractmethod
    async def get_all(self) -> List[Product]:
        pass

    @abstractmethod
    async def add(self, product: Product) -> Product:
        pass

    @abstractmethod
    async def update(self, product: Product) -> Product:
        pass

    @abstractmethod
    async def delete(self, id: UUID) -> None:
        pass
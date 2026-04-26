from typing import Optional
from uuid import UUID
from pydantic import BaseModel

class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    stock: int = 0


class ProductResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    price: float
    stock: int

    class Config:
        from_attributes = True


class ProductList(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    price: float
    stock: int

    class Config:
        from_attributes = True
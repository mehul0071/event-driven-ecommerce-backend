from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel


class OrderItem(BaseModel):
    product_id: UUID
    quantity: int


class OrderCreate(BaseModel):
    items: List[OrderItem]


class OrderDetail(BaseModel):
    order_id: UUID
    product_id: UUID
    name: str
    price: float
    quantity: int
    total: float
from typing import List
from uuid import UUID
from pydantic import BaseModel


class OrderItem(BaseModel):
    product_id: int
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
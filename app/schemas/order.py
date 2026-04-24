from typing import List
from uuid import UUID
from pydantic import BaseModel

class OrderItem(BaseModel):
    product_id: UUID
    quantity: int

class OrderCreate(BaseModel):
    items: List[OrderItem]

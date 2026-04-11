from dataclasses import dataclass
from typing import Optional
from uuid import UUID, uuid4


@dataclass
class Product:
    id: Optional[UUID] = None
    name: str
    description: str = ""
    price: float = 0.0
    stock: int = 0

    def __post_init__(self):
        if self.id == None:
            self.id = uuid4()

    def validate_stock(self, quantity: int) -> bool:
        if self.stock < quantity:
            raise ValueError("Insufficient stock")
        return True
    
    def reduce_stock(self, quantity: int) -> None:
        if self.validate_stock(quantity):
            self.stock -= quantity

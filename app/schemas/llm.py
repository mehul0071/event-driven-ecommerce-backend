from pydantic import BaseModel

class ProductAttributes(BaseModel):
    name: str
    category: str
    color: Optional[str] = None
    size: Optional[str] = None
    price: float
    stock: int
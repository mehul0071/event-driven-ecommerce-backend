from pydantic import BaseModel
from typing import List, Optional
from app.schemas.product import ProductResponse

class ChatRequest(BaseModel):
    query: str
    limit: Optional[int] = 5

class ChatResponse(BaseModel):
    answer: str
    retrieved_products: List[ProductResponse]

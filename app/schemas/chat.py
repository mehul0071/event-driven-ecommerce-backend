from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from app.schemas.product import ProductResponse

class ChatRequest(BaseModel):
    query: str
    limit: Optional[int] = 5

class ChatBotResponse(BaseModel):
    response: str = Field(description="Helpful customer support answer based ONLY on the retrieved products context.")
    recommended_product_ids: List[UUID] = Field(description="List of product IDs recommended to the user from the retrieved context.")
    follow_up_questions: List[str] = Field(description="2-3 suggested follow-up questions the user might ask next.")

class ChatResponse(BaseModel):
    answer: str
    recommended_product_ids: List[UUID]
    follow_up_questions: List[str]
    retrieved_products: List[ProductResponse]

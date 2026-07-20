from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class UserInteractionCreate(BaseModel):
    product_id: UUID
    interaction_type: str

class UserInteractionResponse(BaseModel):
    id: UUID
    user_id: UUID
    product_id: UUID
    interaction_type: str
    created_at: datetime

    class Config:
        from_attributes = True

from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime
from typing import List, Optional


class ReviewCreate(BaseModel):
    product_id: UUID
    rating: int
    comment: Optional[str] = None


class ReviewResponse(BaseModel):
    id: UUID
    product_id: UUID
    user_id: UUID
    rating: int
    comment: Optional[str] = None
    sentiment: Optional[str] = None
    summary_tags: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ReviewQAResponse(BaseModel):
    comment: str
    rating: int
    sentiment: Optional[str] = None
    relevance_score: float


class ReviewSummaryResponse(BaseModel):
    product_id: UUID
    pros: List[str]
    cons: List[str]
    verdict: str


class ReviewAnalysis(BaseModel):
    sentiment: str = Field(description="Must be 'positive', 'neutral', or 'negative'")
    summary_tags: List[str] = Field(description="List of 1-3 short aspect tags, e.g., 'durable', 'stiff zippers'")


class ReviewsConsensus(BaseModel):
    pros: List[str] = Field(description="Top 2-3 positive aspects as concise bullet points")
    cons: List[str] = Field(description="Top 2-3 negative/critique aspects as concise bullet points")
    verdict: str = Field(description="A single sentence summary summarizing if the product is recommended.")
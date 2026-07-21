from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.v1.routes.auth import get_current_user
from app.schemas.review import ReviewCreate, ReviewQAResponse, ReviewSummaryResponse
from app.services.review_service import submit_review, get_product_reviews_qa, get_product_reviews_summary
from app.core.database import get_db

router = APIRouter()


@router.post("/place-review")
async def place_review(
    review: ReviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return await submit_review(db, current_user.id, review)


@router.get("/product/{product_id}/qa", response_model=List[ReviewQAResponse])
async def reviews_qa(
    product_id: UUID,
    query: str = Query(..., description="Semantic question to query reviews"),
    limit: int = Query(3, ge=1, le=10),
    db: AsyncSession = Depends(get_db)
):
    return await get_product_reviews_qa(db, product_id, query, limit)


@router.get("/product/{product_id}/ai-summary", response_model=ReviewSummaryResponse)
async def reviews_summary(
    product_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    return await get_product_reviews_summary(db, product_id)

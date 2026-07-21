from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from sqlalchemy import select
from uuid import UUID
from typing import List
from app.models.review import ReviewModel
from app.models.order import OrderModel, OrderDetailModel
from app.models.product import ProductModel
from app.schemas.review import ReviewCreate
from app.core.event_bus import event_bus
from app.services.embedding_service import embedding_service
from app.services.llm_service import llm_service


async def submit_review(db: AsyncSession, user_id: UUID, review_data: ReviewCreate) -> dict:
    stmt = select(ProductModel).where(ProductModel.id == review_data.product_id)
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    stmt = select(OrderModel).join(
        OrderDetailModel,
        OrderModel.id == OrderDetailModel.order_id
    ).where(
        OrderModel.user_id == user_id,
        OrderDetailModel.product_id == review_data.product_id
    )
    result = await db.execute(stmt)
    order_exists = result.first() is not None
    if not order_exists:
        raise HTTPException(
            status_code=403,
            detail="You can only review products you have purchased."
        )

    stmt = select(ReviewModel).where(
        ReviewModel.user_id == user_id,
        ReviewModel.product_id == review_data.product_id
    )
    result = await db.execute(stmt)
    existing_review = result.scalar_one_or_none()
    if existing_review:
        raise HTTPException(
            status_code=400,
            detail="You have already reviewed this product."
        )

    new_review = ReviewModel(
        product_id=review_data.product_id,
        user_id=user_id,
        rating=review_data.rating,
        comment=review_data.comment,
        sentiment="pending"
    )
    db.add(new_review)
    await db.commit()
    await db.refresh(new_review)

    event_payload = {
        "review_id": str(new_review.id),
        "product_id": str(new_review.product_id),
        "user_id": str(new_review.user_id),
        "comment": new_review.comment or "",
        "rating": new_review.rating
    }
    
    await event_bus.publish(
        channel="review_events",
        event_type="review_created",
        data=event_payload
    )

    return {
        "review_id": new_review.id,
        "status": "pending_analysis"
    }


async def get_product_reviews_qa(db: AsyncSession, product_id: UUID, query: str, limit: int = 3) -> List[dict]:
    stmt = select(ProductModel).where(ProductModel.id == product_id)
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    query_emb = await embedding_service.generate_embedding(query)

    stmt = select(
        ReviewModel,
        ReviewModel.embedding.cosine_distance(query_emb).label("distance")
    ).where(
        ReviewModel.product_id == product_id,
        ReviewModel.embedding.isnot(None)
    ).order_by("distance").limit(limit)

    result = await db.execute(stmt)
    rows = result.all()

    response = []
    for r, dist in rows:
        relevance_score = 1.0 - float(dist)
        response.append({
            "comment": r.comment or "",
            "rating": r.rating,
            "sentiment": r.sentiment,
            "relevance_score": round(relevance_score, 4)
        })

    return response


async def get_product_reviews_summary(db: AsyncSession, product_id: UUID) -> dict:
    stmt = select(ProductModel).where(ProductModel.id == product_id)
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    stmt = select(ReviewModel).where(ReviewModel.product_id == product_id)
    result = await db.execute(stmt)
    reviews = result.scalars().all()

    reviews_list = [
        {"comment": r.comment, "rating": r.rating, "sentiment": r.sentiment}
        for r in reviews
    ]

    summary = await llm_service.generate_reviews_summary(product.name, reviews_list)
    
    return {
        "product_id": product_id,
        "pros": summary.get("pros", []),
        "cons": summary.get("cons", []),
        "verdict": summary.get("verdict", "")
    }

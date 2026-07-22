from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from datetime import datetime, timezone
import math
import logging
from app.models.product import ProductModel
from app.models.interaction import UserInteractionModel
from app.schemas.interaction import UserInteractionCreate

logger = logging.getLogger(__name__)

async def log_user_interaction(
    db: AsyncSession,
    user_id: UUID,
    interaction: UserInteractionCreate
) -> UserInteractionModel:
    db_interaction = UserInteractionModel(
        user_id=user_id,
        product_id=interaction.product_id,
        interaction_type=interaction.interaction_type
    )
    db.add(db_interaction)
    await db.commit()
    await db.refresh(db_interaction)
    return db_interaction


async def compute_user_taste_vector(
    db: AsyncSession,
    user_id: UUID,
    limit: int = 10
) -> list[float] | None:
    stmt = (
        select(ProductModel.embedding, UserInteractionModel.interaction_type, UserInteractionModel.created_at)
        .join(UserInteractionModel, UserInteractionModel.product_id == ProductModel.id)
        .where(UserInteractionModel.user_id == user_id)
        .where(ProductModel.embedding.isnot(None))
        .order_by(UserInteractionModel.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    records = result.all()

    if not records:
        return None

    vector_dim = len(records[0].embedding)
    weighted_sum = [0.0] * vector_dim
    total_weight = 0.0

    interaction_weights = {
        "view": 1.0,
        "cart": 3.0,
        "purchase": 5.0,
        "positive_review": 7.0
    }
    
    decay_lambda = 0.05
    now = datetime.now(timezone.utc)

    for record in records:
        emb, i_type, created_at = record.embedding, record.interaction_type, record.created_at
        
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
            
        age_days = max(0.0, (now - created_at).total_seconds() / 86400.0)
        time_decay = math.exp(-decay_lambda * age_days)
        
        base_weight = interaction_weights.get(i_type, 1.0)
        weight = base_weight * time_decay
        
        for i in range(vector_dim):
            weighted_sum[i] += emb[i] * weight
        total_weight += weight

    if total_weight == 0.0:
        return None

    return [val / total_weight for val in weighted_sum]


async def get_hybrid_recommendations(
    db: AsyncSession,
    user_id: UUID,
    limit: int = 5
) -> list[ProductModel]:
    taste_vector = await compute_user_taste_vector(db, user_id)
    
    if not taste_vector:
        stmt = (
            select(ProductModel)
            .where(ProductModel.stock > 0)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all()
        
    interacted_stmt = (
        select(UserInteractionModel.product_id)
        .where(UserInteractionModel.user_id == user_id)
    )
    
    recommend_stmt = (
        select(ProductModel)
        .where(ProductModel.embedding.isnot(None))
        .where(ProductModel.stock > 0)
        .where(ProductModel.id.notin_(interacted_stmt))
        .order_by(ProductModel.embedding.cosine_distance(taste_vector))
        .limit(limit)
    )
    result = await db.execute(recommend_stmt)
    return result.scalars().all()

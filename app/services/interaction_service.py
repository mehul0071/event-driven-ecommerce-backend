from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.models.product import ProductModel
from app.models.interaction import UserInteractionModel
from app.schemas.interaction import UserInteractionCreate

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
        select(ProductModel.embedding)
        .join(UserInteractionModel, UserInteractionModel.product_id == ProductModel.id)
        .where(UserInteractionModel.user_id == user_id)
        .where(ProductModel.embedding.isnot(None))
        .order_by(UserInteractionModel.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    embeddings = result.scalars().all()

    if not embeddings:
        return None

    num_embeddings = len(embeddings)
    vector_dim = len(embeddings[0])
    
    average_vector = [0.0] * vector_dim
    for emb in embeddings:
        for i in range(vector_dim):
            average_vector[i] += emb[i]

    for i in range(vector_dim):
        average_vector[i] /= num_embeddings

    return average_vector


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

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.order import OrderCreate
from app.services.order_service import create_order
from app.core.database import get_db

router = APIRouter()

@router.post("/place-order")
async def place_order(
    order: OrderCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    return await create_order(db, order, background_tasks)

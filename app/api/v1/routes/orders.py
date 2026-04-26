from typing import List
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.order import OrderCreate
from app.services.order_service import create_order
from sqlalchemy.orm import Session
from app.schemas.order import OrderCreate, OrderDetail
from app.services.order_service import create_order, list_of_order_details
from app.core.database import get_db

router = APIRouter()


@router.post("/place-order")
async def place_order(
    order: OrderCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    return await create_order(db, order, background_tasks)


@router.get("/list-orders", response_model=List[OrderDetail])
async def order_details(
    db: Session = Depends(get_db)
):
    return await list_of_order_details(db)
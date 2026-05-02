from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.order import OrderCreate, OrderDetail
from app.services.order_service import create_order, list_of_order_details, order_detail_by_id
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
    db: AsyncSession = Depends(get_db)
):
    return await list_of_order_details(db)


@router.get("/list-order/{order_id}", response_model=List[OrderDetail])
async def order_detail(
    order_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    return await order_detail_by_id(db, order_id)


@router.delete("/delete-order/{order_id}", response_model=204)
async def delete_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    return await delete_order_by_id(db, order_id)
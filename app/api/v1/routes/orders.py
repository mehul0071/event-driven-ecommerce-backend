from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from app.schemas.order import OrderCreate
from app.services.order_service import create_order
from app.core.database import get_db

router = APIRouter()

@router.post("/")
def place_order(
    order: OrderCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    return create_order(db, order, background_tasks)

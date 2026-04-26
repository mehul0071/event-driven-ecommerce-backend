from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
from datetime import datetime
from typing import List
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.order import OrderModel, OrderDetailModel
from app.models.product import ProductModel
from app.schemas.order import OrderCreate, OrderDetail
from app.events.order_events import OrderCreatedEvent


async def handle_inventory(event: OrderCreatedEvent):
    await asyncio.sleep(2)
    print(f"[Inventory] Reserving stock for order {event.order_id}")


async def handle_payment(event: OrderCreatedEvent):
    await asyncio.sleep(3)
    print(f"[Payment] Processing payment for order {event.order_id}")


async def handle_notification(event: OrderCreatedEvent):
    await asyncio.sleep(1)
    print(f"[Notification] Sending confirmation for order {event.order_id}")


async def create_order(db, order: OrderCreate, background_tasks):
    new_order = OrderModel(status="created")
    db.add(new_order)
    await db.flush()

    total = 0

    for item in order.items:
        stmt = select(ProductModel).where(ProductModel.id == item.product_id)
        result = await db.execute(stmt)
        product = result.scalar_one_or_none()
        
        if not product:
            raise HTTPException(
                status_code=404,
                detail="Product not found"
            )

        subtotal = item.quantity * product.price
        total += subtotal

        db.add(OrderDetailModel(
            order_id=new_order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=product.price,
            subtotal=subtotal
        ))

    new_order.total_amount = total

    await db.commit()
    await db.refresh(new_order)

    return {
        "order_id": new_order.id,
        "status": new_order.status,
        "total_amount": float(new_order.total_amount)
    }


async def list_of_order_details(db: AsyncSession) -> List[OrderDetail]:

    stmt = select(OrderDetailModel, ProductModel).join(
        ProductModel,
        OrderDetailModel.product_id == ProductModel.id
    )

    result = await db.execute(stmt)
    rows = result.all()

    response = []

    for detail, product in rows:
        response.append(
            OrderDetail(
                order_id=detail.order_id,
                product_id=detail.product_id,
                name=product.name,
                price=float(detail.unit_price),
                quantity=detail.quantity,
                total=float(detail.unit_price * detail.quantity)
            )
        )

    return response

        
async def order_detail_by_id(
    db: AsyncSession,
    order_id: UUID
) -> OrderDetail:

    stmt = select(OrderDetailModel, ProductModel).join(
        ProductModel,
        OrderDetailModel.product_id == ProductModel.id
    ).where(
        OrderDetailModel.order_id == order_id
    )
    result = await db.execute(stmt)
    order = result.all()

    if not order:
        raise HTTPException(
            status_code=404,
            detail = "Order not found"
        )

    response = []

    for orders, products in order:
        response.append(
            OrderDetail(
                order_id=orders.order_id,
                product_id=orders.product_id,
                name=products.name,
                price=float(orders.unit_price),
                quantity=orders.quantity,
                total=float(orders.unit_price * orders.quantity)
            )
        )

    return response

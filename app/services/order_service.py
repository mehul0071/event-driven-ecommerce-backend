from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
from datetime import datetime
from typing import List
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select
from app.models.order import OrderModel, OrderDetailModel
from app.models.product import ProductModel
from app.schemas.order import OrderCreate, OrderDetail
from app.events.order_events import OrderCreatedEvent
from app.core.event_bus import event_bus
from app.core.database import AsyncSessionLocal


async def handle_inventory(event: OrderCreatedEvent):
    await asyncio.sleep(2)
    print(f"[Inventory] Reserving stock for order {event.order_id}")


async def handle_payment(event: OrderCreatedEvent):
    await asyncio.sleep(3)
    print(f"[Payment] Processing payment for order {event.order_id}")


async def handle_notification(event: OrderCreatedEvent):
    await asyncio.sleep(1)
    print(f"[Notification] Sending confirmation for order {event.order_id}")


async def update_order_status(order_id: UUID, status: str):
    async with AsyncSessionLocal() as db:
        stmt = select(OrderModel).where(OrderModel.id == order_id)
        result = await db.execute(stmt)
        order = result.scalar_one_or_none()
        if order:
            order.status = status
            await db.commit()
            print(f"[Order Service] Order {order_id} status updated to: {status}")


async def process_order_fallback(event: OrderCreatedEvent):
    try:
        await update_order_status(event.order_id, "processing")
        await asyncio.gather(
            handle_inventory(event),
            handle_payment(event),
            handle_notification(event)
        )
        await update_order_status(event.order_id, "completed")
    except Exception as e:
        print(f"[Fallback] Error processing order {event.order_id}: {e}")
        await update_order_status(event.order_id, "failed")


async def create_order(db, user_id: UUID, order: OrderCreate, background_tasks):
    new_order = OrderModel(user_id=user_id, status="created")
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
            unit_price=product.price
        ))

    new_order.total_amount = total

    await db.commit()
    await db.refresh(new_order)

    event_data = {
        "order_id": str(new_order.id),
        "occurred_at": datetime.utcnow().isoformat()
    }
    
    published = await event_bus.publish(
        channel="order_events",
        event_type="order_created",
        data=event_data
    )
    if not published:
        event = OrderCreatedEvent(order_id=new_order.id, occurred_at=datetime.utcnow())
        background_tasks.add_task(process_order_fallback, event)

    return {
        "order_id": new_order.id,
        "status": new_order.status,
        "total_amount": float(new_order.total_amount)
    }


async def list_of_order_details(
    db: AsyncSession,
    user_id: UUID,
    is_superuser: bool = False
) -> List[OrderDetail]:

    stmt = select(OrderDetailModel, ProductModel).join(
        ProductModel,
        OrderDetailModel.product_id == ProductModel.id
    ).join(
        OrderModel,
        OrderDetailModel.order_id == OrderModel.id
    )

    if not is_superuser:
        stmt = stmt.where(OrderModel.user_id == user_id)

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
    order_id: UUID,
    user_id: UUID,
    is_superuser: bool = False
) -> List[OrderDetail]:

    stmt = select(OrderModel).where(OrderModel.id == order_id)
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    if not is_superuser and order.user_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this order"
        )

    stmt = select(OrderDetailModel, ProductModel).join(
        ProductModel,
        OrderDetailModel.product_id == ProductModel.id
    ).where(
        OrderDetailModel.order_id == order_id
    )
    result = await db.execute(stmt)
    order_details = result.all()

    response = []

    for detail, product in order_details:
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


async def delete_order_by_id(
    db: AsyncSession,
    order_id: UUID,
    user_id: UUID,
    is_superuser: bool = False
):
    
    stmt = select(OrderModel).where(OrderModel.id == order_id)
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )
    
    if not is_superuser and order.user_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to delete this order"
        )
    
    await db.delete(order)
    await db.commit()
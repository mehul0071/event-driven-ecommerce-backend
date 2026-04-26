import asyncio
from datetime import datetime
from typing import List
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
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
            raise Exception("Product not found")

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


async def list_of_order_details(db) -> List[OrderDetail]:

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

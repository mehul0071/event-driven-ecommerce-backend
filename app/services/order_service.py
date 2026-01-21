from sqlalchemy.orm import Session
from datetime import datetime
from time import sleep
from app.models.order import Order
from app.schemas.order import OrderCreate
from app.events.order_events import OrderCreatedEvent

def handle_inventory(event: OrderCreatedEvent):
    sleep(2)
    print(f"[Inventory] Reserving stock for order {event.order_id}")

def handle_payment(event: OrderCreatedEvent):
    sleep(3)
    print(f"[Payment] Processing payment for order {event.order_id}")

def handle_notification(event: OrderCreatedEvent):
    sleep(1)
    print(f"[Notification] Sending confirmation for order {event.order_id}")

def create_order(db: Session, order: OrderCreate, background_tasks):
    new_order = Order(status="created")
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    event = OrderCreatedEvent(
        order_id=new_order.id,
        occurred_at=datetime.utcnow()
    )

    background_tasks.add_task(handle_inventory, event)
    background_tasks.add_task(handle_payment, event)
    background_tasks.add_task(handle_notification, event)

    return {
        "order_id": new_order.id,
        "status": new_order.status,
        "items": order.items
    }

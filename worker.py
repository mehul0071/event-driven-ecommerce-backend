import asyncio
import json
import os
from uuid import UUID
from datetime import datetime
import sys
from dotenv import load_dotenv
import redis.asyncio as aioredis
from sqlalchemy import select
from app.core.database import AsyncSessionLocal, engine
from app.models.product import ProductModel
from app.models.user import UserModel
from app.services.embedding_service import embedding_service
from app.events.order_events import OrderCreatedEvent
from app.services.order_service import handle_inventory, handle_payment, handle_notification


load_dotenv()

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def handle_product_created_or_updated(data):
    product_id = data.get("product_id")
    text_to_embed = data.get("text_to_embed")
    if not product_id or not text_to_embed:
        return

    print(f"[Worker] Processing embedding generation for product: {product_id}")
    try:
        embedding = await embedding_service.generate_embedding(text_to_embed)
        async with AsyncSessionLocal() as db:
            stmt = select(ProductModel).where(ProductModel.id == product_id)
            result = await db.execute(stmt)
            product = result.scalar_one_or_none()
            if product:
                product.embedding = embedding
                await db.commit()
                print(f"[Worker] Successfully saved embedding for product {product_id} to database.")
            else:
                print(f"[Worker] Warning: Product {product_id} not found in database.")
    except Exception as e:
        print(f"[Worker] Error updating product embedding: {e}")

async def handle_order_created(data):
    order_id_str = data.get("order_id")
    occurred_at_str = data.get("occurred_at")
    if not order_id_str:
        return

    print(f"[Worker] Processing order created event for order: {order_id_str}")
    try:
        order_id = UUID(order_id_str)
        occurred_at = datetime.fromisoformat(occurred_at_str) if occurred_at_str else datetime.utcnow()
        event = OrderCreatedEvent(order_id=order_id, occurred_at=occurred_at)
        
        await asyncio.gather(
            handle_inventory(event),
            handle_payment(event),
            handle_notification(event)
        )
        print(f"[Worker] Successfully processed order {order_id_str} tasks.")
    except Exception as e:
        print(f"[Worker] Error handling order created event: {e}")

async def main():
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    print(f"[Worker] Connecting to Redis at {redis_url}...")
    try:
        redis = aioredis.from_url(redis_url, decode_responses=True)
        pubsub = redis.pubsub()
        await pubsub.subscribe("product_events", "order_events")
        print("[Worker] Subscribed to 'product_events' and 'order_events' channels. Listening for events...")
    except Exception as e:
        print(f"[Worker] Failed to initialize Redis subscriber: {e}")
        return

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    payload = json.loads(message["data"])
                    event_type = payload.get("event_type")
                    data = payload.get("data", {})
                    
                    print(f"[Worker] Received event: {event_type}")
                    if event_type in ("product_created", "product_updated"):
                        asyncio.create_task(handle_product_created_or_updated(data))
                    elif event_type == "order_created":
                        asyncio.create_task(handle_order_created(data))
                except Exception as ex:
                    print(f"[Worker] Error processing message: {ex}")
    except asyncio.CancelledError:
        print("[Worker] Shutting down...")
    finally:
        await pubsub.unsubscribe("product_events", "order_events")
        await redis.close()
        await engine.dispose()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[Worker] Interrupted by user. Exiting.")

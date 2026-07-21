import asyncio
import json
import os
from uuid import UUID
from datetime import datetime, timezone
import sys
from dotenv import load_dotenv
import redis.asyncio as aioredis
from sqlalchemy import select
from app.core.database import AsyncSessionLocal, engine
from app.models.product import ProductModel
from app.models.user import UserModel
from app.models.review import ReviewModel
from app.models.interaction import UserInteractionModel
from app.services.embedding_service import embedding_service
from app.services.llm_service import llm_service
from app.events.order_events import OrderCreatedEvent
from app.services.order_service import handle_inventory, handle_payment, handle_notification, update_order_status


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
                raise ValueError(f"Product {product_id} not found in database.")
    except Exception as e:
        print(f"[Worker] Error updating product embedding: {e}")
        raise e

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
        
        await update_order_status(order_id, "processing")
        
        await asyncio.gather(
            handle_inventory(event),
            handle_payment(event),
            handle_notification(event)
        )
        
        await update_order_status(order_id, "completed")
        print(f"[Worker] Successfully processed order {order_id_str} tasks.")
    except Exception as e:
        print(f"[Worker] Error handling order created event: {e}")
        if order_id_str:
            try:
                await update_order_status(UUID(order_id_str), "failed")
            except Exception as update_ex:
                print(f"[Worker] Failed to update order status to failed: {update_ex}")
        raise e


async def handle_review_created(data):
    review_id_str = data.get("review_id")
    product_id_str = data.get("product_id")
    user_id_str = data.get("user_id")
    comment = data.get("comment", "")
    rating = data.get("rating", 3)

    if not review_id_str or not product_id_str or not user_id_str:
        return

    print(f"[Worker] Processing review event for review: {review_id_str}")
    try:
        review_id = UUID(review_id_str)
        product_id = UUID(product_id_str)
        user_id = UUID(user_id_str)

        embedding = None
        if comment:
            embedding = await embedding_service.generate_embedding(comment)

        sentiment = "neutral"
        summary_tags = ""
        if comment:
            analysis = await llm_service.analyze_review_sentiment_and_tags(comment)
            sentiment = analysis.get("sentiment", "neutral")
            tags = analysis.get("summary_tags", [])
            summary_tags = ", ".join(tags)

        async with AsyncSessionLocal() as db:
            stmt = select(ReviewModel).where(ReviewModel.id == review_id)
            result = await db.execute(stmt)
            review = result.scalar_one_or_none()
            
            if review:
                review.embedding = embedding
                review.sentiment = sentiment
                review.summary_tags = summary_tags
                
                if rating >= 4:
                    interaction = UserInteractionModel(
                        user_id=user_id,
                        product_id=product_id,
                        interaction_type="review_positive"
                    )
                    db.add(interaction)
                
                await db.commit()
                print(f"[Worker] Successfully updated review analysis for {review_id_str}")
            else:
                print(f"[Worker] Review {review_id_str} not found in database.")
    except Exception as e:
        print(f"[Worker] Error handling review created event: {e}")
        raise e

async def route_to_dlq(redis, event_type, payload, error_msg):
    try:
        dlq_entry = {
            "event_type": event_type,
            "payload": payload,
            "error": error_msg,
            "failed_at": datetime.now(timezone.utc).isoformat(),
        }
        await redis.lpush("dlq_events", json.dumps(dlq_entry))
        print(f"[Worker] Routed failed event {event_type} to DLQ.")
    except Exception as e:
        print(f"[Worker] Critical: Failed to route event to DLQ: {e}")

async def process_with_retry(redis, handler, event_type, payload, max_retries=3, base_backoff=1.0):
    attempt = 0
    while True:
        try:
            await handler(payload.get("data", {}))
            return
        except Exception as e:
            attempt += 1
            if attempt > max_retries:
                print(f"[Worker] Event {event_type} failed after {max_retries} attempts. Routing to DLQ...")
                await route_to_dlq(redis, event_type, payload, str(e))
                return
            
            backoff = base_backoff * (2 ** (attempt - 1))
            print(f"[Worker] Error handling {event_type} (attempt {attempt}/{max_retries}): {e}. Retrying in {backoff}s...")
            await asyncio.sleep(backoff)

async def main():
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    print(f"[Worker] Connecting to Redis at {redis_url}...")
    try:
        redis = aioredis.from_url(redis_url, decode_responses=True)
        pubsub = redis.pubsub()
        await pubsub.subscribe("product_events", "order_events", "review_events")
        print("[Worker] Subscribed to 'product_events', 'order_events', and 'review_events' channels. Listening for events...")
    except Exception as e:
        print(f"[Worker] Failed to initialize Redis subscriber: {e}")
        return

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    payload = json.loads(message["data"])
                    event_type = payload.get("event_type")
                    
                    print(f"[Worker] Received event: {event_type}")
                    if event_type in ("product_created", "product_updated"):
                        asyncio.create_task(
                            process_with_retry(redis, handle_product_created_or_updated, event_type, payload)
                        )
                    elif event_type == "order_created":
                        asyncio.create_task(
                            process_with_retry(redis, handle_order_created, event_type, payload)
                        )
                    elif event_type == "review_created":
                        asyncio.create_task(
                            process_with_retry(redis, handle_review_created, event_type, payload)
                        )
                except Exception as ex:
                    print(f"[Worker] Error processing message: {ex}")
    except asyncio.CancelledError:
        print("[Worker] Shutting down...")
    finally:
        await pubsub.unsubscribe("product_events", "order_events", "review_events")
        await redis.close()
        await engine.dispose()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[Worker] Interrupted by user. Exiting.")

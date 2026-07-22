import os
import json
import asyncio
from typing import Any, Dict
from dotenv import load_dotenv
import redis.asyncio as aioredis
import logging
logger = logging.getLogger(__name__)

load_dotenv()

class EventBus:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL")
        self.redis = None
        self._connected = False

    async def connect(self):
        if not self.redis_url:
            logger.info("[EventBus] REDIS_URL not configured. Running in fallback (in-memory) mode.")
            return
        try:
            self.redis = aioredis.from_url(self.redis_url, decode_responses=True)
            await self.redis.ping()
            self._connected = True
            logger.info("[EventBus] Successfully connected to Redis event broker.")
        except Exception as e:
            logger.info(f"[EventBus] Failed to connect to Redis: {e}. Running in fallback (in-memory) mode.")
            self._connected = False

    async def publish(self, channel: str, event_type: str, data: Dict[str, Any]):
        message = {
            "event_type": event_type,
            "data": data
        }
        message_str = json.dumps(message)
        
        if self._connected and self.redis:
            try:
                await self.redis.publish(channel, message_str)
                logger.info(f"[EventBus] Published {event_type} event to Redis channel '{channel}'")
                return True
            except Exception as e:
                logger.info(f"[EventBus] Failed to publish event to Redis: {e}")
        
        # Fallback to local warning (FastAPI BackgroundTasks will execute in-process)
        logger.info(f"[EventBus] Fallback: Logged event {event_type} in-memory")
        return False

    async def close(self):
        if self.redis:
            await self.redis.close()

event_bus = EventBus()

"""
Marketing Service — Redis Pub/Sub サブスクライバー

order_events チャネルを購読し、受信したイベントを
マーケティング用リードモデルに投影(Projection)する。

注意: Redis Pub/Sub は fire-and-forget 方式。
サービスがダウンしている間のイベントは失われる。
本番環境では Redis Streams や Kafka を使うべき。
"""

import asyncio
import json
import logging

import redis.asyncio as aioredis
from sqlalchemy.orm import sessionmaker

from . import projections

logger = logging.getLogger(__name__)


async def run_subscriber(
    redis_url: str,
    async_session_factory: sessionmaker,
    shutdown_event: asyncio.Event,
) -> None:
    """
    order_events チャネルを購読し、イベントをマーケティングモデルに投影する。
    shutdown_event がセットされるまで無限ループで待機する。
    """
    redis_conn = aioredis.from_url(redis_url, decode_responses=True)
    pubsub = redis_conn.pubsub()
    await pubsub.subscribe("order_events")
    logger.info("Subscribed to order_events channel")

    try:
        while not shutdown_event.is_set():
            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=1.0
            )
            if message and message["type"] == "message":
                try:
                    event = json.loads(message["data"])
                    event_type = event.get("event_type")
                    event_data = event.get("data", {})

                    async with async_session_factory() as session:
                        await projections.handle_event(
                            session, event_type, event_data
                        )

                    logger.info("Projected event: %s", event_type)
                except Exception:
                    logger.exception("Failed to process event")
            else:
                await asyncio.sleep(0.1)
    finally:
        await pubsub.unsubscribe("order_events")
        await pubsub.aclose()
        await redis_conn.aclose()

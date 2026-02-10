"""
Saga Service — FastAPI エントリーポイント

Saga オーケストレーターを HTTP API として公開する。
BFF からの注文リクエストを受け取り、Saga を実行する。
"""

import os
from contextlib import asynccontextmanager
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import FastAPI
from pydantic import BaseModel

from .orchestrator import OrderSagaOrchestrator

ORDER_SERVICE_URL = os.environ["ORDER_SERVICE_URL"]
INVENTORY_SERVICE_URL = os.environ["INVENTORY_SERVICE_URL"]
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")

redis_pool: aioredis.Redis | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_pool
    redis_pool = aioredis.from_url(REDIS_URL, decode_responses=True)
    yield
    await redis_pool.aclose()


app = FastAPI(title="Saga Orchestrator Service", lifespan=lifespan)


class PlaceOrderRequest(BaseModel):
    order_id: UUID
    customer_name: str
    product_id: UUID
    product_name: str
    quantity: int
    total_price: float


@app.post("/saga/place-order")
async def place_order(req: PlaceOrderRequest):
    """
    注文 Saga を実行する。

    このエンドポイントが Saga 全体のエントリーポイント。
    BFF から呼ばれ、Order Service と Inventory Service を
    オーケストレーションする。
    """
    orchestrator = OrderSagaOrchestrator(
        ORDER_SERVICE_URL,
        INVENTORY_SERVICE_URL,
        redis_pool,
    )
    result = await orchestrator.execute(
        order_id=req.order_id,
        customer_name=req.customer_name,
        product_id=req.product_id,
        product_name=req.product_name,
        quantity=req.quantity,
        total_price=req.total_price,
    )
    return result


@app.get("/health")
async def health():
    return {"status": "ok", "service": "saga-service"}

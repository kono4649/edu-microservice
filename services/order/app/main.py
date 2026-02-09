"""
Order Service — FastAPI エントリーポイント

CQRS パターンに従い、Command (POST) と Query (GET) のエンドポイントを分離。
Event Sourcing により、すべての状態変更をイベントとして記録する。
"""

import os
from contextlib import asynccontextmanager
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from . import commands, event_store, queries

DATABASE_URL = os.environ["DATABASE_URL"]
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
redis_pool: aioredis.Redis | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_pool
    redis_pool = aioredis.from_url(REDIS_URL, decode_responses=True)
    yield
    await redis_pool.aclose()


app = FastAPI(title="Order Service", lifespan=lifespan)


# ── Request / Response Models ────────────────────

class CreateOrderRequest(BaseModel):
    order_id: UUID
    customer_name: str
    product_id: UUID
    product_name: str
    quantity: int
    total_price: float


class UpdateStatusRequest(BaseModel):
    reason: str = ""


# ── Command Endpoints (Write 側) ─────────────────

@app.post("/commands/orders")
async def cmd_create_order(req: CreateOrderRequest):
    """注文作成コマンド"""
    async with async_session() as session:
        agg = await commands.create_order(
            session, redis_pool,
            req.order_id, req.customer_name,
            req.product_id, req.product_name,
            req.quantity, req.total_price,
        )
        return {"order_id": str(agg.id), "status": agg.status, "version": agg.version}


@app.post("/commands/orders/{order_id}/confirm")
async def cmd_confirm_order(order_id: UUID):
    """注文確定コマンド（Saga から呼ばれる）"""
    async with async_session() as session:
        agg = await commands.confirm_order(session, redis_pool, order_id)
        return {"order_id": str(agg.id), "status": agg.status}


@app.post("/commands/orders/{order_id}/cancel")
async def cmd_cancel_order(order_id: UUID, req: UpdateStatusRequest):
    """注文キャンセルコマンド（Saga の補償トランザクション）"""
    async with async_session() as session:
        agg = await commands.cancel_order(session, redis_pool, order_id, req.reason)
        return {"order_id": str(agg.id), "status": agg.status}


# ── Query Endpoints (Read 側) ────────────────────

@app.get("/queries/orders")
async def query_list_orders():
    """全注文をリードモデルから取得"""
    async with async_session() as session:
        return await queries.list_orders(session)


@app.get("/queries/orders/{order_id}")
async def query_get_order(order_id: UUID):
    """指定注文をリードモデルから取得"""
    async with async_session() as session:
        order = await queries.get_order(session, order_id)
        if not order:
            raise HTTPException(404, "Order not found")
        return order


# ── Event Store (学習・デバッグ用) ───────────────

@app.get("/events")
async def get_all_events():
    """イベントストアの全イベントを返す（学習用）"""
    async with async_session() as session:
        return await event_store.load_all_events(session)


@app.get("/events/{aggregate_id}")
async def get_aggregate_events(aggregate_id: UUID):
    """指定集約のイベントを返す"""
    async with async_session() as session:
        return await event_store.load_events(session, aggregate_id)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "order-service"}

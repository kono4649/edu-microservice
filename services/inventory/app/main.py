"""
Inventory Service — FastAPI エントリーポイント

在庫管理サービス。CQRS + Event Sourcing パターン。
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


app = FastAPI(title="Inventory Service", lifespan=lifespan)


# ── Request Models ───────────────────────────────


class ReserveRequest(BaseModel):
    order_id: UUID
    quantity: int


class ReleaseRequest(BaseModel):
    order_id: UUID
    quantity: int


# ── Command Endpoints (Write 側) ─────────────────


@app.post("/commands/inventory/{product_id}/reserve")
async def cmd_reserve(product_id: UUID, req: ReserveRequest):
    """在庫引き当てコマンド"""
    async with async_session() as session:
        result = await commands.reserve_inventory(
            session,
            redis_pool,
            product_id,
            req.order_id,
            req.quantity,
        )
        if not result["success"]:
            raise HTTPException(status_code=409, detail=result["reason"])
        return result


@app.post("/commands/inventory/{product_id}/release")
async def cmd_release(product_id: UUID, req: ReleaseRequest):
    """在庫解放コマンド（補償トランザクション）"""
    async with async_session() as session:
        return await commands.release_inventory(
            session,
            redis_pool,
            product_id,
            req.order_id,
            req.quantity,
        )


# ── Query Endpoints (Read 側) ────────────────────


@app.get("/queries/products")
async def query_list_products():
    """全商品をリードモデルから取得"""
    async with async_session() as session:
        return await queries.list_products(session)


@app.get("/queries/products/{product_id}")
async def query_get_product(product_id: UUID):
    """指定商品をリードモデルから取得"""
    async with async_session() as session:
        product = await queries.get_product(session, product_id)
        if not product:
            raise HTTPException(404, "Product not found")
        return product


# ── Event Store (学習・デバッグ用) ───────────────


@app.get("/events")
async def get_all_events():
    async with async_session() as session:
        return await event_store.load_all_events(session)


@app.get("/events/{aggregate_id}")
async def get_aggregate_events(aggregate_id: UUID):
    async with async_session() as session:
        return await event_store.load_events(session, aggregate_id)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "inventory-service"}

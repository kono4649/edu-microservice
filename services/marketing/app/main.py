"""
Marketing Service — FastAPI エントリーポイント

マーケティング用リードモデルの Query API を提供する。
Redis Pub/Sub で order_events チャネルを購読し、
バックグラウンドでイベントをリードモデルに投影する。

このサービスは CQRS の Read 側のみ。Command エンドポイントは持たない。
Order Service とは独立した DB にマーケティング最適化データを保持する。

┌──────────────┐   order_events   ┌───────────────────┐
│ Order Service │ ──── Redis ────▶ │ Marketing Service │
│ (Write 側)   │   Pub/Sub        │ (Read 側のみ)     │
└──────────────┘                   └────────┬──────────┘
                                            │
                                   ┌────────▼──────────┐
                                   │  Marketing DB     │
                                   │  (専用リードモデル) │
                                   └───────────────────┘
"""

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from . import queries
from .subscriber import run_subscriber

DATABASE_URL = os.environ["DATABASE_URL"]
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """起動時に Redis サブスクライバをバックグラウンドタスクとして開始する。"""
    shutdown_event = asyncio.Event()
    subscriber_task = asyncio.create_task(
        run_subscriber(REDIS_URL, async_session, shutdown_event)
    )
    yield
    shutdown_event.set()
    subscriber_task.cancel()
    try:
        await subscriber_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Marketing Service", lifespan=lifespan)


# ── Query Endpoints (Read 側のみ) ─────────────────


@app.get("/queries/marketing/customers")
async def query_customer_summary():
    """顧客サマリーを取得(マーケティング用リードモデル)"""
    async with async_session() as session:
        return await queries.list_customer_summaries(session)


@app.get("/queries/marketing/customers/{customer_name}")
async def query_customer_detail(customer_name: str):
    """特定顧客の詳細を取得"""
    async with async_session() as session:
        result = await queries.get_customer_summary(session, customer_name)
        if not result:
            return {"detail": "Customer not found"}
        return result


@app.get("/queries/marketing/products")
async def query_product_popularity():
    """商品人気ランキングを取得"""
    async with async_session() as session:
        return await queries.list_product_popularity(session)


@app.get("/queries/marketing/daily")
async def query_daily_sales():
    """日別売上サマリーを取得"""
    async with async_session() as session:
        return await queries.list_daily_sales(session)


@app.get("/queries/marketing/overview")
async def query_marketing_overview():
    """マーケティングダッシュボード概要(集約データ)"""
    async with async_session() as session:
        return await queries.get_marketing_overview(session)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "marketing-service"}

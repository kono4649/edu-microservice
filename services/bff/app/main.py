"""
BFF (Backend for Frontend) サービス

BFF パターン:
  フロントエンド専用の API ゲートウェイ。
  複数のバックエンドサービスを集約し、フロントエンドが
  使いやすい形に変換して返す。

  役割:
  - フロントエンドに最適化された API を提供
  - 複数サービスのデータを集約して1回のレスポンスで返す
  - バックエンドサービスの内部構造をフロントエンドから隠蔽
  - 認証・認可の集中管理（本サンプルでは省略）

  ┌──────────┐     ┌─────┐     ┌─────────────────┐
  │  React   │────▶│ BFF │────▶│ Order Service   │
  │ Frontend │     │     │────▶│ Inventory Svc   │
  │          │     │     │────▶│ Saga Service    │
  │          │     │     │────▶│ Marketing Svc   │
  └──────────┘     └─────┘     └─────────────────┘
"""

import os
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

import httpx
import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

ORDER_SERVICE_URL = os.environ["ORDER_SERVICE_URL"]
INVENTORY_SERVICE_URL = os.environ["INVENTORY_SERVICE_URL"]
SAGA_SERVICE_URL = os.environ["SAGA_SERVICE_URL"]
MARKETING_SERVICE_URL = os.environ["MARKETING_SERVICE_URL"]
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")

redis_pool: aioredis.Redis | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_pool
    redis_pool = aioredis.from_url(REDIS_URL, decode_responses=True)
    yield
    await redis_pool.aclose()


app = FastAPI(title="BFF - Backend for Frontend", lifespan=lifespan)

# CORS 設定（React dev server からのアクセスを許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request Models ───────────────────────────────


class PlaceOrderRequest(BaseModel):
    customer_name: str
    product_id: UUID
    quantity: int


# ── フロントエンド向け集約 API ───────────────────


@app.get("/api/products")
async def get_products():
    """
    商品一覧を取得（BFF が Inventory Service から取得して返す）
    フロントエンドは BFF だけを知っていればよい。
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{INVENTORY_SERVICE_URL}/queries/products")
        resp.raise_for_status()
        return resp.json()


@app.get("/api/products/{product_id}")
async def get_product(product_id: UUID):
    """商品詳細を取得"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{INVENTORY_SERVICE_URL}/queries/products/{product_id}"
        )
        if resp.status_code == 404:
            raise HTTPException(404, "Product not found")
        resp.raise_for_status()
        return resp.json()


@app.post("/api/orders")
async def place_order(req: PlaceOrderRequest):
    """
    注文を作成する（BFF → Saga Orchestrator）

    BFF が:
    1. 商品情報を取得（名前と価格）
    2. 合計金額を計算
    3. Saga Orchestrator に注文を委譲

    フロントエンドは Saga の存在を知らない — BFF が隠蔽する。
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. 商品情報を取得
        prod_resp = await client.get(
            f"{INVENTORY_SERVICE_URL}/queries/products/{req.product_id}"
        )
        if prod_resp.status_code == 404:
            raise HTTPException(404, "Product not found")
        prod_resp.raise_for_status()
        product = prod_resp.json()

        # 2. 合計金額を計算
        total_price = product["price"] * req.quantity

        # 3. Saga Orchestrator に委譲
        order_id = uuid4()
        saga_resp = await client.post(
            f"{SAGA_SERVICE_URL}/saga/place-order",
            json={
                "order_id": str(order_id),
                "customer_name": req.customer_name,
                "product_id": str(req.product_id),
                "product_name": product["product_name"],
                "quantity": req.quantity,
                "total_price": total_price,
            },
        )
        saga_resp.raise_for_status()
        result = saga_resp.json()

        return {
            "order_id": str(order_id),
            "success": result["success"],
            "saga_log": result["saga_log"],
        }


@app.get("/api/orders")
async def get_orders():
    """注文一覧を取得"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{ORDER_SERVICE_URL}/queries/orders")
        resp.raise_for_status()
        return resp.json()


@app.get("/api/orders/{order_id}")
async def get_order(order_id: UUID):
    """注文詳細を取得"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{ORDER_SERVICE_URL}/queries/orders/{order_id}")
        if resp.status_code == 404:
            raise HTTPException(404, "Order not found")
        resp.raise_for_status()
        return resp.json()


@app.get("/api/dashboard")
async def get_dashboard():
    """
    ダッシュボード — 複数サービスのデータを集約して返す。

    BFF パターンの真価: フロントエンドが1回のリクエストで
    必要な全データを取得できる。バックエンドの複雑さを隠蔽。
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        products_resp, orders_resp = await _parallel_fetch(client)
        return {
            "products": products_resp,
            "orders": orders_resp,
        }


async def _parallel_fetch(client: httpx.AsyncClient):
    """複数サービスへ並列リクエスト"""
    import asyncio

    products_task = asyncio.create_task(
        client.get(f"{INVENTORY_SERVICE_URL}/queries/products")
    )
    orders_task = asyncio.create_task(client.get(f"{ORDER_SERVICE_URL}/queries/orders"))
    products_resp, orders_resp = await asyncio.gather(products_task, orders_task)
    return products_resp.json(), orders_resp.json()


# ── イベントログ（学習用） ───────────────────────


@app.get("/api/events")
async def get_all_events():
    """全サービスのイベントを集約して時系列で返す（学習用）"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        import asyncio

        order_task = asyncio.create_task(client.get(f"{ORDER_SERVICE_URL}/events"))
        inventory_task = asyncio.create_task(
            client.get(f"{INVENTORY_SERVICE_URL}/events")
        )
        order_resp, inv_resp = await asyncio.gather(order_task, inventory_task)

        all_events = []
        for e in order_resp.json():
            e["service"] = "order-service"
            all_events.append(e)
        for e in inv_resp.json():
            e["service"] = "inventory-service"
            all_events.append(e)

        all_events.sort(key=lambda x: x.get("created_at", ""))
        return all_events


# ── マーケティングダッシュボード ─────────────────


@app.get("/api/marketing/overview")
async def get_marketing_overview():
    """マーケティング概要を取得(Marketing Service から)"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{MARKETING_SERVICE_URL}/queries/marketing/overview"
        )
        resp.raise_for_status()
        return resp.json()


@app.get("/api/marketing/customers")
async def get_marketing_customers():
    """顧客サマリーを取得"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{MARKETING_SERVICE_URL}/queries/marketing/customers"
        )
        resp.raise_for_status()
        return resp.json()


@app.get("/api/marketing/products")
async def get_marketing_products():
    """商品人気ランキングを取得"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{MARKETING_SERVICE_URL}/queries/marketing/products"
        )
        resp.raise_for_status()
        return resp.json()


@app.get("/api/marketing/daily")
async def get_marketing_daily():
    """日別売上サマリーを取得"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{MARKETING_SERVICE_URL}/queries/marketing/daily"
        )
        resp.raise_for_status()
        return resp.json()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "bff"}

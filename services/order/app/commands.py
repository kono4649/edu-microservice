"""
Order Service — コマンドハンドラ (CQRS の Write 側)

CQRS パターンでは、書き込み(Command)と読み取り(Query)を分離する。
コマンドは状態を変更する操作で、イベントを生成してストアに保存する。
同時にリードモデル(Read Model)も更新する。
"""

import json
from datetime import datetime, timezone
from uuid import UUID

import redis.asyncio as aioredis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from . import event_store
from .aggregate import OrderAggregate


async def create_order(
    session: AsyncSession,
    redis: aioredis.Redis,
    order_id: UUID,
    customer_name: str,
    product_id: UUID,
    product_name: str,
    quantity: int,
    total_price: float,
) -> OrderAggregate:
    """
    注文作成コマンド

    1. OrderCreated イベントを生成
    2. イベントストアに保存
    3. リードモデルを更新
    4. Redis Pub/Sub でイベントを発行（他サービスへ通知）
    """
    now = datetime.now(timezone.utc)
    event_data = {
        "order_id": str(order_id),
        "customer_name": customer_name,
        "product_id": str(product_id),
        "product_name": product_name,
        "quantity": quantity,
        "total_price": total_price,
        "timestamp": now.isoformat(),
    }

    # 1. イベントストアに追記
    version = await event_store.append_event(
        session, order_id, "Order", "OrderCreated", event_data, 0
    )

    # 2. リードモデルを更新 (CQRS: Write 側がリードモデルも更新)
    await session.execute(
        text("""
            INSERT INTO orders_read_model
                (id, customer_name, product_id, product_name, quantity, total_price, status, created_at, updated_at)
            VALUES
                (:id, :customer_name, :product_id, :product_name, :quantity, :total_price, 'PENDING', :now, :now)
        """),
        {
            "id": str(order_id),
            "customer_name": customer_name,
            "product_id": str(product_id),
            "product_name": product_name,
            "quantity": quantity,
            "total_price": total_price,
            "now": now,
        },
    )

    await session.commit()

    # 3. Redis Pub/Sub でイベントを発行
    await redis.publish("order_events", json.dumps({
        "event_type": "OrderCreated",
        "data": event_data,
    }, default=str))

    # 4. 集約を返す
    agg = OrderAggregate()
    agg.apply_order_created(event_data)
    agg.version = version
    return agg


async def confirm_order(
    session: AsyncSession,
    redis: aioredis.Redis,
    order_id: UUID,
) -> OrderAggregate:
    """
    注文確定コマンド（Saga から呼ばれる）

    在庫の引き当てが成功した場合に実行される。
    """
    # 現在の集約をイベントから再構築
    events = await event_store.load_events(session, order_id)
    agg = OrderAggregate.from_events(events)

    now = datetime.now(timezone.utc)
    event_data = {"order_id": str(order_id), "timestamp": now.isoformat()}

    # イベント追記
    version = await event_store.append_event(
        session, order_id, "Order", "OrderConfirmed", event_data, agg.version
    )

    # リードモデル更新
    await session.execute(
        text("""
            UPDATE orders_read_model
            SET status = 'CONFIRMED', updated_at = :now
            WHERE id = :id
        """),
        {"id": str(order_id), "now": now},
    )

    await session.commit()

    await redis.publish("order_events", json.dumps({
        "event_type": "OrderConfirmed",
        "data": event_data,
    }, default=str))

    agg.apply_order_confirmed(event_data)
    agg.version = version
    return agg


async def cancel_order(
    session: AsyncSession,
    redis: aioredis.Redis,
    order_id: UUID,
    reason: str,
) -> OrderAggregate:
    """
    注文キャンセルコマンド（Saga の補償トランザクション）

    在庫の引き当てが失敗した場合、Saga が補償としてこのコマンドを実行する。
    """
    events = await event_store.load_events(session, order_id)
    agg = OrderAggregate.from_events(events)

    now = datetime.now(timezone.utc)
    event_data = {
        "order_id": str(order_id),
        "reason": reason,
        "timestamp": now.isoformat(),
    }

    version = await event_store.append_event(
        session, order_id, "Order", "OrderCancelled", event_data, agg.version
    )

    await session.execute(
        text("""
            UPDATE orders_read_model
            SET status = 'CANCELLED', updated_at = :now
            WHERE id = :id
        """),
        {"id": str(order_id), "now": now},
    )

    await session.commit()

    await redis.publish("order_events", json.dumps({
        "event_type": "OrderCancelled",
        "data": event_data,
    }, default=str))

    agg.apply_order_cancelled(event_data)
    agg.version = version
    return agg

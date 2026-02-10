"""
Inventory Service — コマンドハンドラ (CQRS Write 側)

在庫の引き当て(Reserve)と解放(Release)を処理する。
Saga パターンで重要: 引き当て失敗時は補償トランザクションとして
注文サービスのキャンセルが呼ばれる。
"""

import json
from datetime import datetime, timezone
from uuid import UUID

import redis.asyncio as aioredis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from . import event_store


async def reserve_inventory(
    session: AsyncSession,
    redis: aioredis.Redis,
    product_id: UUID,
    order_id: UUID,
    quantity: int,
) -> dict:
    """
    在庫引き当てコマンド

    1. リードモデルで在庫数を確認
    2. 十分なら InventoryReserved イベントを記録
    3. 不足なら InventoryReservationFailed イベントを記録
    """
    now = datetime.now(timezone.utc)

    # リードモデルから現在の在庫を確認
    result = await session.execute(
        text("SELECT quantity, reserved FROM inventory_read_model WHERE id = :id"),
        {"id": str(product_id)},
    )
    row = result.fetchone()
    if not row:
        return {"success": False, "reason": "Product not found"}

    available = row.quantity - row.reserved

    if available < quantity:
        # 在庫不足 → 失敗イベントを記録
        event_data = {
            "product_id": str(product_id),
            "order_id": str(order_id),
            "quantity_requested": quantity,
            "quantity_available": available,
            "timestamp": now.isoformat(),
        }
        # イベントはバージョン管理のために product_id を aggregate_id として使う
        events = await event_store.load_events(session, product_id)
        current_version = events[-1]["version"] if events else 0

        await event_store.append_event(
            session,
            product_id,
            "Inventory",
            "InventoryReservationFailed",
            event_data,
            current_version,
        )
        await session.commit()

        await redis.publish(
            "inventory_events",
            json.dumps(
                {
                    "event_type": "InventoryReservationFailed",
                    "data": event_data,
                },
                default=str,
            ),
        )

        return {
            "success": False,
            "reason": f"Insufficient stock: requested={quantity}, available={available}",
        }

    # 在庫あり → 引き当てイベントを記録
    event_data = {
        "product_id": str(product_id),
        "order_id": str(order_id),
        "quantity": quantity,
        "timestamp": now.isoformat(),
    }
    events = await event_store.load_events(session, product_id)
    current_version = events[-1]["version"] if events else 0

    await event_store.append_event(
        session,
        product_id,
        "Inventory",
        "InventoryReserved",
        event_data,
        current_version,
    )

    # リードモデル更新
    await session.execute(
        text("""
            UPDATE inventory_read_model
            SET reserved = reserved + :qty, updated_at = :now
            WHERE id = :id
        """),
        {"qty": quantity, "now": now, "id": str(product_id)},
    )
    await session.commit()

    await redis.publish(
        "inventory_events",
        json.dumps(
            {
                "event_type": "InventoryReserved",
                "data": event_data,
            },
            default=str,
        ),
    )

    return {"success": True}


async def release_inventory(
    session: AsyncSession,
    redis: aioredis.Redis,
    product_id: UUID,
    order_id: UUID,
    quantity: int,
) -> dict:
    """
    在庫解放コマンド（Saga の補償トランザクション）

    注文がキャンセルされた場合に引き当て済みの在庫を戻す。
    """
    now = datetime.now(timezone.utc)
    event_data = {
        "product_id": str(product_id),
        "order_id": str(order_id),
        "quantity": quantity,
        "timestamp": now.isoformat(),
    }

    events = await event_store.load_events(session, product_id)
    current_version = events[-1]["version"] if events else 0

    await event_store.append_event(
        session,
        product_id,
        "Inventory",
        "InventoryReleased",
        event_data,
        current_version,
    )

    await session.execute(
        text("""
            UPDATE inventory_read_model
            SET reserved = reserved - :qty, updated_at = :now
            WHERE id = :id
        """),
        {"qty": quantity, "now": now, "id": str(product_id)},
    )
    await session.commit()

    await redis.publish(
        "inventory_events",
        json.dumps(
            {
                "event_type": "InventoryReleased",
                "data": event_data,
            },
            default=str,
        ),
    )

    return {"success": True}

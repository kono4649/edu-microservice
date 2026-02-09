"""
Order Service — クエリハンドラ (CQRS の Read 側)

CQRS パターンでは、読み取りはリードモデル(Read Model)から行う。
リードモデルはイベントから投影(Projection)された非正規化データで、
クエリに最適化されている。
"""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_order(session: AsyncSession, order_id: UUID) -> dict | None:
    """リードモデルから注文を取得する。"""
    result = await session.execute(
        text("SELECT * FROM orders_read_model WHERE id = :id"),
        {"id": str(order_id)},
    )
    row = result.fetchone()
    if not row:
        return None
    return {
        "id": str(row.id),
        "customer_name": row.customer_name,
        "product_id": str(row.product_id),
        "product_name": row.product_name,
        "quantity": row.quantity,
        "total_price": float(row.total_price),
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


async def list_orders(session: AsyncSession) -> list[dict]:
    """全注文一覧をリードモデルから取得する。"""
    result = await session.execute(
        text("SELECT * FROM orders_read_model ORDER BY created_at DESC"),
    )
    return [
        {
            "id": str(row.id),
            "customer_name": row.customer_name,
            "product_id": str(row.product_id),
            "product_name": row.product_name,
            "quantity": row.quantity,
            "total_price": float(row.total_price),
            "status": row.status,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
        for row in result.fetchall()
    ]

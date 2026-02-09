"""
Inventory Service — クエリハンドラ (CQRS Read 側)
"""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_product(session: AsyncSession, product_id: UUID) -> dict | None:
    result = await session.execute(
        text("SELECT * FROM inventory_read_model WHERE id = :id"),
        {"id": str(product_id)},
    )
    row = result.fetchone()
    if not row:
        return None
    return {
        "id": str(row.id),
        "product_name": row.product_name,
        "quantity": row.quantity,
        "reserved": row.reserved,
        "available": row.available,
        "price": float(row.price),
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


async def list_products(session: AsyncSession) -> list[dict]:
    result = await session.execute(
        text("SELECT * FROM inventory_read_model ORDER BY product_name"),
    )
    return [
        {
            "id": str(row.id),
            "product_name": row.product_name,
            "quantity": row.quantity,
            "reserved": row.reserved,
            "available": row.available,
            "price": float(row.price),
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
        for row in result.fetchall()
    ]

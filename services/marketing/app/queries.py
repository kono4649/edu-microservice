"""
Marketing Service — クエリハンドラ (CQRS Read 側)

マーケティング用リードモデルから集約データを返す。
Order Service のリードモデルとは独立しており、
マーケティング分析に特化したクエリを提供する。
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def list_customer_summaries(session: AsyncSession) -> list[dict]:
    """顧客サマリー一覧(売上順)"""
    result = await session.execute(
        text("SELECT * FROM customer_summary ORDER BY total_revenue DESC")
    )
    return [
        {
            "customer_name": row.customer_name,
            "total_orders": row.total_orders,
            "confirmed_orders": row.confirmed_orders,
            "cancelled_orders": row.cancelled_orders,
            "total_revenue": float(row.total_revenue),
            "avg_order_value": float(row.avg_order_value),
            "first_order_at": row.first_order_at.isoformat()
            if row.first_order_at
            else None,
            "last_order_at": row.last_order_at.isoformat()
            if row.last_order_at
            else None,
        }
        for row in result.fetchall()
    ]


async def get_customer_summary(
    session: AsyncSession, customer_name: str
) -> dict | None:
    """特定顧客のサマリー"""
    result = await session.execute(
        text("SELECT * FROM customer_summary WHERE customer_name = :name"),
        {"name": customer_name},
    )
    row = result.fetchone()
    if not row:
        return None
    return {
        "customer_name": row.customer_name,
        "total_orders": row.total_orders,
        "confirmed_orders": row.confirmed_orders,
        "cancelled_orders": row.cancelled_orders,
        "total_revenue": float(row.total_revenue),
        "avg_order_value": float(row.avg_order_value),
        "first_order_at": row.first_order_at.isoformat()
        if row.first_order_at
        else None,
        "last_order_at": row.last_order_at.isoformat() if row.last_order_at else None,
    }


async def list_product_popularity(session: AsyncSession) -> list[dict]:
    """商品人気ランキング(売上順)"""
    result = await session.execute(
        text("SELECT * FROM product_popularity ORDER BY total_revenue DESC")
    )
    return [
        {
            "product_id": str(row.product_id),
            "product_name": row.product_name,
            "total_units_ordered": row.total_units_ordered,
            "confirmed_units": row.confirmed_units,
            "total_order_count": row.total_order_count,
            "confirmed_order_count": row.confirmed_order_count,
            "total_revenue": float(row.total_revenue),
            "unique_customers": row.unique_customers,
        }
        for row in result.fetchall()
    ]


async def list_daily_sales(session: AsyncSession) -> list[dict]:
    """日別売上サマリー(直近30日)"""
    result = await session.execute(
        text("""
            SELECT * FROM daily_sales_summary
            ORDER BY sale_date DESC
            LIMIT 30
        """)
    )
    return [
        {
            "sale_date": row.sale_date.isoformat(),
            "total_orders": row.total_orders,
            "confirmed_orders": row.confirmed_orders,
            "cancelled_orders": row.cancelled_orders,
            "total_revenue": float(row.total_revenue),
            "avg_order_value": float(row.avg_order_value),
        }
        for row in result.fetchall()
    ]


async def get_marketing_overview(session: AsyncSession) -> dict:
    """マーケティングダッシュボード概要 — BFF の集約レスポンス用"""
    customers = await list_customer_summaries(session)
    products = await list_product_popularity(session)
    daily = await list_daily_sales(session)

    total_revenue = sum(c["total_revenue"] for c in customers)
    total_customers = len(customers)
    total_product_types = len(products)

    return {
        "summary": {
            "total_revenue": total_revenue,
            "total_customers": total_customers,
            "total_product_types": total_product_types,
        },
        "top_customers": customers[:5],
        "top_products": products[:5],
        "recent_daily_sales": daily[:7],
    }

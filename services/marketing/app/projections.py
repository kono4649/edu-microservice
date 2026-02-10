"""
Marketing Service — イベント投影 (Projection)

CQRS の Read 側: order_events から受信したイベントを
マーケティング用に最適化されたテーブルに投影する。

Order Service のリードモデルとは独立しており、
マーケティング分析に特化した集計を行う。
"""

from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def handle_event(session: AsyncSession, event_type: str, data: dict) -> None:
    """イベントタイプに応じた投影ハンドラを呼び出す。"""
    handler = {
        "OrderCreated": _project_order_created,
        "OrderConfirmed": _project_order_confirmed,
        "OrderCancelled": _project_order_cancelled,
    }.get(event_type)
    if handler:
        await handler(session, data)
        await session.commit()


async def _project_order_created(session: AsyncSession, data: dict) -> None:
    """
    OrderCreated イベントの投影:
    1. marketing_order_snapshot に新規行を INSERT
    2. customer_summary を UPSERT
    3. product_popularity を UPSERT
    4. product_customer_map にユニーク顧客を追跡
    5. daily_sales_summary を UPSERT
    """
    timestamp = datetime.fromisoformat(data["timestamp"])
    order_date = timestamp.date()

    # 1. Order snapshot
    await session.execute(
        text("""
            INSERT INTO marketing_order_snapshot
                (order_id, customer_name, product_id, product_name,
                 quantity, total_price, status, order_date, created_at, updated_at)
            VALUES
                (:order_id, :customer_name, :product_id, :product_name,
                 :quantity, :total_price, 'PENDING', :order_date, :ts, :ts)
            ON CONFLICT (order_id) DO NOTHING
        """),
        {
            "order_id": data["order_id"],
            "customer_name": data["customer_name"],
            "product_id": data["product_id"],
            "product_name": data["product_name"],
            "quantity": data["quantity"],
            "total_price": data["total_price"],
            "order_date": order_date,
            "ts": timestamp,
        },
    )

    # 2. Customer summary (UPSERT)
    await session.execute(
        text("""
            INSERT INTO customer_summary
                (customer_name, total_orders, total_revenue, avg_order_value,
                 first_order_at, last_order_at, updated_at)
            VALUES
                (:name, 1, :price, :price, :ts, :ts, :ts)
            ON CONFLICT (customer_name) DO UPDATE SET
                total_orders = customer_summary.total_orders + 1,
                total_revenue = customer_summary.total_revenue + :price,
                avg_order_value = (customer_summary.total_revenue + :price)
                    / (customer_summary.total_orders + 1),
                last_order_at = :ts,
                updated_at = :ts
        """),
        {"name": data["customer_name"], "price": data["total_price"], "ts": timestamp},
    )

    # 3. Product popularity (UPSERT)
    await session.execute(
        text("""
            INSERT INTO product_popularity
                (product_id, product_name, total_units_ordered, total_order_count,
                 total_revenue, unique_customers, updated_at)
            VALUES
                (:pid, :pname, :qty, 1, :price, 0, :ts)
            ON CONFLICT (product_id) DO UPDATE SET
                total_units_ordered = product_popularity.total_units_ordered + :qty,
                total_order_count = product_popularity.total_order_count + 1,
                total_revenue = product_popularity.total_revenue + :price,
                updated_at = :ts
        """),
        {
            "pid": data["product_id"],
            "pname": data["product_name"],
            "qty": data["quantity"],
            "price": data["total_price"],
            "ts": timestamp,
        },
    )

    # 4. Track unique customers per product
    await session.execute(
        text("""
            INSERT INTO product_customer_map (product_id, customer_name)
            VALUES (:pid, :name)
            ON CONFLICT DO NOTHING
        """),
        {"pid": data["product_id"], "name": data["customer_name"]},
    )
    await session.execute(
        text("""
            UPDATE product_popularity
            SET unique_customers = (
                SELECT COUNT(*) FROM product_customer_map WHERE product_id = :pid
            )
            WHERE product_id = :pid
        """),
        {"pid": data["product_id"]},
    )

    # 5. Daily sales summary (UPSERT)
    await session.execute(
        text("""
            INSERT INTO daily_sales_summary
                (sale_date, total_orders, total_revenue, avg_order_value, updated_at)
            VALUES
                (:dt, 1, :price, :price, :ts)
            ON CONFLICT (sale_date) DO UPDATE SET
                total_orders = daily_sales_summary.total_orders + 1,
                total_revenue = daily_sales_summary.total_revenue + :price,
                avg_order_value = (daily_sales_summary.total_revenue + :price)
                    / (daily_sales_summary.total_orders + 1),
                updated_at = :ts
        """),
        {"dt": order_date, "price": data["total_price"], "ts": timestamp},
    )


async def _project_order_confirmed(session: AsyncSession, data: dict) -> None:
    """
    OrderConfirmed イベントの投影:
    snapshot から注文情報を取得し、各集計テーブルの confirmed カウントを更新。
    """
    timestamp = datetime.fromisoformat(data["timestamp"])

    result = await session.execute(
        text("SELECT * FROM marketing_order_snapshot WHERE order_id = :oid"),
        {"oid": data["order_id"]},
    )
    order = result.fetchone()
    if not order:
        return

    # 1. Update snapshot status
    await session.execute(
        text("""
            UPDATE marketing_order_snapshot
            SET status = 'CONFIRMED', updated_at = :ts
            WHERE order_id = :oid
        """),
        {"oid": data["order_id"], "ts": timestamp},
    )

    # 2. Customer confirmed_orders
    await session.execute(
        text("""
            UPDATE customer_summary
            SET confirmed_orders = confirmed_orders + 1, updated_at = :ts
            WHERE customer_name = :name
        """),
        {"name": order.customer_name, "ts": timestamp},
    )

    # 3. Product confirmed counts
    await session.execute(
        text("""
            UPDATE product_popularity
            SET confirmed_units = confirmed_units + :qty,
                confirmed_order_count = confirmed_order_count + 1,
                updated_at = :ts
            WHERE product_id = :pid
        """),
        {"qty": order.quantity, "pid": str(order.product_id), "ts": timestamp},
    )

    # 4. Daily confirmed count
    await session.execute(
        text("""
            UPDATE daily_sales_summary
            SET confirmed_orders = confirmed_orders + 1, updated_at = :ts
            WHERE sale_date = :dt
        """),
        {"dt": order.order_date, "ts": timestamp},
    )


async def _project_order_cancelled(session: AsyncSession, data: dict) -> None:
    """
    OrderCancelled イベントの投影:
    snapshot から注文情報を取得し、cancelled カウントを更新。
    """
    timestamp = datetime.fromisoformat(data["timestamp"])

    result = await session.execute(
        text("SELECT * FROM marketing_order_snapshot WHERE order_id = :oid"),
        {"oid": data["order_id"]},
    )
    order = result.fetchone()
    if not order:
        return

    # 1. Update snapshot status
    await session.execute(
        text("""
            UPDATE marketing_order_snapshot
            SET status = 'CANCELLED', updated_at = :ts
            WHERE order_id = :oid
        """),
        {"oid": data["order_id"], "ts": timestamp},
    )

    # 2. Customer cancelled_orders
    await session.execute(
        text("""
            UPDATE customer_summary
            SET cancelled_orders = cancelled_orders + 1, updated_at = :ts
            WHERE customer_name = :name
        """),
        {"name": order.customer_name, "ts": timestamp},
    )

    # 3. Daily cancelled count
    await session.execute(
        text("""
            UPDATE daily_sales_summary
            SET cancelled_orders = cancelled_orders + 1, updated_at = :ts
            WHERE sale_date = :dt
        """),
        {"dt": order.order_date, "ts": timestamp},
    )

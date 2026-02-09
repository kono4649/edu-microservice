"""
Order Service — イベントストア

Event Sourcing の中核コンポーネント。
イベントを PostgreSQL に追記し、集約の再構築に使う。
バージョン番号による楽観的ロックで同時書き込みを防ぐ。
"""

import json
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def append_event(
    session: AsyncSession,
    aggregate_id: UUID,
    aggregate_type: str,
    event_type: str,
    event_data: dict,
    expected_version: int,
) -> int:
    """
    イベントをストアに追記する。

    expected_version で楽観的ロックを実現:
    同じ aggregate_id + version の組み合わせが既に存在すると
    UNIQUE 制約違反で失敗する → 競合を検知できる。
    """
    new_version = expected_version + 1
    await session.execute(
        text("""
            INSERT INTO event_store
                (aggregate_id, aggregate_type, event_type, event_data, version, created_at)
            VALUES
                (:agg_id, :agg_type, :evt_type, :evt_data, :version, :now)
        """),
        {
            "agg_id": str(aggregate_id),
            "agg_type": aggregate_type,
            "evt_type": event_type,
            "evt_data": json.dumps(event_data, default=str),
            "version": new_version,
            "now": datetime.now(timezone.utc),
        },
    )
    return new_version


async def load_events(
    session: AsyncSession,
    aggregate_id: UUID,
) -> list[dict]:
    """
    指定した集約の全イベントをバージョン順に読み出す。
    集約を再構築（リプレイ）するために使う。
    """
    result = await session.execute(
        text("""
            SELECT event_type, event_data, version, created_at
            FROM event_store
            WHERE aggregate_id = :agg_id
            ORDER BY version ASC
        """),
        {"agg_id": str(aggregate_id)},
    )
    return [
        {
            "event_type": row.event_type,
            "event_data": json.loads(row.event_data) if isinstance(row.event_data, str) else row.event_data,
            "version": row.version,
            "created_at": row.created_at,
        }
        for row in result.fetchall()
    ]


async def load_all_events(session: AsyncSession) -> list[dict]:
    """すべてのイベントを時系列順に返す（デバッグ・学習用）。"""
    result = await session.execute(
        text("""
            SELECT aggregate_id, aggregate_type, event_type, event_data, version, created_at
            FROM event_store
            ORDER BY created_at ASC, version ASC
        """),
    )
    return [
        {
            "aggregate_id": str(row.aggregate_id),
            "aggregate_type": row.aggregate_type,
            "event_type": row.event_type,
            "event_data": json.loads(row.event_data) if isinstance(row.event_data, str) else row.event_data,
            "version": row.version,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in result.fetchall()
    ]

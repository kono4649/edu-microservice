"""
Order Service — イベント定義

Event Sourcing では、ドメインで発生した事実(イベント)を定義する。
イベントは過去形で命名し、不変(immutable)として扱う。
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class OrderCreated(BaseModel):
    """注文が作成された"""
    order_id: UUID
    customer_name: str
    product_id: UUID
    product_name: str
    quantity: int
    total_price: float
    timestamp: datetime


class OrderConfirmed(BaseModel):
    """注文が確定された（在庫引き当て成功）"""
    order_id: UUID
    timestamp: datetime


class OrderCancelled(BaseModel):
    """注文がキャンセルされた（在庫引き当て失敗 = 補償トランザクション）"""
    order_id: UUID
    reason: str
    timestamp: datetime

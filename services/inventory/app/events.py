"""
Inventory Service — イベント定義

在庫ドメインで発生するイベント。
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class InventoryReserved(BaseModel):
    """在庫が引き当てられた"""
    product_id: UUID
    order_id: UUID
    quantity: int
    timestamp: datetime


class InventoryReservationFailed(BaseModel):
    """在庫引き当てが失敗した（在庫不足）"""
    product_id: UUID
    order_id: UUID
    quantity_requested: int
    quantity_available: int
    timestamp: datetime


class InventoryReleased(BaseModel):
    """在庫の引き当てが解放された（補償トランザクション）"""
    product_id: UUID
    order_id: UUID
    quantity: int
    timestamp: datetime

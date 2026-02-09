"""
Order Service — 注文集約 (Order Aggregate)

Event Sourcing では集約の状態を直接保存しない。
イベントをリプレイして現在の状態を復元する。

apply_xxx メソッド: 各イベントを適用して状態を変更する
"""

from uuid import UUID


class OrderAggregate:
    """
    注文集約 — イベントから現在の状態を再構築する。

    状態遷移:
        PENDING → CONFIRMED  (在庫引き当て成功)
        PENDING → CANCELLED  (在庫引き当て失敗 = 補償)
    """

    def __init__(self) -> None:
        self.id: UUID | None = None
        self.customer_name: str = ""
        self.product_id: UUID | None = None
        self.product_name: str = ""
        self.quantity: int = 0
        self.total_price: float = 0
        self.status: str = "UNKNOWN"
        self.version: int = 0

    # ── イベント適用メソッド ──────────────────────────

    def apply_order_created(self, data: dict) -> None:
        self.id = UUID(data["order_id"])
        self.customer_name = data["customer_name"]
        self.product_id = UUID(data["product_id"])
        self.product_name = data["product_name"]
        self.quantity = data["quantity"]
        self.total_price = data["total_price"]
        self.status = "PENDING"

    def apply_order_confirmed(self, _data: dict) -> None:
        self.status = "CONFIRMED"

    def apply_order_cancelled(self, data: dict) -> None:
        self.status = "CANCELLED"

    # ── イベントリプレイ ─────────────────────────────

    def apply_event(self, event_type: str, event_data: dict) -> None:
        """イベントタイプに応じた apply メソッドを呼び出す。"""
        handler = {
            "OrderCreated": self.apply_order_created,
            "OrderConfirmed": self.apply_order_confirmed,
            "OrderCancelled": self.apply_order_cancelled,
        }.get(event_type)
        if handler:
            handler(event_data)

    @classmethod
    def from_events(cls, events: list[dict]) -> "OrderAggregate":
        """イベント列から集約を再構築する。"""
        agg = cls()
        for e in events:
            agg.apply_event(e["event_type"], e["event_data"])
            agg.version = e["version"]
        return agg

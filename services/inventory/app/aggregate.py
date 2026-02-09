"""
Inventory Service — 在庫集約 (Inventory Aggregate)

在庫数と予約数をイベントから再構築する。
available = quantity - reserved で算出。
"""

from uuid import UUID


class InventoryAggregate:
    def __init__(self) -> None:
        self.id: UUID | None = None
        self.product_name: str = ""
        self.quantity: int = 0
        self.reserved: int = 0
        self.version: int = 0

    @property
    def available(self) -> int:
        return self.quantity - self.reserved

    def apply_inventory_reserved(self, data: dict) -> None:
        self.reserved += data["quantity"]

    def apply_inventory_released(self, data: dict) -> None:
        self.reserved -= data["quantity"]

    def apply_event(self, event_type: str, event_data: dict) -> None:
        handler = {
            "InventoryReserved": self.apply_inventory_reserved,
            "InventoryReleased": self.apply_inventory_released,
        }.get(event_type)
        if handler:
            handler(event_data)

    @classmethod
    def from_events(cls, events: list[dict]) -> "InventoryAggregate":
        agg = cls()
        for e in events:
            agg.apply_event(e["event_type"], e["event_data"])
            agg.version = e["version"]
        return agg

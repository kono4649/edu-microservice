"""
Saga Orchestrator — 注文・在庫 Saga

Saga パターン（オーケストレーション型）:
  中央のオーケストレーターが各サービスへのコマンド実行を制御する。
  失敗時は補償トランザクション(Compensating Transaction)を実行して
  整合性を保つ。

  フロー:
  ┌─────────────────────────────────────────────────────────┐
  │  1. Order Service に注文作成を依頼                        │
  │  2. Inventory Service に在庫引き当てを依頼                │
  │     ├─ 成功 → Order Service に注文確定を依頼             │
  │     └─ 失敗 → Order Service に注文キャンセルを依頼       │
  │              (補償トランザクション)                       │
  └─────────────────────────────────────────────────────────┘
"""

import json
from datetime import datetime, timezone
from uuid import UUID

import httpx
import redis.asyncio as aioredis


class OrderSagaOrchestrator:
    """注文 Saga のオーケストレーター"""

    def __init__(
        self,
        order_service_url: str,
        inventory_service_url: str,
        redis: aioredis.Redis,
    ):
        self.order_url = order_service_url
        self.inventory_url = inventory_service_url
        self.redis = redis

    async def execute(
        self,
        order_id: UUID,
        customer_name: str,
        product_id: UUID,
        product_name: str,
        quantity: int,
        total_price: float,
    ) -> dict:
        """
        Saga を実行する。

        各ステップの結果に応じて次のアクションを決定する。
        失敗時は補償トランザクションを実行して一貫性を保つ。
        """
        saga_log: list[dict] = []
        now = datetime.now(timezone.utc).isoformat()

        async with httpx.AsyncClient(timeout=30.0) as client:
            # ── Step 1: 注文を作成 ──────────────────────
            saga_log.append(
                {
                    "step": 1,
                    "action": "CreateOrder",
                    "status": "EXECUTING",
                    "timestamp": now,
                }
            )

            try:
                resp = await client.post(
                    f"{self.order_url}/commands/orders",
                    json={
                        "order_id": str(order_id),
                        "customer_name": customer_name,
                        "product_id": str(product_id),
                        "product_name": product_name,
                        "quantity": quantity,
                        "total_price": total_price,
                    },
                )
                resp.raise_for_status()
                saga_log[-1]["status"] = "COMPLETED"
            except httpx.HTTPError as e:
                saga_log[-1]["status"] = "FAILED"
                saga_log[-1]["error"] = str(e)
                await self._publish_saga_event("SagaFailed", order_id, saga_log)
                return {"success": False, "saga_log": saga_log}

            # ── Step 2: 在庫を引き当て ──────────────────
            saga_log.append(
                {
                    "step": 2,
                    "action": "ReserveInventory",
                    "status": "EXECUTING",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

            try:
                resp = await client.post(
                    f"{self.inventory_url}/commands/inventory/{product_id}/reserve",
                    json={
                        "order_id": str(order_id),
                        "quantity": quantity,
                    },
                )
                resp.raise_for_status()
                saga_log[-1]["status"] = "COMPLETED"
            except httpx.HTTPStatusError as e:
                # 在庫不足 → 補償トランザクション実行
                saga_log[-1]["status"] = "FAILED"
                saga_log[-1]["error"] = e.response.text

                # ── Step 3 (補償): 注文をキャンセル ─────
                saga_log.append(
                    {
                        "step": 3,
                        "action": "CancelOrder (COMPENSATING)",
                        "status": "EXECUTING",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )

                try:
                    await client.post(
                        f"{self.order_url}/commands/orders/{order_id}/cancel",
                        json={"reason": "Inventory reservation failed"},
                    )
                    saga_log[-1]["status"] = "COMPLETED"
                except httpx.HTTPError:
                    saga_log[-1]["status"] = "FAILED"

                await self._publish_saga_event("SagaCompensated", order_id, saga_log)
                return {"success": False, "saga_log": saga_log}
            except httpx.HTTPError as e:
                saga_log[-1]["status"] = "FAILED"
                saga_log[-1]["error"] = str(e)

                saga_log.append(
                    {
                        "step": 3,
                        "action": "CancelOrder (COMPENSATING)",
                        "status": "EXECUTING",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )
                try:
                    await client.post(
                        f"{self.order_url}/commands/orders/{order_id}/cancel",
                        json={"reason": f"Inventory service error: {e}"},
                    )
                    saga_log[-1]["status"] = "COMPLETED"
                except httpx.HTTPError:
                    saga_log[-1]["status"] = "FAILED"

                await self._publish_saga_event("SagaCompensated", order_id, saga_log)
                return {"success": False, "saga_log": saga_log}

            # ── Step 3: 注文を確定 ──────────────────────
            saga_log.append(
                {
                    "step": 3,
                    "action": "ConfirmOrder",
                    "status": "EXECUTING",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

            try:
                await client.post(
                    f"{self.order_url}/commands/orders/{order_id}/confirm",
                )
                saga_log[-1]["status"] = "COMPLETED"
            except httpx.HTTPError as e:
                saga_log[-1]["status"] = "FAILED"
                saga_log[-1]["error"] = str(e)

            await self._publish_saga_event("SagaCompleted", order_id, saga_log)
            return {"success": True, "saga_log": saga_log}

    async def _publish_saga_event(
        self,
        event_type: str,
        order_id: UUID,
        saga_log: list[dict],
    ) -> None:
        """Saga のイベントを Redis に発行する。"""
        await self.redis.publish(
            "saga_events",
            json.dumps(
                {
                    "event_type": event_type,
                    "order_id": str(order_id),
                    "saga_log": saga_log,
                },
                default=str,
            ),
        )

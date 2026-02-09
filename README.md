# EC Microservice Demo — Saga / CQRS & Event Sourcing / BFF

マイクロサービスの主要パターンを学ぶための教育用プロジェクトです。
EC（電子商取引）の「販売と在庫引き当て」をシンプルに実装しています。

## アーキテクチャ全体図

```
┌──────────────────┐
│   React Frontend │ :3000
│   (商品一覧/注文) │
└────────┬─────────┘
         │ HTTP
┌────────▼─────────┐
│       BFF        │ :8000   ← Backend for Frontend
│  (API Gateway)   │           フロントエンド専用の集約API
└────────┬─────────┘
         │
┌────────▼─────────┐
│  Saga Orchestrator│ :8003  ← 分散トランザクション制御
│  (オーケストレータ)│
└───┬──────────┬───┘
    │          │
┌───▼───┐  ┌──▼────────┐
│ Order │  │ Inventory  │
│Service│  │  Service   │     ← 各サービスが CQRS + Event Sourcing
│ :8001 │  │   :8002    │
└───┬───┘  └──┬─────────┘
    │         │
┌───▼───┐  ┌──▼─────────┐
│Order  │  │Inventory   │    ← Database per Service
│  DB   │  │    DB      │
│:5432  │  │  :5433     │
└───────┘  └────────────┘
         ┌──────┐
         │Redis │ :6379       ← イベント通知 (Pub/Sub)
         └──────┘
```

## 学べるパターン

### 1. Saga パターン（オーケストレーション型）

分散トランザクションを管理するパターン。マイクロサービスでは
サービスをまたぐトランザクション（2PC）が使えないため、
Saga で整合性を保つ。

**実装箇所**: `services/saga/app/orchestrator.py`

```
正常フロー:
  Step 1: CreateOrder        → Order Service
  Step 2: ReserveInventory   → Inventory Service
  Step 3: ConfirmOrder       → Order Service

失敗フロー (在庫不足):
  Step 1: CreateOrder        → Order Service       ✓
  Step 2: ReserveInventory   → Inventory Service   ✗ (在庫不足)
  Step 3: CancelOrder        → Order Service       ← 補償トランザクション
```

### 2. CQRS (Command Query Responsibility Segregation)

書き込み（Command）と読み取り（Query）を分離するパターン。

**実装箇所**:
- Command 側: `services/order/app/commands.py`, `services/inventory/app/commands.py`
- Query 側: `services/order/app/queries.py`, `services/inventory/app/queries.py`

```
Command (Write):
  POST /commands/orders         → イベントストアに書き込み → リードモデル更新

Query (Read):
  GET  /queries/orders          → リードモデルから読み取り（高速）
```

### 3. Event Sourcing（イベントソーシング）

状態を直接保存するのではなく、発生した「イベント（事実）」を記録する。
現在の状態はイベントをリプレイして再構築する。

**実装箇所**:
- イベントストア: `services/order/app/event_store.py`
- 集約の再構築: `services/order/app/aggregate.py`
- イベント定義: `services/order/app/events.py`

```
従来の方法:  orders テーブルに status = 'CONFIRMED' を UPDATE
Event Sourcing: イベントストアに以下を INSERT (不変)
  v1: OrderCreated   { customer: "山田", product: "ノートPC", qty: 1 }
  v2: OrderConfirmed { order_id: "abc-123" }
```

### 4. BFF (Backend for Frontend)

フロントエンド専用の API ゲートウェイ。複数サービスを集約し、
フロントエンドが使いやすい API を提供する。

**実装箇所**: `services/bff/app/main.py`

```
BFF の役割:
  - 商品情報取得 + 合計金額計算 → 1つの API で返す
  - Saga の存在をフロントエンドから隠蔽
  - ダッシュボード API で複数サービスのデータを集約
```

## 起動方法

### 前提条件

- Docker Desktop がインストールされていること

### 起動

```bash
docker compose up --build
```

### アクセス

| サービス | URL | 説明 |
|---------|-----|------|
| React Frontend | http://localhost:3000 | UI |
| BFF | http://localhost:8000 | フロントエンド用API |
| Order Service | http://localhost:8001 | 注文サービス |
| Inventory Service | http://localhost:8002 | 在庫サービス |
| Saga Service | http://localhost:8003 | Saga オーケストレータ |

### 動作確認の手順

1. http://localhost:3000 にアクセス
2. 商品一覧から商品を選択
3. 名前と数量を入力して「注文する」をクリック
4. **成功ケース**: 在庫十分 → Saga 成功 → 注文 CONFIRMED
5. **失敗ケース**: 在庫以上の数量を指定 → Saga 失敗 → 補償トランザクション → 注文 CANCELLED
6. 「イベントログ」タブで Event Sourcing の記録を確認

### 停止

```bash
docker compose down
# データも削除する場合
docker compose down -v
```

## ディレクトリ構成

```
.
├── docker-compose.yml          # 全サービス定義
├── db/init/
│   ├── order.sql               # Order DB 初期化 (イベントストア + リードモデル)
│   └── inventory.sql           # Inventory DB 初期化 + サンプルデータ
├── services/
│   ├── order/                  # 注文サービス (CQRS + Event Sourcing)
│   │   └── app/
│   │       ├── main.py         # FastAPI エンドポイント
│   │       ├── commands.py     # CQRS Write 側
│   │       ├── queries.py      # CQRS Read 側
│   │       ├── event_store.py  # イベントストア
│   │       ├── aggregate.py    # 集約 (イベントリプレイ)
│   │       └── events.py       # イベント定義
│   ├── inventory/              # 在庫サービス (CQRS + Event Sourcing)
│   │   └── app/
│   │       ├── main.py
│   │       ├── commands.py
│   │       ├── queries.py
│   │       ├── event_store.py
│   │       ├── aggregate.py
│   │       └── events.py
│   ├── saga/                   # Saga オーケストレータ
│   │   └── app/
│   │       ├── main.py
│   │       └── orchestrator.py # Saga ロジック
│   └── bff/                    # BFF (Backend for Frontend)
│       └── app/
│           └── main.py
└── frontend/                   # React フロントエンド
    └── src/
        ├── App.js
        └── components/
            ├── ProductList.js
            ├── OrderForm.js
            ├── OrderHistory.js
            ├── EventLog.js
            └── SagaLog.js
```

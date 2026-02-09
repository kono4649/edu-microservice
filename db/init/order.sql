-- ============================================
-- Order Service: Event Store + Read Model
-- ============================================

-- イベントストア: すべてのイベントを不変のログとして保存
-- Event Sourcing の核心 — 状態ではなくイベントを記録する
CREATE TABLE event_store (
    id            BIGSERIAL PRIMARY KEY,
    aggregate_id  UUID NOT NULL,
    aggregate_type VARCHAR(50) NOT NULL,
    event_type    VARCHAR(100) NOT NULL,
    event_data    JSONB NOT NULL,
    version       INT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (aggregate_id, version)  -- 楽観的ロック
);

CREATE INDEX idx_event_store_aggregate ON event_store (aggregate_id, version);

-- CQRS Read Model: クエリ用に最適化されたビュー
-- コマンド側(イベントストア)とは分離された読み取り専用モデル
CREATE TABLE orders_read_model (
    id          UUID PRIMARY KEY,
    customer_name VARCHAR(200) NOT NULL,
    product_id  UUID NOT NULL,
    product_name VARCHAR(200) NOT NULL,
    quantity    INT NOT NULL,
    total_price NUMERIC(10, 2) NOT NULL,
    status      VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

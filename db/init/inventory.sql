-- ============================================
-- Inventory Service: Event Store + Read Model
-- ============================================

-- イベントストア
CREATE TABLE event_store (
    id            BIGSERIAL PRIMARY KEY,
    aggregate_id  UUID NOT NULL,
    aggregate_type VARCHAR(50) NOT NULL,
    event_type    VARCHAR(100) NOT NULL,
    event_data    JSONB NOT NULL,
    version       INT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (aggregate_id, version)
);

CREATE INDEX idx_event_store_aggregate ON event_store (aggregate_id, version);

-- CQRS Read Model: 在庫の現在状態
CREATE TABLE inventory_read_model (
    id           UUID PRIMARY KEY,
    product_name VARCHAR(200) NOT NULL,
    quantity     INT NOT NULL DEFAULT 0,
    reserved     INT NOT NULL DEFAULT 0,
    available    INT GENERATED ALWAYS AS (quantity - reserved) STORED,
    price        NUMERIC(10, 2) NOT NULL DEFAULT 0,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 初期在庫データ (学習用サンプル)
INSERT INTO inventory_read_model (id, product_name, quantity, reserved, price) VALUES
    ('a1111111-1111-1111-1111-111111111111', 'ノートPC', 50, 0, 120000),
    ('b2222222-2222-2222-2222-222222222222', 'ワイヤレスマウス', 200, 0, 3500),
    ('c3333333-3333-3333-3333-333333333333', 'USBキーボード', 150, 0, 5800),
    ('d4444444-4444-4444-4444-444444444444', '4Kモニター', 30, 0, 65000),
    ('e5555555-5555-5555-5555-555555555555', 'ヘッドセット', 100, 0, 8900);

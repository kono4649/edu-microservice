-- ============================================
-- Marketing Service: マーケティング最適化リードモデル
-- ============================================
-- このサービスは独自のイベントストアを持たない。
-- Order Service が Redis Pub/Sub で発行する order_events を購読し、
-- マーケティング分析に最適化されたリードモデルを構築する。
-- → CQRS の本質的な利点: 同じイベントから目的別の Read Model を構築できる

-- ── 注文スナップショット ─────────────────────────
-- 各注文の非正規化コピー。集計の元データとして利用。
CREATE TABLE marketing_order_snapshot (
    order_id      UUID PRIMARY KEY,
    customer_name VARCHAR(200) NOT NULL,
    product_id    UUID NOT NULL,
    product_name  VARCHAR(200) NOT NULL,
    quantity      INT NOT NULL,
    total_price   NUMERIC(10, 2) NOT NULL,
    status        VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    order_date    DATE NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_order_snapshot_customer ON marketing_order_snapshot (customer_name);
CREATE INDEX idx_order_snapshot_product ON marketing_order_snapshot (product_id);
CREATE INDEX idx_order_snapshot_date ON marketing_order_snapshot (order_date);

-- ── 顧客サマリー ────────────────────────────────
-- 顧客セグメンテーション、LTV 分析、リピート購入追跡に利用
CREATE TABLE customer_summary (
    customer_name     VARCHAR(200) PRIMARY KEY,
    total_orders      INT NOT NULL DEFAULT 0,
    confirmed_orders  INT NOT NULL DEFAULT 0,
    cancelled_orders  INT NOT NULL DEFAULT 0,
    total_revenue     NUMERIC(12, 2) NOT NULL DEFAULT 0,
    avg_order_value   NUMERIC(10, 2) NOT NULL DEFAULT 0,
    first_order_at    TIMESTAMPTZ,
    last_order_at     TIMESTAMPTZ,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── 商品人気度 ──────────────────────────────────
-- ベストセラー分析、売上貢献度、需要予測に利用
CREATE TABLE product_popularity (
    product_id            UUID PRIMARY KEY,
    product_name          VARCHAR(200) NOT NULL,
    total_units_ordered   INT NOT NULL DEFAULT 0,
    confirmed_units       INT NOT NULL DEFAULT 0,
    total_order_count     INT NOT NULL DEFAULT 0,
    confirmed_order_count INT NOT NULL DEFAULT 0,
    total_revenue         NUMERIC(12, 2) NOT NULL DEFAULT 0,
    unique_customers      INT NOT NULL DEFAULT 0,
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── 商品×顧客マッピング ─────────────────────────
-- ユニーク顧客数を正確にカウントするための補助テーブル
CREATE TABLE product_customer_map (
    product_id    UUID NOT NULL,
    customer_name VARCHAR(200) NOT NULL,
    PRIMARY KEY (product_id, customer_name)
);

-- ── 日別売上サマリー ────────────────────────────
-- トレンド分析、日次 KPI ダッシュボード、時系列レポートに利用
CREATE TABLE daily_sales_summary (
    sale_date         DATE PRIMARY KEY,
    total_orders      INT NOT NULL DEFAULT 0,
    confirmed_orders  INT NOT NULL DEFAULT 0,
    cancelled_orders  INT NOT NULL DEFAULT 0,
    total_revenue     NUMERIC(12, 2) NOT NULL DEFAULT 0,
    avg_order_value   NUMERIC(10, 2) NOT NULL DEFAULT 0,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

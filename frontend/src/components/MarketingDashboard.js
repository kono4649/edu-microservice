import React, { useState, useEffect, useCallback } from 'react';

const BFF_URL = process.env.REACT_APP_BFF_URL || 'http://localhost:8000';

/**
 * マーケティングダッシュボード
 *
 * Marketing Service のリードモデルから集約データを表示。
 * Order Service が発行する order_events を Redis Pub/Sub で購読し、
 * マーケティング分析に最適化されたビューを構築している。
 *
 * → CQRS の利点: 同じイベントから目的別のリードモデルを構築できる
 */
export default function MarketingDashboard() {
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchOverview = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${BFF_URL}/api/marketing/overview`);
      setOverview(await res.json());
    } catch (err) {
      console.error('Failed to fetch marketing data', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOverview();
  }, [fetchOverview]);

  if (loading) return <p style={styles.empty}>読み込み中...</p>;
  if (!overview) return <p style={styles.empty}>データがありません</p>;

  const { summary, top_customers, top_products, recent_daily_sales } = overview;

  return (
    <div>
      {/* KPI サマリーカード */}
      <div style={styles.kpiRow}>
        <div style={styles.kpiCard}>
          <div style={styles.kpiValue}>
            {Number(summary.total_revenue).toLocaleString()}円
          </div>
          <div style={styles.kpiLabel}>総売上</div>
        </div>
        <div style={styles.kpiCard}>
          <div style={styles.kpiValue}>{summary.total_customers}</div>
          <div style={styles.kpiLabel}>顧客数</div>
        </div>
        <div style={styles.kpiCard}>
          <div style={styles.kpiValue}>{summary.total_product_types}</div>
          <div style={styles.kpiLabel}>商品種類</div>
        </div>
      </div>

      {/* トップ顧客 */}
      <h3 style={styles.subTitle}>トップ顧客 (売上順)</h3>
      {top_customers.length === 0 ? (
        <p style={styles.empty}>データなし</p>
      ) : (
        <table style={styles.table}>
          <thead>
            <tr style={styles.headerRow}>
              <th style={styles.th}>顧客名</th>
              <th style={styles.th}>注文数</th>
              <th style={styles.th}>確定</th>
              <th style={styles.th}>キャンセル</th>
              <th style={styles.th}>総売上</th>
              <th style={styles.th}>平均注文額</th>
            </tr>
          </thead>
          <tbody>
            {top_customers.map(c => (
              <tr key={c.customer_name} style={styles.row}>
                <td style={styles.td}>{c.customer_name}</td>
                <td style={styles.td}>{c.total_orders}</td>
                <td style={styles.td}>{c.confirmed_orders}</td>
                <td style={styles.td}>{c.cancelled_orders}</td>
                <td style={styles.td}>{Number(c.total_revenue).toLocaleString()}円</td>
                <td style={styles.td}>{Number(c.avg_order_value).toLocaleString()}円</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* 人気商品 */}
      <h3 style={styles.subTitle}>人気商品 (売上順)</h3>
      {top_products.length === 0 ? (
        <p style={styles.empty}>データなし</p>
      ) : (
        <table style={styles.table}>
          <thead>
            <tr style={styles.headerRow}>
              <th style={styles.th}>商品名</th>
              <th style={styles.th}>注文数</th>
              <th style={styles.th}>販売個数</th>
              <th style={styles.th}>売上</th>
              <th style={styles.th}>ユニーク顧客</th>
            </tr>
          </thead>
          <tbody>
            {top_products.map(p => (
              <tr key={p.product_id} style={styles.row}>
                <td style={styles.td}>{p.product_name}</td>
                <td style={styles.td}>{p.total_order_count}</td>
                <td style={styles.td}>{p.total_units_ordered}</td>
                <td style={styles.td}>{Number(p.total_revenue).toLocaleString()}円</td>
                <td style={styles.td}>{p.unique_customers}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* 日別売上 */}
      <h3 style={styles.subTitle}>日別売上 (直近7日)</h3>
      {recent_daily_sales.length === 0 ? (
        <p style={styles.empty}>データなし</p>
      ) : (
        <table style={styles.table}>
          <thead>
            <tr style={styles.headerRow}>
              <th style={styles.th}>日付</th>
              <th style={styles.th}>注文数</th>
              <th style={styles.th}>確定</th>
              <th style={styles.th}>キャンセル</th>
              <th style={styles.th}>売上</th>
              <th style={styles.th}>平均注文額</th>
            </tr>
          </thead>
          <tbody>
            {recent_daily_sales.map(d => (
              <tr key={d.sale_date} style={styles.row}>
                <td style={styles.td}>{d.sale_date}</td>
                <td style={styles.td}>{d.total_orders}</td>
                <td style={styles.td}>{d.confirmed_orders}</td>
                <td style={styles.td}>{d.cancelled_orders}</td>
                <td style={styles.td}>{Number(d.total_revenue).toLocaleString()}円</td>
                <td style={styles.td}>{Number(d.avg_order_value).toLocaleString()}円</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <button onClick={fetchOverview} style={styles.refreshBtn}>更新</button>
    </div>
  );
}

const styles = {
  kpiRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: 16,
    marginBottom: 24,
  },
  kpiCard: {
    background: '#f8f9fa',
    borderRadius: 8,
    padding: '20px 16px',
    textAlign: 'center',
    border: '1px solid #e8eaf6',
  },
  kpiValue: {
    fontSize: 28,
    fontWeight: 700,
    color: '#16213e',
    marginBottom: 4,
  },
  kpiLabel: {
    fontSize: 12,
    color: '#888',
    fontWeight: 600,
  },
  subTitle: {
    fontSize: 15,
    color: '#16213e',
    marginTop: 24,
    marginBottom: 12,
    borderBottom: '1px solid #e8eaf6',
    paddingBottom: 6,
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: 13,
  },
  headerRow: { background: '#f5f5f5' },
  th: {
    textAlign: 'left',
    padding: '10px 8px',
    borderBottom: '2px solid #e0e0e0',
    fontSize: 12,
    color: '#555',
    fontWeight: 700,
  },
  row: { borderBottom: '1px solid #f0f0f0' },
  td: { padding: '10px 8px' },
  refreshBtn: {
    marginTop: 20,
    padding: '8px 20px',
    border: 'none',
    borderRadius: 6,
    background: '#1a1a2e',
    color: '#fff',
    cursor: 'pointer',
    fontSize: 13,
    fontWeight: 600,
  },
  empty: { color: '#999', textAlign: 'center', padding: 40 },
};

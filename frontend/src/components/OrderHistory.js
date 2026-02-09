import React from 'react';

/**
 * 注文履歴コンポーネント
 *
 * Order Service のリードモデル(Read Model)から取得した注文一覧を表示。
 * CQRS パターンにより、クエリは非正規化されたリードモデルから高速に取得。
 */
export default function OrderHistory({ orders }) {
  if (!orders.length) {
    return <p style={styles.empty}>まだ注文がありません</p>;
  }

  return (
    <table style={styles.table}>
      <thead>
        <tr style={styles.headerRow}>
          <th style={styles.th}>注文ID</th>
          <th style={styles.th}>顧客名</th>
          <th style={styles.th}>商品</th>
          <th style={styles.th}>数量</th>
          <th style={styles.th}>合計</th>
          <th style={styles.th}>ステータス</th>
          <th style={styles.th}>作成日時</th>
        </tr>
      </thead>
      <tbody>
        {orders.map(o => (
          <tr key={o.id} style={styles.row}>
            <td style={styles.td}>
              <code style={styles.code}>{o.id.substring(0, 8)}...</code>
            </td>
            <td style={styles.td}>{o.customer_name}</td>
            <td style={styles.td}>{o.product_name}</td>
            <td style={styles.td}>{o.quantity}</td>
            <td style={styles.td}>{Number(o.total_price).toLocaleString()}円</td>
            <td style={styles.td}>
              <span style={{
                ...styles.badge,
                background: statusColor(o.status),
              }}>
                {statusLabel(o.status)}
              </span>
            </td>
            <td style={styles.td}>
              {new Date(o.created_at).toLocaleString('ja-JP')}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function statusColor(s) {
  switch (s) {
    case 'CONFIRMED': return '#2e7d32';
    case 'CANCELLED': return '#c62828';
    default: return '#f9a825';
  }
}

function statusLabel(s) {
  switch (s) {
    case 'CONFIRMED': return '確定';
    case 'CANCELLED': return 'キャンセル';
    default: return '処理中';
  }
}

const styles = {
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
  code: {
    background: '#f5f5f5',
    padding: '2px 6px',
    borderRadius: 4,
    fontSize: 11,
    fontFamily: 'monospace',
  },
  badge: {
    padding: '3px 10px',
    borderRadius: 12,
    color: '#fff',
    fontSize: 11,
    fontWeight: 700,
  },
  empty: { color: '#999', textAlign: 'center', padding: 40 },
};

import React from 'react';

/**
 * 商品一覧コンポーネント
 *
 * Inventory Service のリードモデル(Read Model)から取得したデータを表示。
 * CQRS パターンにより、読み取り用に最適化されたビューを利用している。
 */
export default function ProductList({ products, selectedId, onSelect }) {
  if (!products.length) {
    return <p style={styles.empty}>商品を読み込み中...</p>;
  }

  return (
    <div style={styles.list}>
      {products.map(p => (
        <div
          key={p.id}
          style={{
            ...styles.card,
            ...(selectedId === p.id ? styles.cardSelected : {}),
          }}
          onClick={() => onSelect(p)}
        >
          <div style={styles.cardHeader}>
            <span style={styles.name}>{p.product_name}</span>
            <span style={styles.price}>{Number(p.price).toLocaleString()}円</span>
          </div>
          <div style={styles.stock}>
            <span>総在庫: {p.quantity}</span>
            <span>予約済: {p.reserved}</span>
            <span style={{
              fontWeight: 700,
              color: p.available > 0 ? '#2e7d32' : '#c62828',
            }}>
              購入可能: {p.available}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}

const styles = {
  list: { display: 'flex', flexDirection: 'column', gap: 8 },
  card: {
    padding: '12px 16px',
    border: '2px solid #e0e0e0',
    borderRadius: 8,
    cursor: 'pointer',
    transition: 'all 0.15s',
  },
  cardSelected: {
    borderColor: '#1565c0',
    background: '#e3f2fd',
  },
  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  name: { fontWeight: 700, fontSize: 15 },
  price: { fontSize: 15, color: '#e65100', fontWeight: 600 },
  stock: {
    display: 'flex',
    gap: 16,
    fontSize: 13,
    color: '#666',
  },
  empty: { color: '#999', textAlign: 'center' },
};

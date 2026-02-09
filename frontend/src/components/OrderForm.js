import React, { useState } from 'react';

/**
 * 注文フォームコンポーネント
 *
 * 注文リクエストは BFF に送信され、BFF が Saga Orchestrator に委譲する。
 * フロントエンドは Saga の存在を知らない — BFF パターンで隠蔽されている。
 */
export default function OrderForm({ product, onSubmit, loading }) {
  const [customerName, setCustomerName] = useState('');
  const [quantity, setQuantity] = useState(1);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!product || !customerName.trim()) return;
    onSubmit(customerName.trim(), quantity);
  };

  if (!product) {
    return (
      <div style={styles.placeholder}>
        左の商品一覧から商品を選択してください
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} style={styles.form}>
      <div style={styles.selected}>
        <strong>{product.product_name}</strong>
        <span style={styles.price}>{Number(product.price).toLocaleString()}円</span>
      </div>

      <label style={styles.label}>
        お名前
        <input
          type="text"
          value={customerName}
          onChange={e => setCustomerName(e.target.value)}
          placeholder="山田 太郎"
          style={styles.input}
          required
        />
      </label>

      <label style={styles.label}>
        数量 (在庫: {product.available})
        <input
          type="number"
          min={1}
          max={999}
          value={quantity}
          onChange={e => setQuantity(parseInt(e.target.value) || 1)}
          style={styles.input}
          required
        />
      </label>

      <div style={styles.total}>
        合計: <strong>{(product.price * quantity).toLocaleString()}円</strong>
      </div>

      <button
        type="submit"
        disabled={loading}
        style={{
          ...styles.button,
          ...(loading ? styles.buttonDisabled : {}),
        }}
      >
        {loading ? 'Saga 実行中...' : '注文する (Saga 開始)'}
      </button>

      <p style={styles.hint}>
        BFF → Saga Orchestrator → Order Service + Inventory Service
      </p>
    </form>
  );
}

const styles = {
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },
  placeholder: {
    textAlign: 'center',
    color: '#999',
    padding: 40,
    border: '2px dashed #ddd',
    borderRadius: 8,
  },
  selected: {
    display: 'flex',
    justifyContent: 'space-between',
    background: '#e3f2fd',
    padding: '10px 14px',
    borderRadius: 6,
    fontSize: 15,
  },
  price: { color: '#e65100', fontWeight: 600 },
  label: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
    fontSize: 13,
    fontWeight: 600,
    color: '#444',
  },
  input: {
    padding: '8px 12px',
    border: '1px solid #ccc',
    borderRadius: 6,
    fontSize: 14,
    outline: 'none',
  },
  total: {
    fontSize: 16,
    textAlign: 'right',
    color: '#1a1a2e',
  },
  button: {
    padding: '12px',
    border: 'none',
    borderRadius: 8,
    background: '#1565c0',
    color: '#fff',
    fontSize: 15,
    fontWeight: 700,
    cursor: 'pointer',
    transition: 'background 0.2s',
  },
  buttonDisabled: {
    background: '#90a4ae',
    cursor: 'not-allowed',
  },
  hint: {
    fontSize: 11,
    color: '#aaa',
    textAlign: 'center',
    margin: 0,
  },
};

import React, { useState, useEffect, useCallback } from 'react';
import ProductList from './components/ProductList';
import OrderForm from './components/OrderForm';
import OrderHistory from './components/OrderHistory';
import EventLog from './components/EventLog';
import MarketingDashboard from './components/MarketingDashboard';
import SagaLog from './components/SagaLog';

const BFF_URL = process.env.REACT_APP_BFF_URL || 'http://localhost:8000';

/**
 * EC マイクロサービス デモアプリ
 *
 * このフロントエンドは BFF (Backend for Frontend) のみと通信する。
 * Order Service, Inventory Service, Saga の存在を直接知らない。
 * → BFF パターンにより、バックエンドの複雑さが隠蔽されている。
 */
export default function App() {
  const [products, setProducts] = useState([]);
  const [orders, setOrders] = useState([]);
  const [events, setEvents] = useState([]);
  const [sagaLog, setSagaLog] = useState(null);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('products');

  const fetchProducts = useCallback(async () => {
    const res = await fetch(`${BFF_URL}/api/products`);
    setProducts(await res.json());
  }, []);

  const fetchOrders = useCallback(async () => {
    const res = await fetch(`${BFF_URL}/api/orders`);
    setOrders(await res.json());
  }, []);

  const fetchEvents = useCallback(async () => {
    const res = await fetch(`${BFF_URL}/api/events`);
    setEvents(await res.json());
  }, []);

  useEffect(() => {
    fetchProducts();
    fetchOrders();
  }, [fetchProducts, fetchOrders]);

  const handlePlaceOrder = async (customerName, quantity) => {
    if (!selectedProduct) return;
    setLoading(true);
    setSagaLog(null);

    try {
      const res = await fetch(`${BFF_URL}/api/orders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer_name: customerName,
          product_id: selectedProduct.id,
          quantity: quantity,
        }),
      });
      const data = await res.json();
      setSagaLog(data);

      // 注文後にデータを再取得
      await Promise.all([fetchProducts(), fetchOrders(), fetchEvents()]);
    } catch (err) {
      alert('Error: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const tabs = [
    { id: 'products', label: '商品一覧' },
    { id: 'orders', label: '注文履歴' },
    { id: 'marketing', label: 'マーケティング' },
    { id: 'events', label: 'イベントログ' },
  ];

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <h1 style={styles.title}>EC Microservice Demo</h1>
        <p style={styles.subtitle}>Saga / CQRS & Event Sourcing / BFF パターン学習</p>
      </header>

      <div style={styles.architecture}>
        <pre style={styles.archPre}>{`
  [React Frontend]
        |
     [BFF] ← Backend for Frontend: フロントエンド専用 API Gateway
        |
  [Saga Orchestrator] ← 分散トランザクションを制御
       / \\
[Order Svc]  [Inventory Svc] ← 各サービスが CQRS + Event Sourcing
     |    \\        |
 [Order DB] \\  [Inventory DB] ← Database per Service
             \\
        [Marketing Svc] ← Redis Pub/Sub で order_events を購読
              |
         [Marketing DB] ← マーケティング最適化リードモデル
        `}</pre>
      </div>

      <nav style={styles.nav}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            style={{
              ...styles.tabButton,
              ...(activeTab === tab.id ? styles.tabButtonActive : {}),
            }}
            onClick={() => {
              setActiveTab(tab.id);
              if (tab.id === 'events') fetchEvents();
              if (tab.id === 'orders') fetchOrders();
            }}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <main style={styles.main}>
        {activeTab === 'products' && (
          <div style={styles.twoCol}>
            <div style={styles.col}>
              <h2 style={styles.sectionTitle}>商品一覧 (Inventory Service Read Model)</h2>
              <ProductList
                products={products}
                selectedId={selectedProduct?.id}
                onSelect={setSelectedProduct}
              />
            </div>
            <div style={styles.col}>
              <h2 style={styles.sectionTitle}>注文する (BFF → Saga)</h2>
              <OrderForm
                product={selectedProduct}
                onSubmit={handlePlaceOrder}
                loading={loading}
              />
              {sagaLog && <SagaLog data={sagaLog} />}
            </div>
          </div>
        )}

        {activeTab === 'orders' && (
          <div>
            <h2 style={styles.sectionTitle}>注文履歴 (Order Service Read Model)</h2>
            <OrderHistory orders={orders} />
          </div>
        )}

        {activeTab === 'marketing' && (
          <div>
            <h2 style={styles.sectionTitle}>マーケティングダッシュボード (Marketing Service Read Model)</h2>
            <p style={styles.hint}>
              order_events を Redis Pub/Sub で購読し、マーケティング最適化されたリードモデルから表示。
              Order Service のリードモデルとは独立した別の投影(Projection)。
            </p>
            <MarketingDashboard />
          </div>
        )}

        {activeTab === 'events' && (
          <div>
            <h2 style={styles.sectionTitle}>イベントストア (Event Sourcing)</h2>
            <p style={styles.hint}>
              全サービスのイベントを時系列で表示。状態ではなくイベント(事実)を記録している。
            </p>
            <EventLog events={events} />
          </div>
        )}
      </main>
    </div>
  );
}

const styles = {
  container: {
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    maxWidth: 1100,
    margin: '0 auto',
    padding: '20px',
    color: '#1a1a2e',
    background: '#f0f2f5',
    minHeight: '100vh',
  },
  header: {
    textAlign: 'center',
    marginBottom: 16,
  },
  title: {
    fontSize: 28,
    margin: '0 0 4px 0',
    color: '#16213e',
  },
  subtitle: {
    fontSize: 14,
    color: '#666',
    margin: 0,
  },
  architecture: {
    background: '#1a1a2e',
    borderRadius: 8,
    padding: '4px 16px',
    marginBottom: 20,
    overflowX: 'auto',
  },
  archPre: {
    color: '#4fc3f7',
    fontSize: 12,
    lineHeight: 1.4,
    margin: 0,
  },
  nav: {
    display: 'flex',
    gap: 4,
    marginBottom: 20,
  },
  tabButton: {
    padding: '10px 24px',
    border: 'none',
    borderRadius: '8px 8px 0 0',
    background: '#ddd',
    cursor: 'pointer',
    fontSize: 14,
    fontWeight: 600,
    color: '#555',
    transition: 'all 0.2s',
  },
  tabButtonActive: {
    background: '#fff',
    color: '#1a1a2e',
    boxShadow: '0 -2px 4px rgba(0,0,0,0.05)',
  },
  main: {
    background: '#fff',
    borderRadius: '0 8px 8px 8px',
    padding: 24,
    boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
  },
  twoCol: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 24,
  },
  col: {},
  sectionTitle: {
    fontSize: 18,
    marginTop: 0,
    marginBottom: 16,
    color: '#16213e',
    borderBottom: '2px solid #e8eaf6',
    paddingBottom: 8,
  },
  hint: {
    fontSize: 13,
    color: '#888',
    marginBottom: 12,
  },
};

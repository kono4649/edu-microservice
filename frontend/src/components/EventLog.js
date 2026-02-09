import React from 'react';

/**
 * イベントログコンポーネント
 *
 * Event Sourcing の学習用ビュー。
 * 全サービスのイベントストアの中身を時系列で確認できる。
 * 「状態」ではなく「何が起きたか(イベント)」が記録されていることを体感する。
 */
export default function EventLog({ events }) {
  if (!events.length) {
    return <p style={styles.empty}>まだイベントがありません。注文を作成してみてください。</p>;
  }

  return (
    <div style={styles.list}>
      {events.map((e, i) => (
        <div key={i} style={styles.card}>
          <div style={styles.header}>
            <span style={{
              ...styles.badge,
              background: eventColor(e.event_type),
            }}>
              {e.event_type}
            </span>
            <span style={styles.service}>{e.service}</span>
            <span style={styles.time}>
              {e.created_at ? new Date(e.created_at).toLocaleString('ja-JP') : ''}
            </span>
          </div>
          <div style={styles.details}>
            <span style={styles.meta}>
              Aggregate: <code>{e.aggregate_id?.substring(0, 8)}...</code>
              {' | '}Version: {e.version}
            </span>
          </div>
          <pre style={styles.data}>
            {JSON.stringify(e.event_data, null, 2)}
          </pre>
        </div>
      ))}
    </div>
  );
}

function eventColor(type) {
  if (type.includes('Created')) return '#1565c0';
  if (type.includes('Confirmed') || type.includes('Reserved')) return '#2e7d32';
  if (type.includes('Cancelled') || type.includes('Failed')) return '#c62828';
  if (type.includes('Released')) return '#ef6c00';
  return '#666';
}

const styles = {
  list: { display: 'flex', flexDirection: 'column', gap: 8 },
  card: {
    border: '1px solid #e0e0e0',
    borderRadius: 8,
    padding: 12,
    background: '#fafafa',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    marginBottom: 6,
  },
  badge: {
    padding: '3px 10px',
    borderRadius: 12,
    color: '#fff',
    fontSize: 12,
    fontWeight: 700,
  },
  service: {
    fontSize: 11,
    color: '#888',
    fontStyle: 'italic',
  },
  time: {
    fontSize: 11,
    color: '#aaa',
    marginLeft: 'auto',
  },
  details: { marginBottom: 6 },
  meta: { fontSize: 11, color: '#888' },
  data: {
    background: '#263238',
    color: '#80cbc4',
    padding: 10,
    borderRadius: 6,
    fontSize: 11,
    overflow: 'auto',
    margin: 0,
  },
  empty: { color: '#999', textAlign: 'center', padding: 40 },
};

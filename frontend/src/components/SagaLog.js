import React from 'react';

/**
 * Saga ログコンポーネント
 *
 * Saga Orchestrator の実行結果を可視化する。
 * 各ステップの成功/失敗と、補償トランザクションの流れを確認できる。
 */
export default function SagaLog({ data }) {
  if (!data) return null;

  return (
    <div style={styles.container}>
      <h3 style={styles.title}>
        Saga 実行結果:
        <span style={{
          color: data.success ? '#2e7d32' : '#c62828',
          marginLeft: 8,
        }}>
          {data.success ? '成功' : '失敗 (補償実行済み)'}
        </span>
      </h3>

      <div style={styles.steps}>
        {data.saga_log?.map((step, i) => (
          <div key={i} style={styles.step}>
            <div style={styles.stepHeader}>
              <span style={styles.stepNum}>Step {step.step}</span>
              <span style={styles.action}>{step.action}</span>
              <span style={{
                ...styles.badge,
                background: step.status === 'COMPLETED' ? '#2e7d32' : '#c62828',
              }}>
                {step.status}
              </span>
            </div>
            {step.error && (
              <div style={styles.error}>Error: {step.error}</div>
            )}
            {i < (data.saga_log?.length || 0) - 1 && (
              <div style={styles.arrow}>
                {step.action.includes('COMPENSATING') ? '↑ 補償' : '↓'}
              </div>
            )}
          </div>
        ))}
      </div>

      {!data.success && (
        <p style={styles.explanation}>
          在庫不足により Saga が失敗。補償トランザクション(CancelOrder)が自動実行され、
          注文は CANCELLED 状態に戻されました。これが Saga パターンによる整合性の保証です。
        </p>
      )}
    </div>
  );
}

const styles = {
  container: {
    marginTop: 16,
    border: '2px solid #e0e0e0',
    borderRadius: 8,
    padding: 16,
    background: '#fafafa',
  },
  title: {
    fontSize: 15,
    margin: '0 0 12px 0',
    color: '#1a1a2e',
  },
  steps: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  step: {},
  stepHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '6px 0',
  },
  stepNum: {
    fontSize: 11,
    fontWeight: 700,
    color: '#888',
    minWidth: 50,
  },
  action: {
    fontSize: 13,
    fontWeight: 600,
    flex: 1,
  },
  badge: {
    padding: '2px 8px',
    borderRadius: 10,
    color: '#fff',
    fontSize: 10,
    fontWeight: 700,
  },
  arrow: {
    textAlign: 'center',
    color: '#999',
    fontSize: 12,
    padding: '2px 0',
  },
  error: {
    fontSize: 11,
    color: '#c62828',
    padding: '2px 0 2px 58px',
    fontFamily: 'monospace',
  },
  explanation: {
    marginTop: 12,
    padding: '10px 12px',
    background: '#fff3e0',
    borderRadius: 6,
    fontSize: 12,
    color: '#e65100',
    lineHeight: 1.5,
  },
};

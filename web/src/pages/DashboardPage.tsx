import { useCallback, useEffect, useState } from 'react'
import { getDashboard } from '../api'
import type { DashboardData } from '../types'

const money = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' })
const number = new Intl.NumberFormat('en-US')
const percent = (value: number) => `${(value * 100).toFixed(1)}%`

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try {
      setError('')
      setData(await getDashboard())
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to load dashboard')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
    const timer = window.setInterval(() => void load(), 15_000)
    return () => window.clearInterval(timer)
  }, [load])

  return (
    <section className="dashboard-page page-width">
      <div className="page-title-row">
        <div>
          <div className="eyebrow"><i /> Operations center</div>
          <h1>Fraud overview</h1>
          <p>Live decisions from the CardShield scoring pipeline.</p>
        </div>
        <button className="refresh-button" onClick={() => void load()} disabled={loading}>
          <span className={loading ? 'spinning' : ''}>↻</span> Refresh
        </button>
      </div>

      {error && (
        <div className="error-banner">
          <strong>Dashboard data is unavailable.</strong>
          <span>{error}. Make sure Cassandra is running and migrations are applied.</span>
        </div>
      )}

      <div className="metric-grid">
        <Metric label="Transactions analyzed" value={number.format(data?.metrics.total_transactions ?? 0)} trend="Live sample" />
        <Metric label="Fraud detected" value={number.format(data?.metrics.fraud_transactions ?? 0)} trend="Model decisions" danger />
        <Metric label="Fraud rate" value={percent(data?.metrics.fraud_rate ?? 0)} trend="Across recent activity" />
        <Metric label="Amount at risk" value={money.format(data?.metrics.amount_at_risk ?? 0)} trend="Flagged transaction value" danger />
      </div>

      <div className="dashboard-grid">
        <article className="panel risk-panel">
          <div className="panel-heading">
            <div><span>Detection health</span><h2>Risk distribution</h2></div>
            <small>Recent window</small>
          </div>
          <div className="risk-body">
            <div
              className="dashboard-ring"
              style={{ '--risk': `${(data?.metrics.fraud_rate ?? 0) * 360}deg` } as React.CSSProperties}
            >
              <div><strong>{percent(data?.metrics.fraud_rate ?? 0)}</strong><span>flagged</span></div>
            </div>
            <div className="risk-legend">
              <div><i className="safe" /><span>Legitimate</span><strong>{number.format((data?.metrics.total_transactions ?? 0) - (data?.metrics.fraud_transactions ?? 0))}</strong></div>
              <div><i className="fraud" /><span>Fraud</span><strong>{number.format(data?.metrics.fraud_transactions ?? 0)}</strong></div>
              <div><i className="neutral" /><span>Avg. risk score</span><strong>{percent(data?.metrics.average_probability ?? 0)}</strong></div>
            </div>
          </div>
        </article>

        <article className="panel category-panel">
          <div className="panel-heading">
            <div><span>Signal concentration</span><h2>Top categories</h2></div>
          </div>
          <div className="bar-list">
            {(data?.category_risk ?? []).length === 0 && <p className="empty-state">No transaction data yet.</p>}
            {(data?.category_risk ?? []).map((item) => (
              <div className="bar-item" key={item.category}>
                <div><span>{item.category.replaceAll('_', ' ')}</span><strong>{percent(item.fraud_rate)}</strong></div>
                <div className="bar-track"><i style={{ width: `${Math.max(item.fraud_rate * 100, 2)}%` }} /></div>
              </div>
            ))}
          </div>
        </article>
      </div>

      <article className="panel transaction-panel">
        <div className="panel-heading">
          <div><span>Latest decisions</span><h2>Recent transactions</h2></div>
          <small>Auto-refreshes every 15 seconds</small>
        </div>
        <div className="table-scroll">
          <table>
            <thead><tr><th>Transaction</th><th>Merchant</th><th>Category</th><th>Amount</th><th>Risk score</th><th>Decision</th></tr></thead>
            <tbody>
              {(data?.recent_transactions ?? []).map((transaction) => (
                <tr key={transaction.trans_num}>
                  <td><span className="mono">#{transaction.trans_num.slice(0, 8)}</span><small>{new Date(transaction.inserted_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</small></td>
                  <td>{transaction.merchant?.replace('fraud_', '') ?? 'Unknown'}</td>
                  <td className="capitalize">{transaction.category?.replaceAll('_', ' ') ?? 'Unknown'}</td>
                  <td>{money.format(transaction.amt)}</td>
                  <td><span className="risk-number">{percent(transaction.fraud_probability)}</span></td>
                  <td><span className={`status-pill ${transaction.is_fraud_prediction ? 'blocked' : 'approved'}`}>{transaction.is_fraud_prediction ? 'Flagged' : 'Approved'}</span></td>
                </tr>
              ))}
              {!loading && (data?.recent_transactions ?? []).length === 0 && (
                <tr><td colSpan={6} className="empty-cell">No transactions yet. Run a simulation to create the first one.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </article>
    </section>
  )
}

function Metric({ label, value, trend, danger = false }: { label: string; value: string; trend: string; danger?: boolean }) {
  return (
    <article className="metric-card">
      <div className={`metric-icon ${danger ? 'danger' : ''}`}>{danger ? '!' : '⌁'}</div>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{trend}</small>
    </article>
  )
}

import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { getDashboard, getHealth, getPipelineStatus } from '../api'
import { demoDashboard } from '../demoData'
import type { DashboardData, HealthData, PipelineStage, Transaction } from '../types'

const money = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' })
const number = new Intl.NumberFormat('en-US')
const percent = (value: number) => `${(value * 100).toFixed(1)}%`

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [health, setHealth] = useState<HealthData | null>(null)
  const [snapshotMode, setSnapshotMode] = useState(false)
  const [searchParams, setSearchParams] = useSearchParams()
  const [selected, setSelected] = useState<Transaction | null>(null)
  const [trace, setTrace] = useState<PipelineStage[]>([])
  const highlightedId = searchParams.get('highlight')

  const closeInspector = useCallback(() => {
    setSelected(null)
    setTrace([])
    setSearchParams({})
  }, [setSearchParams])

  const load = useCallback(async () => {
    try {
      setError('')
      const dashboard = await getDashboard()
      setData(dashboard)
      setSnapshotMode(Boolean(dashboard._snapshot))
      getHealth().then(setHealth).catch(() => setHealth(null))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to load dashboard')
      setData((current) => current ?? demoDashboard)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
    if (snapshotMode) return
    const timer = window.setInterval(() => void load(), 5_000)
    return () => window.clearInterval(timer)
  }, [load, snapshotMode])

  useEffect(() => {
    if (!highlightedId || !data) return
    const transaction = data.recent_transactions.find((item) => item.trans_num === highlightedId)
    if (transaction) {
      setSelected(transaction)
      void getPipelineStatus(transaction.trans_num)
        .then((status) => setTrace(status.stages))
        .catch(() => setTrace([]))
    }
  }, [data, highlightedId])

  useEffect(() => {
    if (!selected) return
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') closeInspector()
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [closeInspector, selected])

  const inspect = (transaction: Transaction) => {
    setSelected(transaction)
    setSearchParams({ highlight: transaction.trans_num })
    void getPipelineStatus(transaction.trans_num)
      .then((status) => setTrace(status.stages))
      .catch(() => setTrace([]))
  }

  return (
    <section className="dashboard-page page-width">
      <div className="page-title-row">
        <div>
          <div className="eyebrow"><i /> Operations center</div>
          <h1>Fraud overview</h1>
          <p>Live decisions from the CardShield scoring pipeline.</p>
        </div>
        <button className="refresh-button" onClick={() => void load()} disabled={loading}>
          <span className={`refresh-symbol ${loading ? 'spinning' : ''}`} aria-hidden="true" /> Refresh
        </button>
      </div>

      {error && (
        <div className="error-banner preview-banner">
          <strong>Preview data</strong>
          <span>Live services are unavailable ({error}). Showing a clearly labeled demonstration preview.</span>
        </div>
      )}

      <div className="health-strip">
        <div>
          <span className={`health-dot ${health?.status === 'ok' ? '' : 'degraded'}`} />
          <strong>{health?._snapshot ? 'Analytics ready' : health?.status === 'ok' ? 'All systems operational' : 'System degraded'}</strong>
          <small>Model {health?.model_version ?? 'checking…'}</small>
        </div>
        <div className="component-health">
          {Object.entries(health?.components ?? {}).map(([name, component]) => (
            <span key={name}>
              <i className={component.status} /> {name}
              <small>{component.detail}</small>
            </span>
          ))}
        </div>
      </div>

      <div className="metric-grid">
        <Metric
          label="Transactions analyzed"
          value={number.format(data?.metrics.total_transactions ?? 0)}
          trend={`${number.format(data?.window.maximum_transactions ?? 250)} across ${data?.window.days ?? 7} days`}
        />
        <Metric label="Fraud detected" value={number.format(data?.metrics.fraud_transactions ?? 0)} trend="Model decisions" danger />
        <Metric label="Throughput" value={`${(data?.metrics.transactions_per_minute ?? 0).toFixed(1)}/min`} trend="Across observed window" />
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
            <div><span>Signal concentration</span><h2>Categories with highest risk</h2></div>
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
          <small>
            {data?._snapshot
              ? `Complete held out analysis across ${data.window.days} days`
              : `Refreshes every 5 seconds with the latest ${data?.window.maximum_transactions ?? 250} records`}
          </small>
        </div>
        <div className="table-scroll">
          <table>
            <thead><tr><th>Transaction</th><th>Merchant</th><th>Category</th><th>Amount</th><th>Risk score</th><th>Decision</th></tr></thead>
            <tbody>
              {(data?.recent_transactions ?? []).map((transaction) => (
                <tr
                  key={transaction.trans_num}
                  className={transaction.trans_num === highlightedId ? 'highlighted-row' : ''}
                  onClick={() => inspect(transaction)}
                  tabIndex={0}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') inspect(transaction)
                  }}
                >
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
      {selected && (
        <div className="inspector-backdrop" role="presentation" onClick={closeInspector}>
          <aside className="transaction-inspector" role="dialog" aria-modal="true" aria-label="Transaction details" onClick={(event) => event.stopPropagation()}>
            <button className="inspector-close" onClick={closeInspector} aria-label="Close transaction details"><i aria-hidden="true" /></button>
            <div className="result-kicker"><i /> Decision audit</div>
            <h2>{selected.is_fraud_prediction ? 'Flagged transaction' : 'Approved transaction'}</h2>
            <span className={`status-pill ${selected.is_fraud_prediction ? 'blocked' : 'approved'}`}>
              {percent(selected.fraud_probability)} fraud probability
            </span>
            <dl>
              <div><dt>Transaction</dt><dd>#{selected.trans_num.slice(0, 12)}</dd></div>
              <div><dt>Merchant</dt><dd>{selected.merchant?.replace('fraud_', '') ?? 'Unknown'}</dd></div>
              <div><dt>Category</dt><dd>{selected.category?.replaceAll('_', ' ') ?? 'Unknown'}</dd></div>
              <div><dt>Amount</dt><dd>{money.format(selected.amt)}</dd></div>
              <div><dt>Model</dt><dd>{selected.model_version}</dd></div>
              <div><dt>Scored</dt><dd>{new Date(selected.inserted_at).toLocaleString()}</dd></div>
            </dl>
            <div className="audit-trace">
              <strong>Pipeline audit trail</strong>
              {trace.length === 0 && <p>No interactive trace attached. This event may have come from dataset replay.</p>}
              {trace.map((stage) => (
                <div key={`${stage.stage}-${stage.occurred_at}`}>
                  <i />
                  <span><b>{stage.stage.replaceAll('_', ' ')}</b><small>{stage.detail}</small></span>
                  <time>{new Date(stage.occurred_at).toLocaleTimeString()}</time>
                </div>
              ))}
            </div>
          </aside>
        </div>
      )}
    </section>
  )
}

function Metric({ label, value, trend, danger = false }: { label: string; value: string; trend: string; danger?: boolean }) {
  return (
    <article className="metric-card">
      <div className={`metric-icon metric-shape ${danger ? 'danger' : ''}`} aria-hidden="true"><i /></div>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{trend}</small>
    </article>
  )
}

import { type FormEvent, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getOptions, getPipelineStatus, getPresets, predictTransaction, submitPipelineTransaction } from '../api'
import { decisionSignals } from '../riskSignals'
import type {
  DemoPreset,
  PipelineStage,
  PredictionInput,
  PredictionResult,
  SimulatorOptions,
} from '../types'

const initialForm: PredictionInput = {
  amount: 126.42,
  customer_latitude: 40.7128,
  customer_longitude: -74.006,
  merchant_latitude: 40.7306,
  merchant_longitude: -73.9352,
  city_population: 8_336_817,
  merchant: '',
  category: '',
  gender: '',
  job: '',
}

export default function SimulatorPage() {
  const [form, setForm] = useState(initialForm)
  const [options, setOptions] = useState<SimulatorOptions | null>(null)
  const [result, setResult] = useState<PredictionResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [liveMode, setLiveMode] = useState(true)
  const [stages, setStages] = useState<PipelineStage[]>([])
  const [latency, setLatency] = useState<number | null>(null)
  const [presets, setPresets] = useState<DemoPreset[]>([])
  const [activePreset, setActivePreset] = useState('')

  useEffect(() => {
    getOptions()
      .then((values) => {
        setOptions(values)
        setForm((current) => ({
          ...current,
          merchant: values.merchant[0] ?? '',
          category: values.category[0] ?? '',
          gender: values.gender[0] ?? '',
          job: values.job[0] ?? '',
        }))
      })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Unable to load model options'))
    getPresets().then(setPresets).catch(() => {
      // Presets are a demo convenience; manual scoring remains available.
    })
  }, [])

  const update = (field: keyof PredictionInput, value: string) => {
    const numericFields: Array<keyof PredictionInput> = [
      'amount', 'customer_latitude', 'customer_longitude',
      'merchant_latitude', 'merchant_longitude', 'city_population',
    ]
    setForm((current) => ({
      ...current,
      [field]: numericFields.includes(field) ? Number(value) : value,
    }))
    setActivePreset('')
  }

  const applyPreset = (preset: DemoPreset) => {
    setForm(preset.input)
    setActivePreset(preset.id)
    setResult(null)
    setStages([])
    setError('')
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    setResult(null)
    setStages([])
    setLatency(null)
    try {
      if (!liveMode) {
        setResult(await predictTransaction(form))
        return
      }
      const submission = await submitPipelineTransaction(form)
      const deadline = Date.now() + 45_000
      while (Date.now() < deadline) {
        const status = await getPipelineStatus(submission.transaction_id)
        setStages(status.stages)
        if (status.status === 'complete' && status.prediction) {
          setLatency(status.latency_ms)
          setResult(status.prediction)
          return
        }
        await new Promise((resolve) => window.setTimeout(resolve, 750))
      }
      throw new Error('The streaming pipeline did not complete within 45 seconds')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Prediction failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="simulator-page page-width">
      <div className="simulator-heading">
        <div className="eyebrow"><i /> Interactive model</div>
        <h1>Transaction simulator</h1>
        <p>Enter payment details and run them through the trained Spark fraud pipeline.</p>
      </div>

      <div className="simulator-layout">
        <form className="simulator-form panel" onSubmit={(event) => void submit(event)}>
          <div className="mode-switch" role="group" aria-label="Scoring path">
            <button type="button" className={liveMode ? 'active' : ''} onClick={() => setLiveMode(true)}>
              Live pipeline
            </button>
            <button type="button" className={!liveMode ? 'active' : ''} onClick={() => setLiveMode(false)}>
              Instant API
            </button>
          </div>
          <p className="mode-description">
            {liveMode
              ? 'Publishes to Kafka, scores in Spark Structured Streaming, then persists to Cassandra.'
              : 'Scores synchronously with the same Spark model for a faster inference check.'}
          </p>
          {presets.length > 0 && (
            <div className="preset-section">
              <div className="preset-heading"><span>Demo scenarios</span><small>Held-out data · pre-scored</small></div>
              <div className="preset-grid">
                {presets.map((preset) => (
                  <button
                    type="button"
                    className={activePreset === preset.id ? 'active' : ''}
                    onClick={() => applyPreset(preset)}
                    key={preset.id}
                  >
                    <span className={preset.expected_decision ? 'preset-risk' : 'preset-safe'}>
                      {preset.expected_decision ? 'High risk' : 'Low risk'}
                    </span>
                    <strong>{preset.name}</strong>
                    <small>{preset.description}</small>
                    <b>{(preset.expected_probability * 100).toFixed(1)}% expected score</b>
                  </button>
                ))}
              </div>
            </div>
          )}
          <div className="form-section-heading"><span>01</span><div><h2>Payment details</h2><p>Describe the transaction being attempted.</p></div></div>
          <div className="form-grid">
            <Field label="Amount" prefix="$">
              <input type="number" min="0.01" step="0.01" value={form.amount} onChange={(e) => update('amount', e.target.value)} required />
            </Field>
            <Field label="Category">
              <select value={form.category} onChange={(e) => update('category', e.target.value)} required>
                {(options?.category ?? []).map((value) => <option key={value}>{value}</option>)}
              </select>
            </Field>
            <Field label="Merchant" wide>
              <select value={form.merchant} onChange={(e) => update('merchant', e.target.value)} required>
                {(options?.merchant ?? []).map((value) => <option key={value} value={value}>{value.replace('fraud_', '')}</option>)}
              </select>
            </Field>
            <Field label="Cardholder gender">
              <select value={form.gender} onChange={(e) => update('gender', e.target.value)} required>
                {(options?.gender ?? []).map((value) => <option key={value} value={value}>{value === 'F' ? 'Female' : value === 'M' ? 'Male' : value}</option>)}
              </select>
            </Field>
            <Field label="Cardholder job">
              <select value={form.job} onChange={(e) => update('job', e.target.value)} required>
                {(options?.job ?? []).map((value) => <option key={value}>{value}</option>)}
              </select>
            </Field>
          </div>

          <div className="form-divider" />
          <div className="form-section-heading"><span>02</span><div><h2>Location signals</h2><p>Compare cardholder and merchant geography.</p></div></div>
          <div className="form-grid">
            <Field label="Customer latitude"><input type="number" step="any" min="-90" max="90" value={form.customer_latitude} onChange={(e) => update('customer_latitude', e.target.value)} required /></Field>
            <Field label="Customer longitude"><input type="number" step="any" min="-180" max="180" value={form.customer_longitude} onChange={(e) => update('customer_longitude', e.target.value)} required /></Field>
            <Field label="Merchant latitude"><input type="number" step="any" min="-90" max="90" value={form.merchant_latitude} onChange={(e) => update('merchant_latitude', e.target.value)} required /></Field>
            <Field label="Merchant longitude"><input type="number" step="any" min="-180" max="180" value={form.merchant_longitude} onChange={(e) => update('merchant_longitude', e.target.value)} required /></Field>
            <Field label="City population" wide><input type="number" min="1" step="1" value={form.city_population} onChange={(e) => update('city_population', e.target.value)} required /></Field>
          </div>

          {error && <div className="form-error">{error}</div>}
          <button className="button button-primary submit-button" type="submit" disabled={loading || !options}>
            {loading ? <><span className="loader" /> Analyzing transaction…</> : <>Analyze transaction <span>→</span></>}
          </button>
          <p className="form-footnote"><span>⌁</span> Scored with the same model used by the streaming pipeline.</p>
        </form>

        <aside className={`result-card ${result ? (result.is_fraud_prediction ? 'result-fraud' : 'result-safe') : ''}`}>
          {!result && stages.length === 0 && (
            <div className="result-placeholder">
              <div className="scan-visual"><span /><i /><b>⌁</b></div>
              <h2>Ready to analyze</h2>
              <p>Your fraud decision and confidence score will appear here.</p>
              <div className="placeholder-list"><span>✓ 11 model features</span><span>✓ Live Spark inference</span><span>✓ Cassandra audit trail</span></div>
            </div>
          )}
          {!result && stages.length > 0 && (
            <PipelineProgress stages={stages} />
          )}
          {result && (
            <div className="result-content">
              <div className="result-kicker"><i /> Analysis complete</div>
              <div className="verdict-icon">{result.is_fraud_prediction ? '!' : '✓'}</div>
              <span className="verdict-label">Model decision</span>
              <h2>{result.is_fraud_prediction ? 'Review recommended' : 'Low risk detected'}</h2>
              <p>{result.is_fraud_prediction ? 'The model found a suspicious pattern that warrants human review.' : 'The model did not find a strong fraud pattern. This is a risk estimate, not a guarantee.'}</p>
              <div className="probability-block">
                <div><span>Fraud probability</span><strong>{(result.fraud_probability * 100).toFixed(2)}%</strong></div>
                <div className="probability-track"><i style={{ width: `${result.fraud_probability * 100}%` }} /></div>
              </div>
              <dl>
                <div><dt>Transaction ID</dt><dd>#{result.trans_num.slice(0, 10)}</dd></div>
                <div><dt>Amount</dt><dd>${result.amt.toFixed(2)}</dd></div>
                <div><dt>Model version</dt><dd>{result.model_version}</dd></div>
                <div><dt>Dashboard saved</dt><dd>{result.stored ? 'Yes' : 'No'}</dd></div>
                {latency !== null && <div><dt>Pipeline latency</dt><dd>{latency.toLocaleString()} ms</dd></div>}
              </dl>
              <div className="context-signals">
                <div><strong>Decision context</strong><small>Derived indicators · not model attribution</small></div>
                {decisionSignals(form, result).map((signal) => (
                  <span className={signal.risk ? 'risk' : ''} key={signal.label}>
                    <i>{signal.risk ? '!' : '✓'}</i>
                    <b>{signal.label}</b>
                    <small>{signal.detail}</small>
                  </span>
                ))}
              </div>
              {stages.length > 0 && <PipelineProgress stages={stages} compact />}
              <Link className="dashboard-payoff" to={`/dashboard?highlight=${result.trans_num}`}>
                View on live dashboard <span>→</span>
              </Link>
              <button className="reset-button" onClick={() => { setResult(null); setStages([]) }}>Test another transaction</button>
            </div>
          )}
        </aside>
      </div>
    </section>
  )
}

const pipelineSteps = [
  ['API_ACCEPTED', 'API validated'],
  ['KAFKA_PUBLISHED', 'Kafka published'],
  ['MODEL_SCORED', 'Spark scored'],
  ['CASSANDRA_PERSISTED', 'Cassandra saved'],
] as const

function PipelineProgress({ stages, compact = false }: { stages: PipelineStage[]; compact?: boolean }) {
  const completed = new Map(stages.map((stage) => [stage.stage, stage]))
  return (
    <div className={`pipeline-progress ${compact ? 'compact' : ''}`} aria-live="polite">
      {!compact && <><div className="result-kicker"><i /> Live transaction trace</div><h2>Moving through the shield</h2></>}
      <ol>
        {pipelineSteps.map(([name, label], index) => {
          const stage = completed.get(name)
          const isActive = !stage && completed.size === index
          return (
            <li className={stage ? 'complete' : isActive ? 'active' : ''} key={name}>
              <span>{stage ? '✓' : index + 1}</span>
              <div>
                <strong>{label}</strong>
                <small>{stage?.detail ?? (isActive ? 'Waiting for service…' : 'Pending')}</small>
              </div>
            </li>
          )
        })}
      </ol>
    </div>
  )
}

function Field({ label, prefix, wide = false, children }: { label: string; prefix?: string; wide?: boolean; children: React.ReactNode }) {
  return (
    <label className={wide ? 'wide' : ''}>
      <span>{label}</span>
      <div className={prefix ? 'input-prefix' : ''}>{prefix && <b>{prefix}</b>}{children}</div>
    </label>
  )
}

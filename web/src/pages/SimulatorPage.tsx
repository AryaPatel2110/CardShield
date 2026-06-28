import { type FormEvent, useEffect, useState } from 'react'
import { getOptions, predictTransaction } from '../api'
import type { PredictionInput, PredictionResult, SimulatorOptions } from '../types'

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
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    setResult(null)
    try {
      setResult(await predictTransaction(form))
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
          {!result && (
            <div className="result-placeholder">
              <div className="scan-visual"><span /><i /><b>⌁</b></div>
              <h2>Ready to analyze</h2>
              <p>Your fraud decision and confidence score will appear here.</p>
              <div className="placeholder-list"><span>✓ 11 model features</span><span>✓ Live Spark inference</span><span>✓ Cassandra audit trail</span></div>
            </div>
          )}
          {result && (
            <div className="result-content">
              <div className="result-kicker"><i /> Analysis complete</div>
              <div className="verdict-icon">{result.is_fraud_prediction ? '!' : '✓'}</div>
              <span className="verdict-label">Model decision</span>
              <h2>{result.is_fraud_prediction ? 'Fraud detected' : 'Transaction safe'}</h2>
              <p>{result.is_fraud_prediction ? 'This transaction matches suspicious patterns and should be reviewed.' : 'No strong fraud pattern was detected for this transaction.'}</p>
              <div className="probability-block">
                <div><span>Fraud probability</span><strong>{(result.fraud_probability * 100).toFixed(2)}%</strong></div>
                <div className="probability-track"><i style={{ width: `${result.fraud_probability * 100}%` }} /></div>
              </div>
              <dl>
                <div><dt>Transaction ID</dt><dd>#{result.trans_num.slice(0, 10)}</dd></div>
                <div><dt>Amount</dt><dd>${result.amt.toFixed(2)}</dd></div>
                <div><dt>Model version</dt><dd>{result.model_version}</dd></div>
                <div><dt>Dashboard saved</dt><dd>{result.stored ? 'Yes' : 'No'}</dd></div>
              </dl>
              <button className="reset-button" onClick={() => setResult(null)}>Test another transaction</button>
            </div>
          )}
        </aside>
      </div>
    </section>
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

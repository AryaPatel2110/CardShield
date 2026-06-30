import { useEffect, useState } from 'react'
import { getHealth, getModelReport } from '../api'
import type { HealthData, ModelReport } from '../types'

const percent = (value?: number) => value === undefined ? '—' : `${(value * 100).toFixed(1)}%`

export default function SystemPage() {
  const [health, setHealth] = useState<HealthData | null>(null)
  const [report, setReport] = useState<ModelReport | null>(null)

  useEffect(() => {
    void getHealth().then(setHealth).catch(() => setHealth(null))
    void getModelReport().then(setReport).catch(() => {
      setReport({
        available: false,
        model_version: 'unavailable',
        message: 'The model report endpoint is unavailable.',
      })
    })
  }, [])

  return (
    <section className="system-page page-width">
      <div className="system-heading">
        <div className="eyebrow"><i /> Engineering evidence</div>
        <h1>Inside the shield</h1>
        <p>Live service health, system architecture, and honest model evaluation.</p>
      </div>

      <article className="architecture-panel panel">
        <div className="panel-heading">
          <div><span>Runtime architecture</span><h2>One transaction, end to end</h2></div>
          <small>{health?.status === 'ok' ? 'All services ready' : 'Checking services…'}</small>
        </div>
        <div className="architecture-flow">
          <ServiceNode name="React" detail="Operator console" status="ready" />
          <FlowArrow label="HTTPS" />
          <ServiceNode name="FastAPI" detail="Schema + orchestration" status={health?.components.api.status} />
          <FlowArrow label="EVENT" />
          <ServiceNode name="Kafka" detail="transactions.v1" status={health?.components.kafka.status} />
          <FlowArrow label="STREAM" />
          <ServiceNode name="Spark ML" detail="Structured scoring" status={health?.components.model.status} />
          <FlowArrow label="WRITE" />
          <ServiceNode name="Cassandra" detail="Query tables" status={health?.components.cassandra.status} />
        </div>
        <div className="architecture-notes">
          <span>✓ Versioned event contract</span>
          <span>✓ Dead-letter topic</span>
          <span>✓ Checkpointed offsets</span>
          <span>✓ Idempotent writes</span>
        </div>
      </article>

      <div className="evidence-grid">
        <article className="panel model-panel">
          <div className="panel-heading">
            <div><span>Held-out evaluation</span><h2>Model quality</h2></div>
            <small>{report?.model_version ?? 'Loading…'}</small>
          </div>
          {!report?.available && (
            <div className="model-unavailable">
              <strong>Release metrics pending</strong>
              <p>{report?.message ?? 'Loading model metadata…'}</p>
            </div>
          )}
          {report?.available && report.metrics && (
            <>
              <div className="model-metrics">
                <ModelMetric label="Fraud recall" value={percent(report.metrics.fraud_recall)} primary />
                <ModelMetric label="Fraud precision" value={percent(report.metrics.fraud_precision)} primary />
                <ModelMetric label="PR-AUC" value={percent(report.metrics.area_under_pr)} />
                <ModelMetric label="ROC-AUC" value={percent(report.metrics.area_under_roc)} />
              </div>
              <p className="model-context">
                {report.algorithm} · {report.training_rows?.toLocaleString()} training rows · {report.validation_rows?.toLocaleString()} held-out rows
              </p>
              {report.threshold_diagnostics && (
                <div className="threshold-note">
                  <span>Operating threshold</span>
                  <strong>{report.threshold_diagnostics.applied_threshold.toFixed(2)}</strong>
                  <small>
                    Selected on the earlier calibration period using: {report.threshold_diagnostics.selection_policy}.
                    Final metrics come from the later, untouched evaluation period.
                  </small>
                </div>
              )}
              <div className="model-warnings">
                {report.warnings?.map((warning) => <p key={warning}>! {warning}</p>)}
              </div>
            </>
          )}
        </article>

        <article className="panel tradeoff-panel">
          <div className="panel-heading">
            <div><span>Production thinking</span><h2>Known tradeoffs</h2></div>
          </div>
          <ul>
            <li><strong>Imbalanced labels</strong><span>PR-AUC, recall, and precision lead the evaluation—not accuracy.</span></li>
            <li><strong>Decision threshold</strong><span>Must be tuned against false-decline and fraud-loss costs.</span></li>
            <li><strong>Categorical encoding</strong><span>Integer labels are a baseline; hashing or target encoding is the next experiment.</span></li>
            <li><strong>Sensitive attributes</strong><span>Gender and occupation require fairness review before production use.</span></li>
          </ul>
        </article>
      </div>
    </section>
  )
}

function ServiceNode({ name, detail, status }: { name: string; detail: string; status?: string }) {
  return (
    <div className="service-node">
      <i className={status === 'ready' ? 'ready' : ''} />
      <strong>{name}</strong>
      <span>{detail}</span>
    </div>
  )
}

function FlowArrow({ label }: { label: string }) {
  return <div className="flow-arrow"><span>{label}</span><i>→</i></div>
}

function ModelMetric({ label, value, primary = false }: { label: string; value: string; primary?: boolean }) {
  return <div className={primary ? 'primary' : ''}><span>{label}</span><strong>{value}</strong></div>
}

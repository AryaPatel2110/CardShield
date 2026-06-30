export interface SnapshotMetadata {
  mode: 'snapshot'
  exported_at: string
  source: string
  schema_version: number
}

export interface Transaction {
  inserted_at: string
  trans_num: string
  merchant: string | null
  category: string | null
  amt: number
  is_fraud: number | null
  is_fraud_prediction: number
  fraud_probability: number
  model_version: string
}

export interface DashboardData {
  _snapshot?: SnapshotMetadata
  metrics: {
    total_transactions: number
    fraud_transactions: number
    fraud_rate: number
    amount_at_risk: number
    average_probability: number
    transactions_per_minute: number
  }
  category_risk: Array<{
    category: string
    transactions: number
    fraud_count: number
    fraud_rate: number
  }>
  recent_transactions: Transaction[]
  generated_at: string
  window: {
    transactions: number
    maximum_transactions: number
    days: number
    started_at: string | null
  }
}

export interface HealthData {
  _snapshot?: SnapshotMetadata
  status: 'ok' | 'degraded'
  components: Record<string, {
    status: 'ready' | 'unavailable'
    detail: string
  }>
  model_version: string
  uptime_seconds: number
  checked_at: string
}

export interface PredictionInput {
  amount: number
  customer_latitude: number
  customer_longitude: number
  merchant_latitude: number
  merchant_longitude: number
  city_population: number
  merchant: string
  category: string
  gender: string
  job: string
}

export interface PredictionResult {
  _snapshot?: SnapshotMetadata
  trans_num: string
  amt: number
  merchant: string
  category: string
  is_fraud_prediction: number
  fraud_probability: number
  model_version: string
  inserted_at: string
  stored: boolean
}

export type PipelineStageName =
  | 'API_ACCEPTED'
  | 'KAFKA_PUBLISHED'
  | 'MODEL_SCORED'
  | 'CASSANDRA_PERSISTED'

export interface PipelineStage {
  trans_num: string
  occurred_at: string
  stage: PipelineStageName
  detail: string
  amt: number | null
  merchant: string | null
  category: string | null
  fraud_probability: number | null
  is_fraud_prediction: number | null
  model_version: string | null
}

export interface PipelineSubmission {
  transaction_id: string
  status: 'processing'
  poll_url: string
}

export interface PipelineStatus {
  transaction_id: string
  status: 'processing' | 'complete'
  stages: PipelineStage[]
  latency_ms: number | null
  prediction: PredictionResult | null
}

export interface SimulatorOptions {
  _snapshot?: SnapshotMetadata
  merchant: string[]
  category: string[]
  gender: string[]
  job: string[]
}

export interface DemoPreset {
  id: string
  name: string
  description: string
  expected_decision: number
  expected_probability: number
  input: PredictionInput
}

export interface ModelReport {
  _snapshot?: SnapshotMetadata
  available: boolean
  model_version: string
  message?: string
  algorithm?: string
  trained_at?: string
  training_rows?: number
  validation_rows?: number
  num_trees?: number
  max_depth?: number
  metrics?: {
    area_under_pr: number
    area_under_roc: number
    fraud_precision: number
    fraud_recall: number
    fraud_f1: number
    weighted_f1: number
    accuracy: number
    confusion_matrix: Record<string, number>
  }
  warnings?: string[]
  threshold_diagnostics?: {
    applied_threshold: number
    selected_on_calibration: {
      threshold: number
      fraud_precision: number
      fraud_recall: number
      fraud_f1: number
    }
    selection_policy: string
    note: string
  }
}

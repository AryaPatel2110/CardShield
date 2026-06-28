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
  metrics: {
    total_transactions: number
    fraud_transactions: number
    fraud_rate: number
    amount_at_risk: number
    average_probability: number
  }
  category_risk: Array<{
    category: string
    transactions: number
    fraud_count: number
    fraud_rate: number
  }>
  recent_transactions: Transaction[]
  generated_at: string
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

export interface SimulatorOptions {
  merchant: string[]
  category: string[]
  gender: string[]
  job: string[]
}

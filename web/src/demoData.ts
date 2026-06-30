import type { DashboardData } from './types'

const now = Date.now()

export const demoDashboard: DashboardData = {
  metrics: {
    total_transactions: 248,
    fraud_transactions: 7,
    fraud_rate: 7 / 248,
    amount_at_risk: 4_821.37,
    average_probability: 0.084,
    transactions_per_minute: 18.6,
  },
  category_risk: [
    { category: 'shopping_net', transactions: 21, fraud_count: 3, fraud_rate: 3 / 21 },
    { category: 'misc_net', transactions: 17, fraud_count: 2, fraud_rate: 2 / 17 },
    { category: 'grocery_pos', transactions: 38, fraud_count: 2, fraud_rate: 2 / 38 },
    { category: 'gas_transport', transactions: 44, fraud_count: 0, fraud_rate: 0 },
  ],
  recent_transactions: [
    ['demo-fraud-01', 'fraud_Schmitt Inc', 'shopping_net', 1299.99, 1, 0.947],
    ['demo-safe-01', 'fraud_Kuphal-Bartoletti', 'gas_transport', 42.18, 0, 0.018],
    ['demo-safe-02', 'fraud_Hills-Witting', 'grocery_pos', 86.44, 0, 0.031],
    ['demo-fraud-02', 'fraud_Pacocha-Bauch', 'misc_net', 742.21, 1, 0.882],
  ].map(([trans_num, merchant, category, amt, prediction, probability], index) => ({
    inserted_at: new Date(now - index * 42_000).toISOString(),
    trans_num: String(trans_num),
    merchant: String(merchant),
    category: String(category),
    amt: Number(amt),
    is_fraud: null,
    is_fraud_prediction: Number(prediction),
    fraud_probability: Number(probability),
    model_version: 'demo preview',
  })),
  generated_at: new Date(now).toISOString(),
  window: {
    transactions: 248,
    maximum_transactions: 250,
    days: 7,
    started_at: new Date(now - 13 * 60_000).toISOString(),
  },
}

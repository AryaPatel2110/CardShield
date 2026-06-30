import { describe, expect, it } from 'vitest'
import { decisionSignals, distanceMiles } from './riskSignals'
import type { PredictionInput, PredictionResult } from './types'

const input: PredictionInput = {
  amount: 750,
  customer_latitude: 40.7128,
  customer_longitude: -74.006,
  merchant_latitude: 34.0522,
  merchant_longitude: -118.2437,
  city_population: 8_000_000,
  merchant: 'Store',
  category: 'shopping_net',
  gender: 'F',
  job: 'Engineer',
}

const result: PredictionResult = {
  trans_num: 'test',
  amt: 750,
  merchant: 'Store',
  category: 'shopping_net',
  is_fraud_prediction: 1,
  fraud_probability: 0.91,
  model_version: 'test',
  inserted_at: new Date(0).toISOString(),
  stored: true,
}

describe('risk signal helpers', () => {
  it('calculates a realistic great-circle distance', () => {
    expect(distanceMiles(40.7128, -74.006, 34.0522, -118.2437)).toBeCloseTo(2445, -1)
  })

  it('marks high amount, long distance, and model score as risk context', () => {
    expect(decisionSignals(input, result).map((signal) => signal.risk)).toEqual([
      true,
      true,
      true,
    ])
  })
})

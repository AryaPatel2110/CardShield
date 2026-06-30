import type { PredictionInput, PredictionResult } from './types'

export interface DecisionSignal {
  label: string
  detail: string
  risk: boolean
}

export function decisionSignals(
  form: PredictionInput,
  result: PredictionResult,
): DecisionSignal[] {
  const distance = distanceMiles(
    form.customer_latitude,
    form.customer_longitude,
    form.merchant_latitude,
    form.merchant_longitude,
  )
  return [
    {
      label: 'Transaction amount',
      detail: form.amount >= 500
        ? `$${form.amount.toFixed(2)} is a high-value payment`
        : `$${form.amount.toFixed(2)} is below the high-value demo threshold`,
      risk: form.amount >= 500,
    },
    {
      label: 'Location distance',
      detail: `${distance.toFixed(1)} miles between customer and merchant`,
      risk: distance >= 100,
    },
    {
      label: 'Model score',
      detail: `${(result.fraud_probability * 100).toFixed(1)}% estimated fraud probability`,
      risk: result.fraud_probability >= 0.5,
    },
  ]
}

export function distanceMiles(lat1: number, lon1: number, lat2: number, lon2: number) {
  const radians = (degrees: number) => degrees * Math.PI / 180
  const latitudeDelta = radians(lat2 - lat1)
  const longitudeDelta = radians(lon2 - lon1)
  const a = Math.sin(latitudeDelta / 2) ** 2
    + Math.cos(radians(lat1)) * Math.cos(radians(lat2)) * Math.sin(longitudeDelta / 2) ** 2
  return 3958.8 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

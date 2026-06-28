import type {
  DashboardData,
  PredictionInput,
  PredictionResult,
  SimulatorOptions,
} from './types'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  })
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(error.detail ?? `Request failed with status ${response.status}`)
  }
  return response.json() as Promise<T>
}

export const getDashboard = () => request<DashboardData>('/api/dashboard')
export const getOptions = () => request<SimulatorOptions>('/api/options')
export const predictTransaction = (input: PredictionInput) =>
  request<PredictionResult>('/api/predict', {
    method: 'POST',
    body: JSON.stringify(input),
  })

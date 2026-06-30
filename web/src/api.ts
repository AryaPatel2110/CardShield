import type {
  DashboardData,
  DemoPreset,
  HealthData,
  ModelReport,
  PredictionInput,
  PredictionResult,
  PipelineStatus,
  PipelineSubmission,
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
export const getHealth = () => request<HealthData>('/api/health')
export const getModelReport = () => request<ModelReport>('/api/model')
export const getOptions = () => request<SimulatorOptions>('/api/options')
export const getPresets = () =>
  request<{ presets: DemoPreset[] }>('/api/presets').then((result) => result.presets)
export const predictTransaction = (input: PredictionInput) =>
  request<PredictionResult>('/api/predict', {
    method: 'POST',
    body: JSON.stringify(input),
  })

export const submitPipelineTransaction = (input: PredictionInput) =>
  request<PipelineSubmission>('/api/pipeline', {
    method: 'POST',
    body: JSON.stringify(input),
  })

export const getPipelineStatus = (transactionId: string) =>
  request<PipelineStatus>(`/api/pipeline/${transactionId}`)

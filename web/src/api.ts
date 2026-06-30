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

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')
const SNAPSHOT_BASE_URL = (import.meta.env.VITE_SNAPSHOT_BASE_URL ?? '/snapshots').replace(/\/$/, '')

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
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
  const contentType = response.headers.get('content-type') ?? ''
  if (!contentType.includes('application/json')) {
    throw new Error('The live API did not return JSON')
  }
  return response.json() as Promise<T>
}

async function snapshot<T>(file: string): Promise<T> {
  const response = await fetch(`${SNAPSHOT_BASE_URL}/${file}`, {
    headers: { Accept: 'application/json' },
  })
  if (!response.ok) {
    throw new Error(`Captured results file ${file} is unavailable`)
  }
  return response.json() as Promise<T>
}

async function getWithSnapshot<T>(path: string, file: string): Promise<T> {
  try {
    return await request<T>(path)
  } catch {
    return snapshot<T>(file)
  }
}

export const getDashboard = () => getWithSnapshot<DashboardData>('/api/dashboard', 'dashboard.json')
export const getHealth = () => getWithSnapshot<HealthData>('/api/health', 'health.json')
export const getModelReport = () => getWithSnapshot<ModelReport>('/api/model', 'model.json')
export const getOptions = () => getWithSnapshot<SimulatorOptions>('/api/options', 'options.json')
export const getPresets = () =>
  getWithSnapshot<{ presets: DemoPreset[] }>('/api/presets', 'presets.json')
    .then((result) => result.presets)

const predictionInputsMatch = (left: PredictionInput, right: PredictionInput) =>
  (Object.keys(left) as Array<keyof PredictionInput>)
    .every((key) => left[key] === right[key])

export const predictTransaction = async (input: PredictionInput) => {
  try {
    return await request<PredictionResult>('/api/predict', {
      method: 'POST',
      body: JSON.stringify(input),
    })
  } catch (liveError) {
    const exported = await snapshot<{
      predictions: Array<{ input: PredictionInput; result: PredictionResult }>
    }>('predictions.json')
    const match = exported.predictions.find((item) => predictionInputsMatch(item.input, input))
    if (match) return match.result
    const message = liveError instanceof Error ? liveError.message : 'Live scoring is unavailable'
    throw new Error(
      `Live scoring is offline (${message}). Start the backend or choose an exported demo scenario.`,
    )
  }
}

export const submitPipelineTransaction = (input: PredictionInput) =>
  request<PipelineSubmission>('/api/pipeline', {
    method: 'POST',
    body: JSON.stringify(input),
  }).catch((reason: unknown) => {
    const message = reason instanceof Error ? reason.message : 'Live pipeline unavailable'
    throw new Error(`The live Kafka pipeline is offline (${message}). Use Instant API for an exported scenario.`)
  })

export const getPipelineStatus = (transactionId: string) =>
  request<PipelineStatus>(`/api/pipeline/${transactionId}`)

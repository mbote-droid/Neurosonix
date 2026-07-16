// Typed client for the agentic evaluation API.
// Mirrors backend/agentic/schemas.py.

// Configurable so deployments can point at a non-default backend host.
const API_BASE =
  (import.meta.env?.VITE_API_BASE as string | undefined) ?? 'http://localhost:8000'

export type Dimension =
  | 'task_completion'
  | 'conversational_naturalness'
  | 'audio_comprehension'
  | 'instruction_adherence'
  | 'technical_clarity'

export type Domain = 'finance' | 'healthcare' | 'bioinformatics' | 'travel'

export interface ScenarioTemplate {
  id: string
  domain: Domain
  name: string
  system_prompt: string
  user_goal: string
  example_exchange: string | null
}

export interface RubricCriterion {
  dimension: Dimension
  description: string
  scale_min: number
  scale_max: number
  anchors: Record<string, string>
}

export interface AgentScore {
  dimension: Dimension
  score: number
  rationale: string
  confidence: number
  degraded: boolean
}

export interface EvaluationResult {
  id: string
  scenario_id: string
  model_name: string
  transcript: string
  agent_response: string
  agent_scores: AgentScore[]
  synthesized_score: number
  audio_file_id: string | null
  degraded: boolean
  created_at: string
}

export interface ModelComparisonEntry {
  model_name: string
  synthesized_score: number
  transcript: string
  per_dimension: Record<string, number>
}

export interface ModelComparison {
  id: string
  scenario_id: string
  transcript: string
  entries: ModelComparisonEntry[]
  winner: string | null
  audio_file_id: string | null
  created_at: string
}

export interface EvaluationHealth {
  status: string
  llm_available: boolean
  mode: string
  scenarios: number
  dimensions: number
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const err = await res.json()
      if (err?.detail) detail = err.detail
    } catch {
      /* keep statusText */
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

export const evaluationApi = {
  health: () => getJson<EvaluationHealth>('/api/evaluate/health'),
  scenarios: () => getJson<ScenarioTemplate[]>('/api/evaluate/scenarios'),
  rubrics: () => getJson<RubricCriterion[]>('/api/evaluate/rubrics'),
  evaluate: (body: {
    scenario_id: string
    transcript: string
    model_name?: string
    audio_file_id?: string
  }) => postJson<EvaluationResult>('/api/evaluate/', body),
  compare: (body: {
    scenario_id: string
    model_transcripts: Record<string, string>
    audio_file_id?: string
  }) => postJson<ModelComparison>('/api/evaluate/compare', body),
}

export const DIMENSION_LABELS: Record<Dimension, string> = {
  task_completion: 'Task Completion',
  conversational_naturalness: 'Conversational Naturalness',
  audio_comprehension: 'Audio Comprehension',
  instruction_adherence: 'Instruction Adherence',
  technical_clarity: 'Technical Clarity',
}

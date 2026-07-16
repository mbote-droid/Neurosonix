import { useEffect, useMemo, useState } from 'react'
import './Evaluation.css'
import {
  evaluationApi,
  type ScenarioTemplate,
  type EvaluationResult,
  type ModelComparison,
  type EvaluationHealth,
  type Domain,
} from '../api/evaluation'
import EvaluationScorePanel from './EvaluationScorePanel'
import ModelComparisonPanel from './ModelComparisonPanel'

interface Props {
  seedTranscript?: string
  seedAudioFileId?: string
}

type Mode = 'single' | 'compare'

const DOMAIN_ORDER: Domain[] = ['finance', 'healthcare', 'bioinformatics', 'travel']
const DOMAIN_LABELS: Record<Domain, string> = {
  finance: 'Finance',
  healthcare: 'Healthcare',
  bioinformatics: 'Bioinformatics',
  travel: 'Travel',
}

export default function EvaluationDashboard({ seedTranscript, seedAudioFileId }: Props) {
  const [health, setHealth] = useState<EvaluationHealth | null>(null)
  const [scenarios, setScenarios] = useState<ScenarioTemplate[]>([])
  const [scenarioId, setScenarioId] = useState('')
  const [mode, setMode] = useState<Mode>('single')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Single-evaluation state
  const [transcript, setTranscript] = useState(seedTranscript ?? '')
  const [modelName, setModelName] = useState('')
  const [result, setResult] = useState<EvaluationResult | null>(null)

  // Comparison state
  const [rows, setRows] = useState<{ model: string; transcript: string }[]>([
    { model: 'Whisper', transcript: seedTranscript ?? '' },
    { model: 'Gemini', transcript: '' },
  ])
  const [comparison, setComparison] = useState<ModelComparison | null>(null)

  useEffect(() => {
    evaluationApi.health().then(setHealth).catch(() => setHealth(null))
    evaluationApi
      .scenarios()
      .then((s) => {
        setScenarios(s)
        if (s.length > 0) setScenarioId(s[0].id)
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load scenarios'))
  }, [])

  const grouped = useMemo(() => {
    const byDomain: Record<string, ScenarioTemplate[]> = {}
    for (const s of scenarios) (byDomain[s.domain] ??= []).push(s)
    return byDomain
  }, [scenarios])

  const selectedScenario = scenarios.find((s) => s.id === scenarioId)

  const runEvaluate = async () => {
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const res = await evaluationApi.evaluate({
        scenario_id: scenarioId,
        transcript,
        model_name: modelName || undefined,
        audio_file_id: seedAudioFileId,
      })
      setResult(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Evaluation failed')
    } finally {
      setLoading(false)
    }
  }

  const runCompare = async () => {
    setLoading(true)
    setError('')
    setComparison(null)
    try {
      const model_transcripts: Record<string, string> = {}
      for (const r of rows) {
        const name = r.model.trim()
        if (name && r.transcript.trim()) model_transcripts[name] = r.transcript
      }
      if (Object.keys(model_transcripts).length < 2) {
        throw new Error('Add at least two models with transcripts.')
      }
      const res = await evaluationApi.compare({
        scenario_id: scenarioId,
        model_transcripts,
        audio_file_id: seedAudioFileId,
      })
      setComparison(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Comparison failed')
    } finally {
      setLoading(false)
    }
  }

  const updateRow = (i: number, patch: Partial<{ model: string; transcript: string }>) =>
    setRows((rs) => rs.map((r, idx) => (idx === i ? { ...r, ...patch } : r)))

  const addRow = () => setRows((rs) => [...rs, { model: '', transcript: '' }])
  const removeRow = (i: number) => setRows((rs) => rs.filter((_, idx) => idx !== i))

  return (
    <section className="eval-dashboard">
      <div className="eval-head">
        <h2>Agentic Evaluation</h2>
        {health && (
          <span className={`eval-mode-badge ${health.llm_available ? 'live' : 'degraded'}`}>
            {health.llm_available ? '● Live LLM' : '● Offline (heuristic)'}
          </span>
        )}
      </div>
      <p className="eval-sub">
        Score a voice-agent reply across five dimensions, or compare two models on the
        same scenario.
      </p>

      <div className="eval-controls">
        <label className="eval-field">
          <span>Scenario</span>
          <select value={scenarioId} onChange={(e) => setScenarioId(e.target.value)}>
            {DOMAIN_ORDER.filter((d) => grouped[d]?.length).map((d) => (
              <optgroup key={d} label={DOMAIN_LABELS[d]}>
                {grouped[d].map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </label>

        <div className="eval-mode-toggle">
          <button
            className={mode === 'single' ? 'active' : ''}
            onClick={() => setMode('single')}
          >
            Single
          </button>
          <button
            className={mode === 'compare' ? 'active' : ''}
            onClick={() => setMode('compare')}
          >
            Compare models
          </button>
        </div>
      </div>

      {selectedScenario && (
        <p className="eval-goal">
          <strong>Goal:</strong> {selectedScenario.user_goal}
        </p>
      )}

      {mode === 'single' ? (
        <div className="eval-form">
          <label className="eval-field">
            <span>Transcript (caller's turn)</span>
            <textarea
              rows={3}
              value={transcript}
              placeholder="e.g. I want to dispute a charge I don't recognize."
              onChange={(e) => setTranscript(e.target.value)}
            />
          </label>
          <label className="eval-field">
            <span>Model name (optional)</span>
            <input
              value={modelName}
              placeholder="e.g. claude-opus-4-8"
              onChange={(e) => setModelName(e.target.value)}
            />
          </label>
          <button
            className="eval-run"
            onClick={runEvaluate}
            disabled={loading || !scenarioId || !transcript.trim()}
          >
            {loading ? 'Evaluating…' : 'Evaluate'}
          </button>
        </div>
      ) : (
        <div className="eval-form">
          {rows.map((r, i) => (
            <div className="cmp-row" key={i}>
              <input
                className="cmp-model-name"
                value={r.model}
                placeholder="Model name"
                onChange={(e) => updateRow(i, { model: e.target.value })}
              />
              <textarea
                rows={2}
                value={r.transcript}
                placeholder="This model's transcript of the audio"
                onChange={(e) => updateRow(i, { transcript: e.target.value })}
              />
              {rows.length > 2 && (
                <button className="cmp-remove" onClick={() => removeRow(i)} title="Remove">
                  ✕
                </button>
              )}
            </div>
          ))}
          <div className="cmp-actions">
            <button className="eval-secondary" onClick={addRow}>
              + Add model
            </button>
            <button
              className="eval-run"
              onClick={runCompare}
              disabled={loading || !scenarioId}
            >
              {loading ? 'Comparing…' : 'Compare'}
            </button>
          </div>
        </div>
      )}

      {error && <p className="eval-error">{error}</p>}

      {mode === 'single' && result && <EvaluationScorePanel result={result} />}
      {mode === 'compare' && comparison && (
        <ModelComparisonPanel comparison={comparison} />
      )}
    </section>
  )
}

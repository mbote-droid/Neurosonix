import type { EvaluationResult } from '../api/evaluation'
import { DIMENSION_LABELS } from '../api/evaluation'

interface Props {
  result: EvaluationResult
}

function scoreColor(score: number): string {
  if (score >= 4) return '#2e9e5b' // green
  if (score >= 3) return '#e0a92e' // amber
  return '#d6564b' // red
}

export default function EvaluationScorePanel({ result }: Props) {
  return (
    <div className="eval-panel">
      <div className="eval-panel-header">
        <div>
          <span className="eval-model">{result.model_name}</span>
          {result.degraded && (
            <span className="eval-degraded" title="Scored without a live LLM">
              degraded
            </span>
          )}
        </div>
        <div className="eval-synth" style={{ color: scoreColor(result.synthesized_score) }}>
          {result.synthesized_score.toFixed(2)}
          <span className="eval-synth-max"> / 5</span>
        </div>
      </div>

      <div className="eval-response">
        <span className="eval-label">Agent reply</span>
        <p>{result.agent_response}</p>
      </div>

      <div className="eval-scores">
        {result.agent_scores.map((s) => (
          <div className="eval-score-row" key={s.dimension}>
            <div className="eval-score-top">
              <span className="eval-dim">{DIMENSION_LABELS[s.dimension]}</span>
              <span className="eval-dim-score">{s.score}/5</span>
            </div>
            <div className="eval-bar">
              <div
                className="eval-bar-fill"
                style={{
                  width: `${(s.score / 5) * 100}%`,
                  background: scoreColor(s.score),
                }}
              />
            </div>
            {s.rationale && <p className="eval-rationale">{s.rationale}</p>}
          </div>
        ))}
      </div>
    </div>
  )
}

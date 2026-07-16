import type { ModelComparison, Dimension } from '../api/evaluation'
import { DIMENSION_LABELS } from '../api/evaluation'

interface Props {
  comparison: ModelComparison
}

const DIMENSIONS: Dimension[] = [
  'task_completion',
  'conversational_naturalness',
  'audio_comprehension',
  'instruction_adherence',
  'technical_clarity',
]

export default function ModelComparisonPanel({ comparison }: Props) {
  if (comparison.entries.length === 0) {
    return <p className="eval-empty">No models to compare.</p>
  }

  return (
    <div className="cmp-panel">
      <table className="cmp-table">
        <thead>
          <tr>
            <th>Dimension</th>
            {comparison.entries.map((e) => (
              <th
                key={e.model_name}
                className={e.model_name === comparison.winner ? 'cmp-winner' : ''}
              >
                {e.model_name}
                {e.model_name === comparison.winner && (
                  <span className="cmp-crown" title="Winner"> 🏆</span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {DIMENSIONS.map((dim) => (
            <tr key={dim}>
              <td className="cmp-dim">{DIMENSION_LABELS[dim]}</td>
              {comparison.entries.map((e) => (
                <td key={e.model_name} className="cmp-cell">
                  {e.per_dimension[dim] != null ? e.per_dimension[dim].toFixed(0) : '—'}
                </td>
              ))}
            </tr>
          ))}
          <tr className="cmp-total-row">
            <td className="cmp-dim">Synthesized</td>
            {comparison.entries.map((e) => (
              <td
                key={e.model_name}
                className={
                  'cmp-cell cmp-total' +
                  (e.model_name === comparison.winner ? ' cmp-winner' : '')
                }
              >
                {e.synthesized_score.toFixed(2)}
              </td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  )
}

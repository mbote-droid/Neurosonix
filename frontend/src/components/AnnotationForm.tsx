import { useState } from 'react'

interface AnnotationFormProps {
  fileId: string
}

export default function AnnotationForm({ fileId }: AnnotationFormProps) {
  const [annotations, setAnnotations] = useState<any[]>([])
  const [formData, setFormData] = useState({
    speaker: 'Speaker 1',
    timestamp_start: 0,
    timestamp_end: 5,
    text: '',
    emotion: 'neutral',
    clarity: 3,
    confidence: 0.8,
    notes: '',
  })
  const [saving, setSaving] = useState(false)

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: name === 'clarity' || name === 'timestamp_start' || name === 'timestamp_end'
        ? Number(value)
        : name === 'confidence'
        ? Number(value)
        : value
    }))
  }

  const handleAddAnnotation = async () => {
    setSaving(true)
    try {
      const response = await fetch(`http://localhost:8000/api/annotate/${fileId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      })

      if (!response.ok) throw new Error('Failed to save annotation')

      setAnnotations([...annotations, formData])
      // Reset form
      setFormData({
        speaker: 'Speaker 1',
        timestamp_start: formData.timestamp_end,
        timestamp_end: formData.timestamp_end + 5,
        text: '',
        emotion: 'neutral',
        clarity: 3,
        confidence: 0.8,
        notes: '',
      })
    } catch (err) {
      alert('Error saving annotation: ' + (err instanceof Error ? err.message : 'Unknown error'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="annotation-section">
      <h2>Step 3: Annotate Audio</h2>

      <div className="annotation-form">
        <div className="form-group">
          <label>Speaker</label>
          <select name="speaker" value={formData.speaker} onChange={handleInputChange}>
            <option>Speaker 1</option>
            <option>Speaker 2</option>
            <option>Speaker 3</option>
            <option>Speaker 4</option>
          </select>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Start (sec)</label>
            <input
              type="number"
              name="timestamp_start"
              value={formData.timestamp_start}
              onChange={handleInputChange}
              step="0.1"
            />
          </div>
          <div className="form-group">
            <label>End (sec)</label>
            <input
              type="number"
              name="timestamp_end"
              value={formData.timestamp_end}
              onChange={handleInputChange}
              step="0.1"
            />
          </div>
        </div>

        <div className="form-group">
          <label>Transcription</label>
          <textarea
            name="text"
            value={formData.text}
            onChange={handleInputChange}
            placeholder="What was said..."
          />
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Emotion</label>
            <select name="emotion" value={formData.emotion} onChange={handleInputChange}>
              <option value="neutral">Neutral</option>
              <option value="calm">Calm</option>
              <option value="excited">Excited</option>
              <option value="sad">Sad</option>
              <option value="angry">Angry</option>
            </select>
          </div>

          <div className="form-group">
            <label>Clarity (1-5)</label>
            <input
              type="range"
              name="clarity"
              min="1"
              max="5"
              value={formData.clarity}
              onChange={handleInputChange}
            />
            <span>{formData.clarity}</span>
          </div>

          <div className="form-group">
            <label>Confidence (0-1)</label>
            <input
              type="number"
              name="confidence"
              min="0"
              max="1"
              step="0.1"
              value={formData.confidence}
              onChange={handleInputChange}
            />
          </div>
        </div>

        <div className="form-group">
          <label>Notes</label>
          <textarea
            name="notes"
            value={formData.notes}
            onChange={handleInputChange}
            placeholder="Optional notes..."
          />
        </div>

        <button onClick={handleAddAnnotation} disabled={saving}>
          {saving ? 'Saving...' : 'Save Annotation'}
        </button>
      </div>

      {annotations.length > 0 && (
        <div className="annotations-list">
          <h3>Saved Annotations ({annotations.length})</h3>
          {annotations.map((anno, idx) => (
            <div key={idx} className="annotation-item">
              <strong>{anno.speaker}</strong> ({anno.timestamp_start.toFixed(1)} - {anno.timestamp_end.toFixed(1)}s)
              <p>{anno.text}</p>
              <small>{anno.emotion} • Clarity: {anno.clarity}/5</small>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

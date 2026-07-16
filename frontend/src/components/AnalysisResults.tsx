interface AnalysisResultsProps {
  data: {
    filename: string
    snr_db: number
    quality: string
    emotion: string
    emotion_confidence: number
    transcription: string
    f1_hz: number | null
    f2_hz: number | null
    duration_sec: number
  }
}

export default function AnalysisResults({ data }: AnalysisResultsProps) {
  const getQualityColor = (quality: string) => {
    switch (quality) {
      case 'excellent':
        return '#10b981'
      case 'usable':
        return '#f59e0b'
      case 'poor':
        return '#ef4444'
      default:
        return '#6b7280'
    }
  }

  return (
    <section className="analysis-section">
      <h2>Step 2: Analysis Results</h2>

      <div className="analysis-grid">
        {/* SNR Traffic Light */}
        <div className="metric-card">
          <h3>Audio Quality</h3>
          <div
            className="traffic-light"
            style={{ backgroundColor: getQualityColor(data.quality) }}
          >
            {data.quality.toUpperCase()}
          </div>
          <p>SNR: {data.snr_db.toFixed(1)} dB</p>
        </div>

        {/* Emotion */}
        <div className="metric-card">
          <h3>Emotion Detected</h3>
          <div className="emotion-badge">{data.emotion}</div>
          <p>Confidence: {(data.emotion_confidence * 100).toFixed(0)}%</p>
        </div>

        {/* Duration */}
        <div className="metric-card">
          <h3>Duration</h3>
          <p className="large-text">{data.duration_sec.toFixed(1)}s</p>
        </div>

        {/* Formants */}
        {data.f1_hz && data.f2_hz && (
          <div className="metric-card">
            <h3>Formants</h3>
            <p>F1: {data.f1_hz.toFixed(0)} Hz</p>
            <p>F2: {data.f2_hz.toFixed(0)} Hz</p>
            <small>Vowel characteristics</small>
          </div>
        )}
      </div>

      {/* Transcription */}
      <div className="transcription-card">
        <h3>Transcription</h3>
        <p className="transcript-text">
          {data.transcription || '[Transcription unavailable]'}
        </p>
      </div>
    </section>
  )
}

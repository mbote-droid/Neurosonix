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
    spectral_centroid_hz: number
    rms_energy: number
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

  const getQualityIcon = (quality: string) => {
    switch (quality) {
      case 'excellent':
        return '✅'
      case 'usable':
        return '⚠️'
      case 'poor':
        return '❌'
      default:
        return '❓'
    }
  }

  const getEmotionIcon = (emotion: string) => {
    const icons: { [key: string]: string } = {
      neutral: '😐',
      calm: '😌',
      excited: '😃',
      sad: '😢',
      angry: '😠'
    }
    return icons[emotion] || '😐'
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
            {getQualityIcon(data.quality)}
          </div>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-light)' }}>
            {data.quality.toUpperCase()}
          </p>
          <p style={{ fontSize: '1.3rem', fontWeight: '600', marginTop: '0.5rem' }}>
            {data.snr_db.toFixed(1)} dB
          </p>
        </div>

        {/* Emotion */}
        <div className="metric-card">
          <h3>Detected Emotion</h3>
          <div style={{ fontSize: '3rem', margin: '1rem 0' }}>
            {getEmotionIcon(data.emotion)}
          </div>
          <div className="emotion-badge">{data.emotion}</div>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-light)', marginTop: '0.5rem' }}>
            Confidence: {(data.emotion_confidence * 100).toFixed(0)}%
          </p>
        </div>

        {/* Duration */}
        <div className="metric-card">
          <h3>Duration</h3>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-light)' }}>Total length</p>
          <div className="large-text">{data.duration_sec.toFixed(1)}s</div>
        </div>

        {/* RMS Energy */}
        <div className="metric-card">
          <h3>Energy Level</h3>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-light)' }}>RMS amplitude</p>
          <div className="large-text">{(data.rms_energy * 1000).toFixed(1)}</div>
        </div>

        {/* Spectral Centroid */}
        <div className="metric-card">
          <h3>Brightness</h3>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-light)' }}>Spectral centroid</p>
          <div className="large-text">{(data.spectral_centroid_hz / 1000).toFixed(1)}k Hz</div>
        </div>

        {/* Formants */}
        {data.f1_hz && data.f2_hz && (
          <div className="metric-card">
            <h3>Formants</h3>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-light)', marginBottom: '0.75rem' }}>
              Vowel characteristics
            </p>
            <p>F1: <strong>{data.f1_hz.toFixed(0)} Hz</strong></p>
            <p>F2: <strong>{data.f2_hz.toFixed(0)} Hz</strong></p>
          </div>
        )}
      </div>

      {/* Transcription */}
      <div className="transcription-card">
        <h3>📝 Transcription</h3>
        <div className="transcript-text">
          {data.transcription || '[Transcription unavailable]'}
        </div>
      </div>

      {/* Metadata */}
      <div style={{ marginTop: '2rem', padding: '1rem', backgroundColor: 'var(--surface-secondary)', borderRadius: '8px', fontSize: '0.85rem', color: 'var(--text-light)' }}>
        <p><strong>File:</strong> {data.filename}</p>
        <p><strong>Sample Rate:</strong> {(data.duration_sec > 0 ? '16000 Hz' : 'N/A')}</p>
      </div>
    </section>
  )
}

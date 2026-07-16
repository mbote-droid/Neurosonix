import { useState, useRef } from 'react'

interface UploadSectionProps {
  onUpload: (file: File) => void
  loading: boolean
  error: string
}

export default function UploadSection({ onUpload, loading, error }: UploadSectionProps) {
  const [dragActive, setDragActive] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    const files = e.dataTransfer.files
    if (files && files[0]) {
      onUpload(files[0])
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files[0]) {
      onUpload(files[0])
    }
  }

  const handleMicRecord = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      alert('🎙️ Microphone access granted! Full recording coming soon.')
      stream.getTracks().forEach(track => track.stop())
    } catch (err) {
      alert('❌ Microphone access denied')
    }
  }

  return (
    <section className="upload-section">
      <h2>Step 1: Upload Audio</h2>

      <div
        className={`drop-zone ${dragActive ? 'active' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <p style={{ fontSize: '3rem', margin: '0.5rem 0' }}>📁</p>
        <p><strong>Drag and drop your audio file here</strong></p>
        <p style={{ margin: '1rem 0' }}>or</p>
        <button onClick={() => fileInputRef.current?.click()} disabled={loading}>
          {loading ? '⏳ Uploading...' : '📂 Browse Files'}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="audio/*"
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />
        <p style={{ fontSize: '0.9rem', marginTop: '1rem', color: 'var(--text-lighter)' }}>
          Supports: WAV, MP3, FLAC (max 5 minutes)
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem' }}>
        <button onClick={handleMicRecord} disabled={loading} className="mic-button">
          🎤 Record from Mic
        </button>
      </div>

      {error && (
        <div className="error-message">
          <span>❌</span>
          <span>{error}</span>
        </div>
      )}
      {loading && (
        <div className="loading">
          Analyzing audio — this may take 10-15 seconds...
        </div>
      )}
    </section>
  )
}

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
      alert('Mic recording not yet implemented. Use file upload for now.')
    } catch (err) {
      alert('Microphone access denied')
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
        <p>Drag and drop your audio file here</p>
        <p>or</p>
        <button onClick={() => fileInputRef.current?.click()} disabled={loading}>
          {loading ? 'Uploading...' : 'Browse Files'}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="audio/*"
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />
      </div>

      <button onClick={handleMicRecord} disabled={loading} className="mic-button">
        🎤 Record from Mic (beta)
      </button>

      {error && <div className="error-message">{error}</div>}
      {loading && <div className="loading">Analyzing audio...</div>}
    </section>
  )
}

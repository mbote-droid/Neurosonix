import { useState } from 'react'
import './App.css'
import UploadSection from './components/UploadSection'
import AnalysisResults from './components/AnalysisResults'
import AnnotationForm from './components/AnnotationForm'
import ExportSection from './components/ExportSection'

interface AudioMetadata {
  file_id: string
  filename: string
  snr_db: number
  quality: string
  emotion: string
  emotion_confidence: number
  transcription: string
  diarization_segments: any[]
  f1_hz: number | null
  f2_hz: number | null
}

function App() {
  const [audioData, setAudioData] = useState<AudioMetadata | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleUpload = async (file: File) => {
    setLoading(true)
    setError('')
    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch('http://localhost:8000/api/audio/upload', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`)
      }

      const data = await response.json()
      setAudioData(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
      console.error('Upload error:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="neurosonix-app">
      <header className="header">
        <h1>NeuroSonix</h1>
        <p>Locale-Agnostic Audio Annotation Pipeline</p>
      </header>

      <main className="main-container">
        {!audioData ? (
          <UploadSection onUpload={handleUpload} loading={loading} error={error} />
        ) : (
          <>
            <AnalysisResults data={audioData} />
            <AnnotationForm fileId={audioData.file_id} />
            <ExportSection fileId={audioData.file_id} />
            <button
              onClick={() => setAudioData(null)}
              className="reset-button"
            >
              Upload Another File
            </button>
          </>
        )}
      </main>

      <footer className="footer">
        <p>NeuroSonix v0.1.0 | Physician-Scientist AI Tools</p>
      </footer>
    </div>
  )
}

export default App

import { useState } from 'react'

interface ExportSectionProps {
  fileId: string
}

export default function ExportSection({ fileId }: ExportSectionProps) {
  const [exporting, setExporting] = useState(false)
  const [exported, setExported] = useState<'json' | 'csv' | null>(null)

  const handleExport = async (format: 'json' | 'csv') => {
    setExporting(true)
    try {
      const response = await fetch(
        `http://localhost:8000/api/annotate/${fileId}/export/${format}`
      )

      if (!response.ok) throw new Error('Export failed')

      const data = await response.json()

      // Create downloadable file
      const content = data.data
      const blob = new Blob([content], { type: format === 'json' ? 'application/json' : 'text/csv' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `annotations_${fileId}.${format}`
      a.click()
      URL.revokeObjectURL(url)

      setExported(format)
      setTimeout(() => setExported(null), 3000)
    } catch (err) {
      alert('❌ Export failed: ' + (err instanceof Error ? err.message : 'Unknown error'))
    } finally {
      setExporting(false)
    }
  }

  return (
    <section className="export-section">
      <h2>Step 4: Export Results</h2>

      <div className="export-buttons">
        <button
          onClick={() => handleExport('json')}
          disabled={exporting}
          className="export-button json"
        >
          {exported === 'json' ? '✅ Downloaded!' : '📄 JSON'}
        </button>
        <button
          onClick={() => handleExport('csv')}
          disabled={exporting}
          className="export-button csv"
        >
          {exported === 'csv' ? '✅ Downloaded!' : '📊 CSV'}
        </button>
      </div>

      <div className="export-info">
        <p>📤 Export your annotations for use in ML pipelines, spreadsheets, or further analysis.</p>
        <p style={{marginTop: '0.75rem', fontSize: '0.85rem', color: 'var(--text-lighter)'}}>
          JSON: Full metadata with nested structure | CSV: Tabular format for spreadsheets
        </p>
      </div>
    </section>
  )
}

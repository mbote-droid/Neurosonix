import { useState } from 'react'

interface ExportSectionProps {
  fileId: string
}

export default function ExportSection({ fileId }: ExportSectionProps) {
  const [exporting, setExporting] = useState(false)

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
    } catch (err) {
      alert('Export failed: ' + (err instanceof Error ? err.message : 'Unknown error'))
    } finally {
      setExporting(false)
    }
  }

  return (
    <section className="export-section">
      <h2>Step 4: Export</h2>

      <div className="export-buttons">
        <button
          onClick={() => handleExport('json')}
          disabled={exporting}
          className="export-button json"
        >
          📄 Export as JSON
        </button>
        <button
          onClick={() => handleExport('csv')}
          disabled={exporting}
          className="export-button csv"
        >
          📊 Export as CSV
        </button>
      </div>

      <p className="export-info">
        Export your annotations for use in ML training or further processing.
      </p>
    </section>
  )
}

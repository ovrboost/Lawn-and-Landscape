import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'

const LABEL = { new: 'New customer', new_property: 'New property', duplicate: 'Already have it', error: 'Problem' }

export default function Import() {
  const [preview, setPreview] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const choose = async (e) => {
    const file = e.target.files[0]
    e.target.value = ''
    if (!file) return
    setBusy(true); setError(''); setResult(null); setPreview(null)
    try {
      const form = new FormData(); form.append('file', file)
      setPreview(await api('/api/import/preview', { method: 'POST', form }))
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }

  const importable = preview ? preview.rows.filter((r) => r.status === 'new' || r.status === 'new_property') : []

  const commit = async () => {
    setBusy(true); setError('')
    try {
      const rows = preview.rows.filter((r) => r.status !== 'error')
      setResult(await api('/api/import/commit', { method: 'POST', body: { rows } }))
      setPreview(null)
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }

  return (
    <>
      <h1>Import customers</h1>
      <section className="card">
        <p>Upload a CSV with a name column and, ideally, email, phone, and address. Nothing is saved until you confirm.</p>
        <a className="btn" href="/api/import/template" download>Download template</a>
        <label className="btn file">Choose CSV file
          <input type="file" accept=".csv,text/csv" onChange={choose} hidden />
        </label>
      </section>
      {busy && <p className="muted">Working…</p>}
      {error && <p className="error">{error}</p>}

      {result && (
        <section className="card ok">
          <strong>Import finished.</strong>
          <p>{result.customers_created} customers and {result.properties_created} properties added; {result.skipped_duplicates} duplicates skipped.</p>
          <Link className="btn primary" to="/customers">View customers</Link>
        </section>
      )}

      {preview && (
        <>
          <div className="counts">
            <span>{preview.counts.customers_created} new customers</span>
            <span>{preview.counts.properties_created} properties</span>
            <span>{preview.counts.skipped_duplicates} duplicates</span>
            <span className={preview.counts.errors ? 'bad' : ''}>{preview.counts.errors} {preview.counts.errors === 1 ? "problem" : "problems"}</span>
          </div>
          <button className="primary wide" disabled={busy || importable.length === 0} onClick={commit}>
            {importable.length === 0 ? 'Nothing new to import' : `Import ${importable.length} rows`}
          </button>
          <ul className="list">
            {preview.rows.map((r) => (
              <li key={r.line} className={`imp ${r.status}`}>
                <div className="row between">
                  <strong>{r.name || '(no name)'}</strong>
                  <span className={`chip ${r.status}`}>{LABEL[r.status]}</span>
                </div>
                <div className="muted small">Line {r.line}{r.email ? ` · ${r.email}` : ''}</div>
                {r.address && <div className="small">{r.address}</div>}
                {r.errors.map((m) => <div key={m} className="error small">{m}</div>)}
                {r.warnings.map((m) => <div key={m} className="warn small">{m}</div>)}
              </li>
            ))}
          </ul>
        </>
      )}
    </>
  )
}

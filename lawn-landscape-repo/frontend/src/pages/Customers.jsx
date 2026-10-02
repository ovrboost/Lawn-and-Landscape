import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'

export default function Customers() {
  const [q, setQ] = useState('')
  const [showInactive, setShowInactive] = useState(false)
  const [rows, setRows] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    const t = setTimeout(() => {
      const qs = new URLSearchParams({ q, include_inactive: showInactive })
      api(`/api/customers?${qs}`).then((r) => { setRows(r); setError('') }).catch((e) => setError(e.message))
    }, 200)
    return () => clearTimeout(t)
  }, [q, showInactive])

  return (
    <>
      <div className="row between">
        <h1>Customers</h1>
        <Link className="btn primary" to="/customers/new">Add</Link>
      </div>
      <input type="search" placeholder="Search name, email, phone, address" value={q} onChange={(e) => setQ(e.target.value)} />
      <label className="check"><input type="checkbox" checked={showInactive} onChange={(e) => setShowInactive(e.target.checked)} /> Show inactive</label>
      {error && <p className="error">{error}</p>}
      {rows === null ? <p className="muted">Loading…</p> : rows.length === 0 ? (
        <p className="muted">{q ? 'No matches.' : 'No customers yet. Add one, or import a CSV.'}</p>
      ) : (
        <ul className="list">
          {rows.map((c) => (
            <li key={c.id}>
              <Link to={`/customers/${c.id}`}>
                <div className="row between">
                  <strong>{c.name}</strong>
                  {!c.active && <span className="chip">inactive</span>}
                </div>
                <div className="muted small">
                  {c.first_address || 'No property yet'}
                  {c.property_count > 1 ? ` + ${c.property_count - 1} more` : ''}
                </div>
                <div className="muted small">{[c.email, c.phone].filter(Boolean).join(' · ')}</div>
              </Link>
            </li>
          ))}
        </ul>
      )}
      <p className="muted small">{rows ? `${rows.length} shown` : ''}</p>
    </>
  )
}

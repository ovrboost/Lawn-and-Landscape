import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api.js'

const blankProp = () => ({
  key: Math.random().toString(36).slice(2), id: null, address: '', billing_mode: 'monthly_flat',
  monthly_rate: '', per_visit_price: '', lot_size_sqft: '', mow_frequency: 'weekly',
  geofence_radius_m: 75, notes: '',
})
const num = (v) => (v === '' || v === null || v === undefined ? null : Number(v))

export default function CustomerForm() {
  const { id } = useParams()
  const nav = useNavigate()
  const [c, setC] = useState({ name: '', email: '', phone: '', billing_address: '', notes: '', active: true })
  const [props, setProps] = useState([blankProp()])
  const [removed, setRemoved] = useState([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [loaded, setLoaded] = useState(!id)

  useEffect(() => {
    if (!id) return
    api(`/api/customers/${id}`).then((d) => {
      setC({ name: d.name, email: d.email, phone: d.phone, billing_address: d.billing_address, notes: d.notes, active: d.active })
      setProps(d.properties.map((p) => ({
        ...p, key: String(p.id), monthly_rate: p.monthly_rate ?? '', per_visit_price: p.per_visit_price ?? '',
        lot_size_sqft: p.lot_size_sqft ?? '',
      })))
      setLoaded(true)
    }).catch((e) => setError(e.message))
  }, [id])

  const setField = (k) => (e) => setC({ ...c, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value })
  const setProp = (key, k, v) => setProps(props.map((p) => (p.key === key ? { ...p, [k]: v } : p)))
  const dropProp = (p) => {
    if (p.id) setRemoved([...removed, p.id])
    setProps(props.filter((x) => x.key !== p.key))
  }

  const propBody = (p) => ({
    address: p.address.trim(), billing_mode: p.billing_mode, monthly_rate: num(p.monthly_rate),
    per_visit_price: num(p.per_visit_price), lot_size_sqft: num(p.lot_size_sqft),
    mow_frequency: p.mow_frequency, geofence_radius_m: Number(p.geofence_radius_m) || 75, notes: p.notes,
  })

  const save = async (e) => {
    e.preventDefault()
    setBusy(true); setError('')
    try {
      const filled = props.filter((p) => p.address.trim())
      if (!id) {
        await api('/api/customers', { method: 'POST', body: { ...c, properties: filled.map(propBody) } })
      } else {
        await api(`/api/customers/${id}`, { method: 'PUT', body: c })
        for (const pid of removed) await api(`/api/properties/${pid}`, { method: 'DELETE' })
        for (const p of filled) {
          if (p.id) await api(`/api/properties/${p.id}`, { method: 'PUT', body: propBody(p) })
          else await api(`/api/customers/${id}/properties`, { method: 'POST', body: propBody(p) })
        }
      }
      nav('/customers')
    } catch (err) { setError(err.message); setBusy(false) }
  }

  const del = async () => {
    if (!window.confirm(`Delete ${c.name} and all their properties? This cannot be undone. Use "inactive" to just hide them.`)) return
    try { await api(`/api/customers/${id}`, { method: 'DELETE' }); nav('/customers') } catch (err) { setError(err.message) }
  }

  if (!loaded) return <p className="muted">{error || 'Loading…'}</p>

  return (
    <form onSubmit={save}>
      <div className="row between">
        <h1>{id ? 'Edit customer' : 'New customer'}</h1>
        <button type="button" className="link" onClick={() => nav(-1)}>Cancel</button>
      </div>
      <section className="card">
        <label>Name<input required value={c.name} onChange={setField('name')} /></label>
        <label>Email<input type="email" inputMode="email" value={c.email} onChange={setField('email')} /></label>
        <label>Phone<input type="tel" value={c.phone} onChange={setField('phone')} /></label>
        <label>Billing address (if different)<input value={c.billing_address} onChange={setField('billing_address')} /></label>
        <label>Notes<textarea rows="2" value={c.notes} onChange={setField('notes')} /></label>
        <label className="check"><input type="checkbox" checked={c.active} onChange={setField('active')} /> Active</label>
      </section>

      <h2>Properties</h2>
      {props.map((p, i) => (
        <section className="card" key={p.key}>
          <div className="row between">
            <strong>Property {i + 1}</strong>
            <button type="button" className="link danger" onClick={() => dropProp(p)}>Remove</button>
          </div>
          <label>Service address<input value={p.address} placeholder="123 Main St, Pacific, MO 63069"
            onChange={(e) => setProp(p.key, 'address', e.target.value)} /></label>
          <label>Billing
            <select value={p.billing_mode} onChange={(e) => setProp(p.key, 'billing_mode', e.target.value)}>
              <option value="monthly_flat">Monthly flat rate</option>
              <option value="per_visit">Price per visit</option>
            </select>
          </label>
          {p.billing_mode === 'monthly_flat' ? (
            <label>Monthly rate ($)<input type="number" inputMode="decimal" step="0.01" min="0" value={p.monthly_rate}
              onChange={(e) => setProp(p.key, 'monthly_rate', e.target.value)} /></label>
          ) : (
            <label>Price per visit ($)<input type="number" inputMode="decimal" step="0.01" min="0" value={p.per_visit_price}
              onChange={(e) => setProp(p.key, 'per_visit_price', e.target.value)} /></label>
          )}
          <div className="grid2">
            <label>Lot size (sq ft)<input type="number" inputMode="numeric" min="0" value={p.lot_size_sqft}
              onChange={(e) => setProp(p.key, 'lot_size_sqft', e.target.value)} /></label>
            <label>Frequency
              <select value={p.mow_frequency} onChange={(e) => setProp(p.key, 'mow_frequency', e.target.value)}>
                <option value="weekly">Weekly</option><option value="biweekly">Every 2 weeks</option>
                <option value="monthly">Monthly</option><option value="as_needed">As needed</option>
              </select>
            </label>
          </div>
          <label>Check-in radius (meters)<input type="number" inputMode="numeric" min="10" max="1000" value={p.geofence_radius_m}
            onChange={(e) => setProp(p.key, 'geofence_radius_m', e.target.value)} /></label>
          <label>Property notes<textarea rows="2" value={p.notes} onChange={(e) => setProp(p.key, 'notes', e.target.value)} /></label>
        </section>
      ))}
      <button type="button" onClick={() => setProps([...props, blankProp()])}>+ Add another property</button>

      {error && <p className="error">{error}</p>}
      <button className="primary wide" disabled={busy}>{busy ? 'Saving…' : 'Save customer'}</button>
      {id && <button type="button" className="link danger" onClick={del}>Delete customer</button>}
    </form>
  )
}

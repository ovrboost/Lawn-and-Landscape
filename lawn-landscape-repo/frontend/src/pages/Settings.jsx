import React, { useEffect, useState } from 'react'
import { api } from '../api.js'

const num = (v) => (v === '' || v === null ? 0 : Number(v))

export default function Settings({ onLogout, onBusinessName }) {
  const [s, setS] = useState(null)
  const [gmailPw, setGmailPw] = useState('')
  const [clearPw, setClearPw] = useState(false)
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')
  const [pw, setPw] = useState({ current_password: '', new_password: '' })
  const [pwMsg, setPwMsg] = useState('')

  useEffect(() => { api('/api/settings').then(setS).catch((e) => setError(e.message)) }, [])
  if (!s) return <p className="muted">{error || 'Loading…'}</p>

  const set = (k) => (e) => setS({ ...s, [k]: e.target.value })

  const save = async (e) => {
    e.preventDefault()
    setMsg(''); setError('')
    const body = {
      business_name: s.business_name, timezone: s.timezone, base_address: s.base_address,
      rate_per_1000_sqft: num(s.rate_per_1000_sqft), travel_charge_per_minute: num(s.travel_charge_per_minute),
      min_visit_price: num(s.min_visit_price), tax_rate_percent: num(s.tax_rate_percent),
      late_fee_type: s.late_fee_type, late_fee_value: num(s.late_fee_value),
      late_fee_grace_days: Math.round(num(s.late_fee_grace_days)), gmail_address: s.gmail_address,
    }
    if (clearPw) body.gmail_app_password = ''
    else if (gmailPw) body.gmail_app_password = gmailPw
    try {
      setS(await api('/api/settings', { method: 'PUT', body }))
      onBusinessName(body.business_name)
      setGmailPw(''); setClearPw(false); setMsg('Saved.')
    } catch (err) { setError(err.message) }
  }

  const changePw = async (e) => {
    e.preventDefault(); setPwMsg('')
    try {
      await api('/api/auth/password', { method: 'POST', body: pw })
      setPw({ current_password: '', new_password: '' }); setPwMsg('Password changed.')
    } catch (err) { setPwMsg(err.message) }
  }

  return (
    <>
      <h1>Settings</h1>
      <form onSubmit={save}>
        <section className="card">
          <h2>Business</h2>
          <label>Business name<input value={s.business_name} onChange={set('business_name')} /></label>
          <label>Timezone<input value={s.timezone} onChange={set('timezone')} /></label>
          <p className="muted small">"The 1st" for monthly billing is decided by this timezone.</p>
          <label>Base address (routes start here)<input value={s.base_address} onChange={set('base_address')} /></label>
        </section>

        <section className="card">
          <h2>Quote pricing</h2>
          <label>Rate per 1,000 sq ft ($)<input type="number" step="0.01" min="0" inputMode="decimal" value={s.rate_per_1000_sqft} onChange={set('rate_per_1000_sqft')} /></label>
          <label>Travel charge per drive minute ($)<input type="number" step="0.01" min="0" inputMode="decimal" value={s.travel_charge_per_minute} onChange={set('travel_charge_per_minute')} /></label>
          <label>Minimum price per visit ($)<input type="number" step="0.01" min="0" inputMode="decimal" value={s.min_visit_price} onChange={set('min_visit_price')} /></label>
        </section>

        <section className="card">
          <h2>Invoices</h2>
          <label>Sales tax rate (%) — 0 keeps tax off<input type="number" step="0.001" min="0" max="30" inputMode="decimal" value={s.tax_rate_percent} onChange={set('tax_rate_percent')} /></label>
          <label>Late fee type
            <select value={s.late_fee_type} onChange={set('late_fee_type')}>
              <option value="flat">Flat amount ($)</option>
              <option value="percent">Percent of balance (%)</option>
            </select>
          </label>
          <label>Late fee {s.late_fee_type === 'flat' ? '($)' : '(%)'}<input type="number" step="0.01" min="0" inputMode="decimal" value={s.late_fee_value} onChange={set('late_fee_value')} /></label>
          <label>Grace days before a late fee<input type="number" min="0" max="365" inputMode="numeric" value={s.late_fee_grace_days} onChange={set('late_fee_grace_days')} /></label>
          <p className="muted small">These are defaults. You can change them any time, and later override per customer or on a draft invoice.</p>
        </section>

        <section className="card">
          <h2>Gmail for invoices</h2>
          <p className="muted small">Not used until billing is built. Use a Gmail app password (needs 2-step verification), not your normal password. It is stored encrypted and never shown again.</p>
          <label>Gmail address<input type="email" inputMode="email" value={s.gmail_address} onChange={set('gmail_address')} /></label>
          <label>App password {s.gmail_password_set && !clearPw && <span className="chip ok">saved</span>}
            <input type="password" autoComplete="off" placeholder={s.gmail_password_set ? 'Leave blank to keep the saved one' : '16-character app password'}
              value={gmailPw} onChange={(e) => { setGmailPw(e.target.value); setClearPw(false) }} />
          </label>
          {s.gmail_password_set && (
            <label className="check"><input type="checkbox" checked={clearPw} onChange={(e) => { setClearPw(e.target.checked); setGmailPw('') }} /> Remove the saved password</label>
          )}
        </section>

        {error && <p className="error">{error}</p>}
        {msg && <p className="okmsg">{msg}</p>}
        <button className="primary wide">Save settings</button>
      </form>

      <form className="card" onSubmit={changePw}>
        <h2>Change app password</h2>
        <label>Current password<input type="password" autoComplete="current-password" value={pw.current_password} onChange={(e) => setPw({ ...pw, current_password: e.target.value })} /></label>
        <label>New password (8+ characters)<input type="password" autoComplete="new-password" value={pw.new_password} onChange={(e) => setPw({ ...pw, new_password: e.target.value })} /></label>
        {pwMsg && <p className="muted">{pwMsg}</p>}
        <button disabled={!pw.current_password || pw.new_password.length < 8}>Change password</button>
      </form>
      <button className="link danger" onClick={onLogout}>Sign out</button>
    </>
  )
}

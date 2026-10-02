import React, { useState } from 'react'
import { api } from '../api.js'

export default function Login({ onDone }) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true); setError('')
    try {
      await api('/api/auth/login', { method: 'POST', body: { password } })
      onDone(await api('/api/auth/me'))
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }

  return (
    <form className="login card" onSubmit={submit}>
      <img src="/icon.svg" alt="" width="64" height="64" />
      <h1>Lawn &amp; Landscape</h1>
      <label>Password
        <input type="password" autoFocus autoComplete="current-password" value={password}
          onChange={(e) => setPassword(e.target.value)} />
      </label>
      {error && <p className="error">{error}</p>}
      <button className="primary" disabled={busy || !password}>{busy ? 'Signing in…' : 'Sign in'}</button>
    </form>
  )
}

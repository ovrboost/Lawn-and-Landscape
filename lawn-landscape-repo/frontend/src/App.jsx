import React, { useEffect, useState } from 'react'
import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { api, setUnauthorizedHandler } from './api.js'
import Login from './pages/Login.jsx'
import Customers from './pages/Customers.jsx'
import CustomerForm from './pages/CustomerForm.jsx'
import Import from './pages/Import.jsx'
import Settings from './pages/Settings.jsx'

export default function App() {
  const [me, setMe] = useState(undefined) // undefined = checking, null = signed out

  useEffect(() => {
    setUnauthorizedHandler(() => setMe(null))
    api('/api/auth/me').then(setMe).catch(() => setMe(null))
  }, [])

  if (me === undefined) return <div className="center muted">Loading…</div>
  if (me === null) return <Login onDone={(m) => setMe(m)} />

  const logout = async () => { await api('/api/auth/logout', { method: 'POST' }).catch(() => {}); setMe(null) }

  return (
    <div className="shell">
      <header className="top">
        <strong>{me.business_name || 'Lawn & Landscape'}</strong>
      </header>
      <main className="page">
        <Routes>
          <Route path="/" element={<Navigate to="/customers" replace />} />
          <Route path="/customers" element={<Customers />} />
          <Route path="/customers/new" element={<CustomerForm />} />
          <Route path="/customers/:id" element={<CustomerForm />} />
          <Route path="/import" element={<Import />} />
          <Route path="/settings" element={<Settings onLogout={logout} onBusinessName={(n) => setMe({ ...me, business_name: n })} />} />
          <Route path="*" element={<Navigate to="/customers" replace />} />
        </Routes>
      </main>
      <nav className="tabs">
        <NavLink to="/customers">Customers</NavLink>
        <NavLink to="/import">Import</NavLink>
        <NavLink to="/settings">Settings</NavLink>
      </nav>
    </div>
  )
}

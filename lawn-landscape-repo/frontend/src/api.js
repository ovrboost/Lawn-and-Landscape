let onUnauthorized = () => {}
export const setUnauthorizedHandler = (fn) => { onUnauthorized = fn }

export async function api(path, { method = 'GET', body, form } = {}) {
  const opts = { method, credentials: 'same-origin', headers: {} }
  if (form) opts.body = form
  else if (body !== undefined) { opts.body = JSON.stringify(body); opts.headers['Content-Type'] = 'application/json' }
  let res
  try { res = await fetch(path, opts) } catch { throw new Error('No connection to the server. Check your signal and try again.') }
  if (res.status === 401 && !path.startsWith('/api/auth/login')) onUnauthorized()
  if (res.status === 204) return null
  const data = await res.json().catch(() => null)
  if (!res.ok) {
    let msg = data?.detail
    if (Array.isArray(msg)) msg = msg.map((d) => `${(d.loc || []).slice(1).join(' ')}: ${d.msg}`).join('; ')
    throw new Error(msg || `Request failed (${res.status})`)
  }
  return data
}

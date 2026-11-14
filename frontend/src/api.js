// Small helpers for talking to the FastAPI backend.
// In development Vite forwards /api to http://127.0.0.1:8000 (see vite.config.js).

// Turn the filters object into a query string.
// Arrays become repeated keys: { state: ['GA', 'TX'] } -> state=GA&state=TX
export function toQuery(params) {
  const qs = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (Array.isArray(value)) value.forEach((v) => qs.append(key, v))
    else if (value !== '' && value !== null && value !== undefined) qs.append(key, value)
  }
  return qs.toString()
}

export async function getJSON(path, params = {}) {
  const query = toQuery(params)
  const res = await fetch(query ? `${path}?${query}` : path)
  if (!res.ok) throw new Error(`${path} returned ${res.status}`)
  return res.json()
}

export const csvUrl = (filters) => `/api/records.csv?${toQuery(filters)}`

// "2026-11-30" -> "Nov 30, 2026"
export function formatDate(iso) {
  if (!iso) return '—'
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

// "2026-11" -> "Nov 2026"
export function formatMonth(ym) {
  const [y, m] = ym.split('-').map(Number)
  return new Date(y, m - 1, 1).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })
}

// 4075.2 -> "1h 7m"
export function formatDuration(seconds) {
  if (seconds == null) return '—'
  const s = Math.round(seconds)
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  if (h) return `${h}h ${m}m`
  if (m) return `${m}m ${s % 60}s`
  return `${s}s`
}

export const formatNumber = (n) => (n ?? 0).toLocaleString('en-US')

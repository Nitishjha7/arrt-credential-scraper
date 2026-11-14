import { formatDate } from '../api'
import { QUERY_LABELS } from '../constants'

// A row of removable chips that says, in words, what the table is showing.
export default function ActiveFilters({ filters, options, onChange, onReset }) {
  const nameOf = (code) => options?.disciplines?.find((d) => d.code === code)?.name ?? code
  const chips = []

  if (filters.q) chips.push({ key: 'q', label: `“${filters.q}”`, clear: { q: '' } })
  if (filters.status) chips.push({ key: 'status', label: filters.status === 'Active' ? 'Registered now' : 'Expired', clear: { status: '' } })
  filters.discipline.forEach((d) =>
    chips.push({ key: `d${d}`, label: nameOf(d), clear: { discipline: filters.discipline.filter((x) => x !== d) } }))
  filters.state.forEach((s) =>
    chips.push({ key: `s${s}`, label: s, clear: { state: filters.state.filter((x) => x !== s) } }))
  if (filters.valid_from || filters.valid_to)
    chips.push({ key: 'v', label: `Valid thru ${formatDate(filters.valid_from) } – ${formatDate(filters.valid_to)}`, clear: { valid_from: '', valid_to: '' } })
  if (filters.ce_end_from || filters.ce_end_to)
    chips.push({ key: 'c', label: `CE ends ${formatDate(filters.ce_end_from)} – ${formatDate(filters.ce_end_to)}`, clear: { ce_end_from: '', ce_end_to: '' } })
  filters.source_query.forEach((q) =>
    chips.push({ key: `q${q}`, label: QUERY_LABELS[q] ?? q, clear: { source_query: filters.source_query.filter((x) => x !== q) } }))

  if (!chips.length) return null

  return (
    <div className="active-filters" aria-label="Active filters">
      <span className="muted">Showing</span>
      {chips.map((c) => (
        <button key={c.key} className="tag" onClick={() => onChange(c.clear)} aria-label={`Remove filter ${c.label}`}>
          {c.label} <span aria-hidden="true">×</span>
        </button>
      ))}
      <button className="link-button" onClick={onReset}>Clear all</button>
    </div>
  )
}

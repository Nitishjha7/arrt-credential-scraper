import { formatMonth, formatNumber } from '../api'

// "Renewal horizon": one bar per month = how many credentials are valid
// until that month. Bars left of "today" are expired, right are active.
// Clicking a bar filters the table to that month (click again to clear).

const H = 120 // chart height in px

function monthRange(ym) {
  const [y, m] = ym.split('-').map(Number)
  const last = new Date(y, m, 0).getDate()
  const mm = String(m).padStart(2, '0')
  return [`${y}-${mm}-01`, `${y}-${mm}-${last}`]
}

// Fill the gaps so the axis is a real timeline: months with no one get a 0 bar
function fillMonths(rows) {
  if (!rows.length) return []
  const counts = Object.fromEntries(rows.map((r) => [r.month, r.count]))
  let [y, m] = rows[0].month.split('-').map(Number)
  const last = rows[rows.length - 1].month
  const out = []
  for (;;) {
    const key = `${y}-${String(m).padStart(2, '0')}`
    out.push({ month: key, count: counts[key] ?? 0 })
    if (key >= last) break
    m += 1
    if (m > 12) { m = 1; y += 1 }
  }
  return out
}

export default function RenewalHorizon({ months: rawMonths, selected, onSelect }) {
  const months = fillMonths(rawMonths)
  if (!months.length) return null

  const today = new Date()
  const thisMonth = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`
  const max = Math.max(...months.map((m) => m.count))
  const selectedMonth = selected.from && selected.to && selected.from.slice(0, 7) === selected.to.slice(0, 7)
    ? selected.from.slice(0, 7)
    : null

  // Label only the first month of each year (plus the first bar) to keep the axis calm
  const showLabel = (m, i) => i === 0 || m.month.endsWith('-01')

  return (
    <section className="horizon" aria-label="Valid-thru dates by month">
      <div className="horizon__head">
        <h2>Renewal horizon</h2>
        <p>How many registrations run until each month. Select a month to list those people.</p>
        {selectedMonth && (
          <button className="link-button" onClick={() => onSelect('', '')}>
            Show all months
          </button>
        )}
      </div>

      <div className="horizon__scroll">
        <div className="horizon__bars" style={{ height: H + 28 }}>
          {months.map((m, i) => {
            const past = m.month < thisMonth
            const isNow = m.month === thisMonth
            const isSelected = m.month === selectedMonth
            const [from, to] = monthRange(m.month)
            return (
              <button
                key={m.month}
                className={`bar ${past ? 'bar--past' : ''} ${isSelected ? 'is-on' : ''} ${selectedMonth && !isSelected ? 'is-dim' : ''}`}
                disabled={m.count === 0}
                onClick={() => (isSelected ? onSelect('', '') : onSelect(from, to))}
                aria-pressed={isSelected}
                aria-label={`${formatMonth(m.month)}: ${formatNumber(m.count)} registrations`}
                title={`${formatMonth(m.month)} · ${formatNumber(m.count)}`}
              >
                {isNow && <span className="bar__today">today</span>}
                <span className="bar__fill" style={{ height: m.count ? Math.max(2, (m.count / max) * H) : 0 }} />
                <span className="bar__label">{showLabel(m, i) ? m.month.slice(0, 4) : ''}</span>
              </button>
            )
          })}
        </div>
      </div>

      <div className="horizon__legend">
        <span><i className="swatch swatch--past" /> expired</span>
        <span><i className="swatch" /> currently registered</span>
      </div>
    </section>
  )
}

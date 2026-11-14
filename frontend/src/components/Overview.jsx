import { formatNumber } from '../api'

// Headline numbers for whatever is currently filtered.
// The Active / Expired figures double as filter buttons.
export default function Overview({ stats, onStatus, activeStatus }) {
  if (!stats) return <section className="overview overview--loading" aria-busy="true" />

  const { total, active, expired, expiring_90_days: soon, top_states: states, disciplines } = stats
  const known = active + expired
  const activeShare = known ? (active / known) * 100 : 0

  return (
    <section className="overview" aria-label="Summary">
      <div className="figures">
        <div className="figure">
          <span className="figure__value">{formatNumber(total)}</span>
          <span className="figure__label">technologists in view</span>
        </div>
        <button
          className={`figure figure--button figure--active ${activeStatus === 'Active' ? 'is-on' : ''}`}
          onClick={() => onStatus(activeStatus === 'Active' ? '' : 'Active')}
          aria-pressed={activeStatus === 'Active'}
        >
          <span className="figure__value">{formatNumber(active)}</span>
          <span className="figure__label">registered now</span>
        </button>
        <button
          className={`figure figure--button figure--expired ${activeStatus === 'Expired' ? 'is-on' : ''}`}
          onClick={() => onStatus(activeStatus === 'Expired' ? '' : 'Expired')}
          aria-pressed={activeStatus === 'Expired'}
        >
          <span className="figure__value">{formatNumber(expired)}</span>
          <span className="figure__label">past their valid-thru date</span>
        </button>
        <div className="figure">
          <span className="figure__value">{formatNumber(soon)}</span>
          <span className="figure__label">renew within 90 days</span>
        </div>
      </div>

      <p className="coverage">
        Full details (valid thru, CE biennium, CQR) are loaded for{' '}
        <strong>{formatNumber(stats.with_details)}</strong> of {formatNumber(total)} people in view.
      </p>

      <div className="share" aria-label={`${activeShare.toFixed(0)}% currently registered`}>
        <div className="share__bar"><span style={{ width: `${activeShare}%` }} /></div>
        <span className="share__text">{activeShare.toFixed(0)}% of people with details are registered now</span>
      </div>

      <div className="breakdowns">
        <Breakdown title="Top states" rows={states.map((s) => ({ key: s.state, count: s.count }))} />
        <Breakdown title="Disciplines" rows={disciplines.slice(0, 8).map((d) => ({ key: d.code, count: d.count }))} />
      </div>
    </section>
  )
}

function Breakdown({ title, rows }) {
  const max = Math.max(1, ...rows.map((r) => r.count))
  return (
    <div className="breakdown">
      <h3>{title}</h3>
      {rows.length === 0 && <p className="muted">No data for these filters.</p>}
      <ol>
        {rows.map((r) => (
          <li key={r.key}>
            <span className="breakdown__key">{r.key}</span>
            <span className="breakdown__bar"><span style={{ width: `${(r.count / max) * 100}%` }} /></span>
            <span className="breakdown__count">{formatNumber(r.count)}</span>
          </li>
        ))}
      </ol>
    </div>
  )
}

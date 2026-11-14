import { useState } from 'react'
import { QUERY_LABELS } from '../constants'

// Toggle a value in/out of an array: ['GA'] + 'TX' -> ['GA', 'TX']
const toggle = (list, value) => (list.includes(value) ? list.filter((v) => v !== value) : [...list, value])

export default function FilterPanel({ open, filters, options, onChange, onReset, activeCount }) {
  const [stateSearch, setStateSearch] = useState('')
  const states = (options?.states ?? []).filter((s) => s.toLowerCase().includes(stateSearch.toLowerCase()))

  return (
    <aside className={`filters ${open ? 'filters--open' : ''}`} aria-label="Filters">
      <div className="filters__head">
        <h2>Filters</h2>
        {activeCount > 0 && (
          <button className="link-button" onClick={onReset}>Clear all</button>
        )}
      </div>


      <fieldset className="field">
        <legend className="field__label">Registration</legend>
        <div className="segmented" role="radiogroup">
          {[['', 'All'], ['Active', 'Active'], ['Expired', 'Expired']].map(([value, label]) => (
            <button
              key={label}
              role="radio"
              aria-checked={filters.status === value}
              className={filters.status === value ? 'is-on' : ''}
              onClick={() => onChange({ status: value })}
            >
              {label}
            </button>
          ))}
        </div>
      </fieldset>

      <fieldset className="field">
        <legend className="field__label">Discipline</legend>
        <div className="chips">
          {(options?.disciplines ?? []).map((d) => (
            <button
              key={d.code}
              className={`chip ${filters.discipline.includes(d.code) ? 'is-on' : ''}`}
              aria-pressed={filters.discipline.includes(d.code)}
              title={d.name}
              onClick={() => onChange({ discipline: toggle(filters.discipline, d.code) })}
            >
              <b>{d.code}</b> {d.name !== d.code && <span>{d.name}</span>}
            </button>
          ))}
        </div>
      </fieldset>

      <fieldset className="field">
        <legend className="field__label">Valid thru</legend>
        <div className="range">
          <input type="date" aria-label="Valid thru from" value={filters.valid_from}
            onChange={(e) => onChange({ valid_from: e.target.value })} />
          <span>to</span>
          <input type="date" aria-label="Valid thru to" value={filters.valid_to}
            onChange={(e) => onChange({ valid_to: e.target.value })} />
        </div>
      </fieldset>

      <fieldset className="field">
        <legend className="field__label">CE biennium ends</legend>
        <div className="range">
          <input type="date" aria-label="CE biennium ends from" value={filters.ce_end_from}
            onChange={(e) => onChange({ ce_end_from: e.target.value })} />
          <span>to</span>
          <input type="date" aria-label="CE biennium ends to" value={filters.ce_end_to}
            onChange={(e) => onChange({ ce_end_to: e.target.value })} />
        </div>
      </fieldset>

      <fieldset className="field">
        <legend className="field__label">
          State {filters.state.length > 0 && <em>{filters.state.length} selected</em>}
        </legend>
        <input type="search" placeholder="Find a state" value={stateSearch}
          onChange={(e) => setStateSearch(e.target.value)} />
        <div className="state-grid">
          {states.map((s) => (
            <button
              key={s}
              className={`chip chip--compact ${filters.state.includes(s) ? 'is-on' : ''}`}
              aria-pressed={filters.state.includes(s)}
              onClick={() => onChange({ state: toggle(filters.state, s) })}
            >
              {s}
            </button>
          ))}
        </div>
      </fieldset>

      <fieldset className="field">
        <legend className="field__label">Scraped by search</legend>
        <div className="chips">
          {(options?.source_queries ?? []).map((q) => (
            <button
              key={q}
              className={`chip ${filters.source_query.includes(q) ? 'is-on' : ''}`}
              aria-pressed={filters.source_query.includes(q)}
              onClick={() => onChange({ source_query: toggle(filters.source_query, q) })}
            >
              {QUERY_LABELS[q] ?? q}
            </button>
          ))}
        </div>
      </fieldset>
    </aside>
  )
}

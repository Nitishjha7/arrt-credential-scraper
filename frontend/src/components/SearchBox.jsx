import { useEffect, useId, useRef, useState } from 'react'
import { formatNumber, getJSON } from '../api'

// Search with autocomplete.
// - Typing filters the table (after a short pause).
// - Suggestions show matching people (opens their record) and cities (filters by city).
// - Keyboard: ↑ ↓ to move, Enter to pick, Esc to close.
export default function SearchBox({ value, onSearch, onOpenPerson }) {
  const [text, setText] = useState(value)
  const [suggestions, setSuggestions] = useState({ people: [], cities: [] })
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(-1)
  const listId = useId()
  const boxRef = useRef(null)

  useEffect(() => setText(value), [value])

  // Fetch suggestions while typing (debounced)
  useEffect(() => {
    if (text.trim().length < 2) { setSuggestions({ people: [], cities: [] }); return }
    const t = setTimeout(() => {
      getJSON('/api/suggest', { q: text.trim() }).then((s) => { setSuggestions(s); setActive(-1) }).catch(() => {})
    }, 180)
    return () => clearTimeout(t)
  }, [text])

  // Typing also filters the table, after a slightly longer pause
  useEffect(() => {
    const t = setTimeout(() => text !== value && onSearch(text), 400)
    return () => clearTimeout(t)
  }, [text]) // eslint-disable-line react-hooks/exhaustive-deps

  // Close when clicking outside
  useEffect(() => {
    const onClick = (e) => !boxRef.current?.contains(e.target) && setOpen(false)
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [])

  const options = [
    ...suggestions.people.map((p) => ({ kind: 'person', key: `p${p.id}`, ...p })),
    ...suggestions.cities.map((c) => ({ kind: 'city', key: `c${c.city}${c.state}`, ...c })),
  ]

  const choose = (o) => {
    setOpen(false)
    if (o.kind === 'person') onOpenPerson(o.id)
    else { setText(o.city); onSearch(o.city) }
  }

  const onKeyDown = (e) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setOpen(true); setActive((i) => Math.min(i + 1, options.length - 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive((i) => Math.max(i - 1, -1)) }
    else if (e.key === 'Enter') {
      if (open && active >= 0) { e.preventDefault(); choose(options[active]) }
      else { setOpen(false); onSearch(text) }
    } else if (e.key === 'Escape') setOpen(false)
  }

  const showList = open && options.length > 0

  return (
    <div className="search" ref={boxRef}>
      <svg className="search__icon" viewBox="0 0 20 20" aria-hidden="true">
        <circle cx="8.5" cy="8.5" r="5.5" fill="none" stroke="currentColor" strokeWidth="1.8" />
        <path d="M13 13l4.5 4.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      </svg>
      <input
        type="search"
        role="combobox"
        aria-expanded={showList}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={active >= 0 ? `${listId}-${active}` : undefined}
        aria-label="Search by name or city"
        placeholder="Search by name or city"
        value={text}
        onChange={(e) => { setText(e.target.value); setOpen(true) }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
      />
      {text && (
        <button className="search__clear" aria-label="Clear search" onClick={() => { setText(''); onSearch('') }}>×</button>
      )}

      {showList && (
        <ul className="suggest" id={listId} role="listbox">
          {options.map((o, i) => [
            i === 0 && o.kind === 'person' && <li key="gp" className="suggest__group" role="presentation">People</li>,
            o.kind === 'city' && i === suggestions.people.length &&
              <li key="gc" className="suggest__group" role="presentation">Cities</li>,
            <li
              key={o.key}
              id={`${listId}-${i}`}
              role="option"
              aria-selected={i === active}
              className={`suggest__item ${i === active ? 'is-active' : ''}`}
              onMouseDown={(e) => { e.preventDefault(); choose(o) }}
              onMouseEnter={() => setActive(i)}
            >
              {o.kind === 'person' ? (
                <>
                  <span className="suggest__main">{o.name}</span>
                  <span className="suggest__meta">{o.place}</span>
                </>
              ) : (
                <>
                  <span className="suggest__main">{o.city}, {o.state}</span>
                  <span className="suggest__meta">{formatNumber(o.count)} {o.count === 1 ? 'person' : 'people'}</span>
                </>
              )}
            </li>,
          ])}
        </ul>
      )}
    </div>
  )
}

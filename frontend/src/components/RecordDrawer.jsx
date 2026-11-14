import { useEffect, useRef, useState } from 'react'
import { formatDate, getJSON } from '../api'
import { StatusPill } from './RecordsTable'

// Side panel with one person's full record - the same facts as the
// "View Details" popup on arrt.org, laid out as a verification slip.
export default function RecordDrawer({ id, onClose }) {
  const [record, setRecord] = useState(null)
  const closeRef = useRef(null)

  useEffect(() => {
    if (!id) return
    setRecord(null)
    getJSON(`/api/records/${id}`).then(setRecord).catch(() => setRecord(false))
    closeRef.current?.focus()
  }, [id])

  // Esc closes the drawer
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  if (!id) return null

  return (
    <>
      <div className="scrim" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-modal="true" aria-label="Credential details">
        <button ref={closeRef} className="drawer__close" onClick={onClose} aria-label="Close details">×</button>

        {record === null && <p className="muted">Loading…</p>}
        {record === false && <p>This record couldn't be loaded. Close the panel and try again.</p>}

        {record && (
          <div className="slip">
            <div className="slip__top">
              <StatusPill status={record.status} />
              <h2>{record.full_name}</h2>
              <p className="slip__credential">{record.credential_string}</p>
            </div>

            <dl className="slip__facts">
              <dt>City, state, zip</dt>
              <dd>{[record.city, record.state].filter(Boolean).join(', ')} {record.zip_code}</dd>
              <dt>Country</dt>
              <dd>{record.country ?? '—'}</dd>
              <dt>Valid thru</dt>
              <dd className="num">{record.valid_thru ?? '—'}</dd>
              <dt>CE biennium</dt>
              <dd className="num">
                {record.ce_start_date ? `${formatDate(record.ce_start_date)} – ${formatDate(record.ce_end_date)}` : '—'}
              </dd>
            </dl>

            <h3>Disciplines</h3>
            {record.credential_description.length ? (
              <ul className="slip__list">
                {record.credential_description.map((d) => (
                  <li key={d.code}><span className="code">{d.code}</span> {d.name}</li>
                ))}
              </ul>
            ) : <p className="muted">Not listed.</p>}

            <h3>CQR compliance periods</h3>
            {record.cqr_periods.length ? (
              <ul className="slip__list">
                {record.cqr_periods.map((p) => (
                  <li key={p.discipline + p.start}>
                    {p.discipline}
                    <span className="num muted"> {formatDate(p.start)} – {formatDate(p.end)}</span>
                  </li>
                ))}
              </ul>
            ) : <p className="muted">None on file.</p>}

            {!record.details_fetched && (
              <p className="notice">Details for this person weren't fetched yet; only the search-table columns are shown.</p>
            )}

            <p className="slip__source">
              Source: ARRT Verify Credentials. Scraped by the “{record.source_query}” search.
            </p>
          </div>
        )}
      </aside>
    </>
  )
}

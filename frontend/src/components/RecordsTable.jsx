import { formatDate, formatNumber } from '../api'

const COLUMNS = [
  { key: 'name', label: 'Name', sortable: true },
  { key: 'city', label: 'City', sortable: true },
  { key: 'state', label: 'State', sortable: true },
  { key: 'credential', label: 'Credential', sortable: false },
  { key: 'valid_thru', label: 'Valid thru', sortable: true },
  { key: 'ce_end', label: 'CE biennium ends', sortable: true },
]

export function StatusPill({ status }) {
  const label = { Active: 'Registered', Expired: 'Expired', Unknown: 'No details' }[status]
  return <span className={`pill pill--${status.toLowerCase()}`}>{label}</span>
}

export default function RecordsTable({ data, sort, onSort, page, onPage, pageSize, onPageSize, onOpen, selectedId }) {
  if (!data) return <section className="records" aria-busy="true"><p className="muted">Loading records…</p></section>

  const { items, total, pages } = data
  const first = total ? (page - 1) * pageSize + 1 : 0
  const last = Math.min(page * pageSize, total)

  return (
    <section className="records" aria-label="Records">
      <div className="records__head">
        <h2>Records</h2>
        <span className="muted">
          {total ? `${formatNumber(first)}–${formatNumber(last)} of ${formatNumber(total)}` : 'No matches'}
        </span>
      </div>

      {total === 0 ? (
        <p className="empty">Nobody matches these filters. Remove one to widen the search.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                {COLUMNS.map((c) => (
                  <th key={c.key} aria-sort={sort.by === c.key ? (sort.order === 'asc' ? 'ascending' : 'descending') : undefined}>
                    {c.sortable ? (
                      <button className="sort" onClick={() => onSort(c.key)}>
                        {c.label}
                        <span className="sort__arrow" aria-hidden="true">
                          {sort.by === c.key ? (sort.order === 'asc' ? '▲' : '▼') : ''}
                        </span>
                      </button>
                    ) : c.label}
                  </th>
                ))}
                <th><span className="visually-hidden">Status</span></th>
              </tr>
            </thead>
            <tbody>
              {items.map((r) => (
                <tr
                  key={r.id}
                  className={selectedId === r.id ? 'is-selected' : ''}
                  onClick={() => onOpen(r.id)}
                >
                  <td>
                    <button className="name-link" onClick={(e) => { e.stopPropagation(); onOpen(r.id) }}>
                      {r.full_name}
                    </button>
                  </td>
                  <td>{r.city}</td>
                  <td>{r.state}</td>
                  <td>
                    <span className="codes">
                      {r.disciplines.map((d) => <span key={d} className="code">{d}</span>)}
                    </span>
                  </td>
                  <td className="num">{r.valid_thru ?? '—'}</td>
                  <td className="num">{formatDate(r.ce_end_date)}</td>
                  <td><StatusPill status={r.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <nav className="pager" aria-label="Pages">
        <label>
          Rows
          <select value={pageSize} onChange={(e) => onPageSize(Number(e.target.value))}>
            {[25, 50, 100].map((n) => <option key={n}>{n}</option>)}
          </select>
        </label>
        <div className="pager__steps">
          <button className="button button--ghost" disabled={page <= 1} onClick={() => onPage(page - 1)}>Previous</button>
          <span>Page {page} of {formatNumber(pages)}</span>
          <button className="button button--ghost" disabled={page >= pages} onClick={() => onPage(page + 1)}>Next</button>
        </div>
      </nav>
    </section>
  )
}

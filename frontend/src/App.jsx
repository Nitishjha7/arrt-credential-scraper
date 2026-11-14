import { useEffect, useState } from 'react'
import { csvUrl, getJSON } from './api'
import FilterPanel from './components/FilterPanel'
import Overview from './components/Overview'
import RenewalHorizon from './components/RenewalHorizon'
import RecordsTable from './components/RecordsTable'
import RecordDrawer from './components/RecordDrawer'
import SearchBox from './components/SearchBox'
import { EMPTY_FILTERS } from './constants'
import ActiveFilters from './components/ActiveFilters'

export default function App() {
  const [filters, setFilters] = useState(EMPTY_FILTERS)
  const [sort, setSort] = useState({ by: 'name', order: 'asc' })
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)

  const [records, setRecords] = useState(null)
  const [stats, setStats] = useState(null)
  const [options, setOptions] = useState(null)
  const [selectedId, setSelectedId] = useState(null)
  const [error, setError] = useState(null)
  const [filtersOpen, setFiltersOpen] = useState(false) // mobile only

  // Changing a filter always goes back to page 1
  const updateFilters = (patch) => {
    setFilters((f) => ({ ...f, ...patch }))
    setPage(1)
  }

  // Dropdown values and last scrape timings: load once
  useEffect(() => {
    getJSON('/api/filters').then(setOptions).catch((e) => setError(e.message))
  }, [])

  // Stat strip + chart follow the filters
  useEffect(() => {
    getJSON('/api/stats', filters).then(setStats).catch((e) => setError(e.message))
  }, [filters])

  // Table rows follow filters, sorting and paging
  useEffect(() => {
    let cancelled = false
    getJSON('/api/records', { ...filters, sort: sort.by, order: sort.order, page, page_size: pageSize })
      .then((data) => !cancelled && setRecords(data))
      .catch((e) => !cancelled && setError(e.message))
    return () => { cancelled = true } // ignore slow responses for old filters
  }, [filters, sort, page, pageSize])

  const activeFilterCount = Object.entries(filters).filter(([, v]) => (Array.isArray(v) ? v.length : v)).length

  return (
    <div className="app">
      <header className="masthead">
        <div className="masthead__title">
          <span className="mark" aria-hidden="true">
            <svg viewBox="0 0 28 28"><rect x="3" y="5" width="22" height="18" rx="2.5" fill="none" stroke="currentColor" strokeWidth="1.6"/><path d="M7 17l4-5 3.5 3.5L19 10l2 3" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/><circle cx="19.5" cy="9.5" r="1.4" fill="currentColor"/></svg>
          </span>
          <div>
            <h1>Credential&nbsp;Registry</h1>
            <p>
              Medical imaging &amp; radiation therapy professionals ·{' '}
              <a href="https://www.arrt.org/pages/verify-credentials" target="_blank" rel="noreferrer">ARRT directory</a>
            </p>
          </div>
        </div>
        <SearchBox
          value={filters.q}
          onSearch={(q) => updateFilters({ q })}
          onOpenPerson={setSelectedId}
        />
        <div className="masthead__actions">
          <button className="button button--ghost filters-toggle" onClick={() => setFiltersOpen((o) => !o)}>
            Filters{activeFilterCount ? ` (${activeFilterCount})` : ''}
          </button>
          <a className="button" href={csvUrl(filters)} download>Download CSV</a>
        </div>
      </header>

      {error && (
        <div className="notice" role="alert">
          Couldn't reach the API ({error}). Start it with <code>uvicorn backend.main:app</code> and reload.
        </div>
      )}

      <div className="layout">
        <FilterPanel
          open={filtersOpen}
          filters={filters}
          options={options}
          onChange={updateFilters}
          onReset={() => { setFilters(EMPTY_FILTERS); setPage(1) }}
          activeCount={activeFilterCount}
        />

        <main className="main">
          <Overview stats={stats} onStatus={(status) => updateFilters({ status })} activeStatus={filters.status} />
          <RenewalHorizon
            months={stats?.valid_thru_by_month ?? []}
            selected={{ from: filters.valid_from, to: filters.valid_to }}
            onSelect={(from, to) => updateFilters({ valid_from: from, valid_to: to })}
          />
          <ActiveFilters filters={filters} options={options} onChange={updateFilters} onReset={() => { setFilters(EMPTY_FILTERS); setPage(1) }} />
          <RecordsTable
            data={records}
            sort={sort}
            onSort={(by) => setSort((s) => ({ by, order: s.by === by && s.order === 'asc' ? 'desc' : 'asc' }))}
            page={page}
            onPage={setPage}
            pageSize={pageSize}
            onPageSize={(n) => { setPageSize(n); setPage(1) }}
            onOpen={setSelectedId}
            selectedId={selectedId}
          />
        </main>
      </div>

      <RecordDrawer id={selectedId} onClose={() => setSelectedId(null)} />
    </div>
  )
}

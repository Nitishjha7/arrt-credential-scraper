// Shared constants, kept out of component files so React Fast Refresh stays happy.

export const EMPTY_FILTERS = {
  q: '',
  state: [],
  discipline: [],
  status: '',
  valid_from: '',
  valid_to: '',
  ce_end_from: '',
  ce_end_to: '',
  source_query: [],
}

// Friendly labels for the scraper's query codes (see scraper/config.py).
export const QUERY_LABELS = {
  first_a: 'First name A…',
  first_b: 'First name B…',
  first_c: 'First name C…',
  first_d: 'First name D…',
  last_sm: 'Last name Sm…',
  last_pa: 'Last name Pa…',
  mix_j_jo: 'J… Jo…',
}

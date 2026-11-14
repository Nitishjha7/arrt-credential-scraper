"""
Turn the site's HTML into Python dicts.

Both parsers were written against real responses saved by the recon run
(data/inspect/search_response.html and 13_POST_GetDisplayDetails.txt).

Search response  -> one <table id="grid"> with ALL rows (paging is done in
                    the browser by DataTables, so one request = every row).
Details response -> a <table class="table-condensed"> of label/value rows,
                    followed by a "Credential Description" table.
"""

import hashlib
import re

from bs4 import BeautifulSoup

from . import clean

DETAIL_KEY_RE = re.compile(r"showDetails\(\s*this\s*,\s*'([^']+)'")


def _text(el) -> str:
    """All text inside an element, whitespace squashed: '  11/2026 \\n ' -> '11/2026'."""
    return " ".join(el.get_text(" ").split()) if el else ""


def person_key(full_name: str, city: str, state: str, credential: str) -> str:
    """Stable id for de-duplication (the site's own key changes per search)."""
    raw = "|".join(x.strip().lower() for x in (full_name, city, state, credential))
    return hashlib.sha1(raw.encode()).hexdigest()


# --------------------------------------------------------------------------
# Search results
# --------------------------------------------------------------------------
def parse_search(html: str) -> list[dict]:
    """
    Returns one dict per table row:
    {full_name, city, state, credential_string, detail_key, person_key}
    """
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for tr in soup.select("#grid tbody tr"):
        tds = tr.find_all("td")
        if len(tds) < 5:
            continue
        name, city, state, credential = (_text(td) for td in tds[:4])
        m = DETAIL_KEY_RE.search(str(tds[4]))
        rows.append({
            "full_name": name,
            "city": city,
            "state": state,
            "credential_string": credential,
            "detail_key": m.group(1) if m else None,
            "person_key": person_key(name, city, state, credential),
        })
    return rows


# --------------------------------------------------------------------------
# "View Details" popup
# --------------------------------------------------------------------------
def parse_details(html: str) -> dict:
    """
    Returns the cleaned fields for the `credentials` table, plus
    `raw_details`: every label/value exactly as the site showed it.
    """
    soup = BeautifulSoup(html, "html.parser")
    raw: dict = {}

    # 1) Main label/value table. Only its *direct* rows - the CQR cell
    #    contains a nested table we read separately below.
    main = soup.select_one("table.table-condensed")
    cqr_cell = None
    if main:
        for tr in main.find_all("tr", recursive=False) or main.select(":scope > tbody > tr"):
            th, td = tr.find("th"), tr.find("td")
            if not th or not td:
                continue
            label = _text(th)
            raw[label] = _text(td)
            if label.lower().startswith("cqr"):
                cqr_cell = td

    # 2) "Credential Description" table: (R) Radiography, (CT) ...
    description_lines = []
    heading = soup.find("b", string=re.compile("Credential Description", re.I))
    if heading:
        table = heading.find_next("table")
        for tr in table.find_all("tr") if table else []:
            description_lines.append(_text(tr))
    if description_lines:
        raw["Credential Description"] = description_lines

    # 3) Clean values
    city_state_zip = raw.get("City, State, Zip", "")
    zip_match = re.search(r"\b(\d{5}(?:-\d{4})?)\s*$", city_state_zip)
    ce_start, ce_end = clean.parse_date_range(raw.get("CE Biennium"))

    return {
        "zip_code": zip_match.group(1) if zip_match else None,
        "country": raw.get("Country"),
        "valid_thru_raw": raw.get("Valid Thru"),
        "valid_thru_date": clean.parse_valid_thru(raw.get("Valid Thru")),
        "ce_biennium_raw": raw.get("CE Biennium"),
        "ce_start_date": ce_start,
        "ce_end_date": ce_end,
        "cqr_periods": clean.parse_cqr(_text(cqr_cell)) if cqr_cell else None,
        "credential_description": clean.parse_description(description_lines),
        "raw_details": raw,
    }

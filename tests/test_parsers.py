"""
Parser tests against REAL responses saved by the recon run.

Using the actual HTML ARRT returned (data/inspect/) means these tests fail
the moment the site's markup changes, which is exactly when the scraper
would silently break.
"""

from pathlib import Path

import pytest

from scraper import parsers

INSPECT = Path(__file__).resolve().parent.parent / "data" / "inspect"
SEARCH_HTML = INSPECT / "search_response.html"
DETAILS_HTML = INSPECT / "13_POST_GetDisplayDetails.txt"

pytestmark = pytest.mark.skipif(
    not SEARCH_HTML.exists(), reason="recon fixtures not present (run scraper.recon)"
)


@pytest.fixture(scope="module")
def search_rows():
    return parsers.parse_search(SEARCH_HTML.read_text(encoding="utf-8"))


def test_search_finds_rows(search_rows):
    assert len(search_rows) > 10


def test_every_row_has_name_and_detail_key(search_rows):
    for r in search_rows:
        assert r["full_name"]
        assert r["detail_key"]          # needed to fetch details later


def test_person_keys_are_unique(search_rows):
    keys = [r["person_key"] for r in search_rows]
    assert len(keys) == len(set(keys))


def test_first_row_fields(search_rows):
    first = search_rows[0]
    assert first["full_name"] == "A'liyah A Adams"
    assert first["state"] == "GA"
    assert "ARRT" in first["credential_string"]


def test_person_key_is_stable():
    a = parsers.person_key("A B", "Albany", "GA", "R.T.(R)(ARRT)")
    b = parsers.person_key("A B", "Albany", "GA", "R.T.(R)(ARRT)")
    assert a == b and len(a) == 40


def test_details_parse():
    data = parsers.parse_details(DETAILS_HTML.read_text(encoding="utf-8"))
    assert data["zip_code"] == "31701"
    assert data["country"] == "U.S.A."
    assert data["valid_thru_raw"] == "11/2026"
    assert data["ce_start_date"].isoformat() == "2025-11-01"
    assert data["cqr_periods"][0]["discipline"] == "Radiography"
    assert {"code": "R", "name": "Radiography"} in data["credential_description"]
    assert data["raw_details"]["Name"] == "A'liyah A Adams"


def test_lookup_cap_message_is_not_data():
    """The 'maximum number of lookups' page must parse as empty, never as a record."""
    capped = (
        '<div class="modal-content"><table class="table table-condensed"></table>'
        "You have reached the maximum number of lookups. Contact ARRT.</div>"
    )
    data = parsers.parse_details(capped)
    assert not data["raw_details"]

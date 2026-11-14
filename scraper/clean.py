"""
Small, pure functions that turn the site's text into clean values.

Each one takes a string exactly as the site shows it and returns something
the database can filter on (a date, a list, a split name). They never
raise on odd input - they return None instead, and the raw text is kept
in the database anyway.
"""

import calendar
import re
from datetime import date, datetime

NAME_SUFFIXES = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "v"}


def split_name(full_name: str) -> tuple[str | None, str | None, str | None]:
    """'Abigail Elaine Adams' -> ('Abigail', 'Elaine', 'Adams'); handles 'Jr', 'III'."""
    parts = full_name.split()
    if not parts:
        return None, None, None
    if len(parts) > 2 and parts[-1].lower() in NAME_SUFFIXES:
        parts = parts[:-1]
    if len(parts) == 1:
        return parts[0], None, None
    first, last = parts[0], parts[-1]
    middle = " ".join(parts[1:-1]) or None
    return first, middle, last


def parse_disciplines(credential_string: str | None) -> str | None:
    """'R.T.(R)(CT)(ARRT)' -> 'R,CT'  (ARRT itself is not a discipline)."""
    if not credential_string:
        return None
    codes = [c for c in re.findall(r"\(([A-Z]+)\)", credential_string) if c != "ARRT"]
    return ",".join(codes) or None


def parse_us_date(text: str | None) -> date | None:
    """'11/1/2025' -> date(2025, 11, 1)"""
    if not text:
        return None
    try:
        return datetime.strptime(text.strip(), "%m/%d/%Y").date()
    except ValueError:
        return None


def parse_valid_thru(text: str | None) -> date | None:
    """'11/2026' -> date(2026, 11, 30)  (valid until the end of that month)."""
    if not text:
        return None
    m = re.search(r"(\d{1,2})/(\d{4})", text)
    if not m:
        return None
    month, year = int(m.group(1)), int(m.group(2))
    if not 1 <= month <= 12:
        return None
    return date(year, month, calendar.monthrange(year, month)[1])


def parse_date_range(text: str | None) -> tuple[date | None, date | None]:
    """'11/1/2025 to 10/31/2027' -> (date(2025,11,1), date(2027,10,31))"""
    if not text:
        return None, None
    found = re.findall(r"\d{1,2}/\d{1,2}/\d{4}", text)
    if len(found) < 2:
        return None, None
    return parse_us_date(found[0]), parse_us_date(found[1])


CQR_PATTERN = re.compile(
    r"([A-Za-z][A-Za-z &/\-]*?)\s+(\d{1,2}/\d{1,2}/\d{4})\s*-\s*(\d{1,2}/\d{1,2}/\d{4})"
)


def parse_cqr(text: str | None) -> list[dict] | None:
    """'Radiography 11/1/2032 - 10/31/2035' -> [{'discipline': 'Radiography', 'start': '2032-11-01', ...}]"""
    if not text:
        return None
    periods = []
    for name, start, end in CQR_PATTERN.findall(text):
        s, e = parse_us_date(start), parse_us_date(end)
        periods.append({
            "discipline": name.strip(),
            "start": s.isoformat() if s else start,
            "end": e.isoformat() if e else end,
        })
    return periods or None


def parse_description(lines: list[str]) -> list[dict] | None:
    """['(R) Radiography', '(CT) Computed Tomography'] -> [{'code': 'R', 'name': 'Radiography'}, ...]"""
    out = []
    for line in lines:
        m = re.match(r"\s*\(([A-Z]+)\)\s*(.+)", line)
        if m:
            out.append({"code": m.group(1), "name": m.group(2).strip()})
    return out or None

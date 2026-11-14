"""
Database tables - just two, on purpose.

credentials   one row per person: the results-table columns AND everything
              from the "View Details" popup.
scrape_runs   one row per scraper run: timings and per-query stats.

Why only two?
-------------
- Disciplines ("R,CT") are a short comma list -> filtered with FIND_IN_SET.
- CQR periods are a small list per person -> stored as JSON.
Separate tables for these would add JOINs to every query for no real gain
at ~35k rows; MySQL scans this in milliseconds.

Why no "status" column?
-----------------------
Active / Expired depends on *today's* date, so a stored value would go stale.
The API works it out at query time from valid_thru_date.
"""

from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class ScrapeRun(Base):
    """One execution of the scraper, with its timings."""

    __tablename__ = "scrape_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    total_seconds: Mapped[float | None] = mapped_column(Float)
    records_saved: Mapped[int] = mapped_column(Integer, default=0)
    details_fetched: Mapped[int] = mapped_column(Integer, default=0)
    details_failed: Mapped[int] = mapped_column(Integer, default=0)
    requests_per_second: Mapped[float | None] = mapped_column(Float)
    # [{"label": "first_a", "first": "a", "last": "%%", "found": 38473, "kept": 5000, "seconds": 41.2}, ...]
    queries: Mapped[list | None] = mapped_column(JSON)
    stats: Mapped[dict | None] = mapped_column(JSON)   # any extra timing breakdown


class Credential(Base):
    """One registered technologist: results-table row + details popup combined."""

    __tablename__ = "credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    # sha1(name|city|state|credential) - stable id used to skip duplicates
    person_key: Mapped[str] = mapped_column(String(64), unique=True)
    # the site's encrypted token for "View Details" (~263 chars, changes per search)
    detail_key: Mapped[str | None] = mapped_column(Text)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("scrape_runs.id"))
    source_query: Mapped[str] = mapped_column(String(50), index=True)  # e.g. "first_a"

    # --- from the results table -------------------------------------------
    full_name: Mapped[str] = mapped_column(String(255))
    first_name: Mapped[str | None] = mapped_column(String(100))
    middle_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100), index=True)
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(10), index=True)
    credential_string: Mapped[str | None] = mapped_column(String(255))  # R.T.(R)(CT)(ARRT)
    disciplines: Mapped[str | None] = mapped_column(String(100))        # "R,CT"

    # --- from the "View Details" popup -------------------------------------
    zip_code: Mapped[str | None] = mapped_column(String(20))
    country: Mapped[str | None] = mapped_column(String(100))
    valid_thru_raw: Mapped[str | None] = mapped_column(String(50))      # "11/2026"
    valid_thru_date: Mapped[date | None] = mapped_column(Date, index=True)  # 2026-11-30
    ce_biennium_raw: Mapped[str | None] = mapped_column(String(100))    # "11/1/2025 to 10/31/2027"
    ce_start_date: Mapped[date | None] = mapped_column(Date)
    ce_end_date: Mapped[date | None] = mapped_column(Date, index=True)
    # [{"discipline": "Radiography", "start": "2032-11-01", "end": "2035-10-31"}]
    cqr_periods: Mapped[list | None] = mapped_column(JSON)
    # [{"code": "R", "name": "Radiography"}]
    credential_description: Mapped[list | None] = mapped_column(JSON)

    # --- safety net: every label/value exactly as the site showed it -------
    raw_details: Mapped[dict | None] = mapped_column(JSON)

    details_fetched_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

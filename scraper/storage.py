"""
Saving scraped data to MySQL.

Rows are written in two steps, so nothing is lost if a run stops halfway:
  1. right after a search  -> the results-table columns (name, city, ...)
  2. as details arrive     -> the "View Details" fields for that person
Re-running the scraper skips people whose details are already saved.
"""

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.mysql import insert

from backend.db import SessionLocal
from backend.models import Credential, ScrapeRun

from .clean import parse_disciplines, split_name


def start_run() -> int:
    with SessionLocal.begin() as s:
        run = ScrapeRun(started_at=datetime.now())
        s.add(run)
        s.flush()
        return run.id


def finish_run(run_id: int, **fields) -> None:
    with SessionLocal.begin() as s:
        s.execute(update(ScrapeRun).where(ScrapeRun.id == run_id).values(finished_at=datetime.now(), **fields))


def people_with_details() -> set[str]:
    """person_keys that are already complete - used to resume / skip."""
    with SessionLocal() as s:
        return set(s.scalars(select(Credential.person_key).where(Credential.details_fetched_at.is_not(None))))


def people_missing_details() -> list[dict]:
    """Everyone saved from a search whose details we don't have yet."""
    with SessionLocal() as s:
        rows = s.execute(
            select(Credential.person_key, Credential.detail_key)
            .where(Credential.details_fetched_at.is_(None), Credential.detail_key.is_not(None))
            .order_by(Credential.id)
        ).all()
    return [{"person_key": k, "detail_key": d} for k, d in rows]


def save_list_rows(rows: list[dict], run_id: int, source_query: str) -> None:
    """Insert search rows; if a person already exists, just refresh their details key."""
    if not rows:
        return
    values = []
    for r in rows:
        first, middle, last = split_name(r["full_name"])
        values.append({
            "person_key": r["person_key"],
            "detail_key": r["detail_key"],
            "run_id": run_id,
            "source_query": source_query,
            "full_name": r["full_name"],
            "first_name": first,
            "middle_name": middle,
            "last_name": last,
            "city": r["city"] or None,
            "state": r["state"] or None,
            "credential_string": r["credential_string"] or None,
            "disciplines": parse_disciplines(r["credential_string"]),
        })
    with SessionLocal.begin() as s:
        for i in range(0, len(values), 1000):   # chunks keep each statement small
            stmt = insert(Credential).values(values[i:i + 1000])
            s.execute(stmt.on_duplicate_key_update(detail_key=stmt.inserted.detail_key))


def save_details(batch: list[tuple[str, dict]]) -> None:
    """batch = [(person_key, parsed_details), ...]"""
    if not batch:
        return
    now = datetime.now()
    with SessionLocal.begin() as s:
        for key, details in batch:
            s.execute(
                update(Credential)
                .where(Credential.person_key == key)
                .values(**details, details_fetched_at=now)
            )

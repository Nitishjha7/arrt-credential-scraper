"""
FastAPI backend for the ARRT credentials dashboard.

    .venv\\Scripts\\uvicorn backend.main:app --reload
    -> http://127.0.0.1:8000/docs   (interactive API docs)

All filtering, sorting and paging happens in MySQL, so the browser only
ever receives one page of rows.
"""

import copy
import csv
import io
from datetime import date
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import case, desc, func, or_, select
from sqlalchemy.orm import Session

from scraper.export_csv import COLUMNS, to_row

from .db import SessionLocal
from .models import Credential, ScrapeRun

app = FastAPI(title="ARRT Credentials API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Vite dev server
    allow_methods=["GET"],
    allow_headers=["*"],
)


def get_db():
    with SessionLocal() as session:
        yield session


# Active / Expired is computed on the fly from today's date (never stored)
STATUS = case(
    (Credential.valid_thru_date.is_(None), "Unknown"),
    (Credential.valid_thru_date >= func.curdate(), "Active"),
    else_="Expired",
).label("status")

SORTABLE = {
    "name": Credential.last_name,
    "city": Credential.city,
    "state": Credential.state,
    "valid_thru": Credential.valid_thru_date,
    "ce_end": Credential.ce_end_date,
}


class Filters:
    """Query-string filters shared by /api/records and /api/records.csv."""

    def __init__(
        self,
        q: str | None = Query(None, description="part of the name"),
        state: list[str] = Query(default=[]),
        discipline: list[str] = Query(default=[], description="R, CT, MR ..."),
        status: Literal["Active", "Expired", "Unknown"] | None = None,
        valid_from: date | None = None,
        valid_to: date | None = None,
        ce_end_from: date | None = None,
        ce_end_to: date | None = None,
        source_query: list[str] = Query(default=[]),
    ):
        args = locals()
        args.pop("self")
        self.__dict__.update(args)

    def apply(self, stmt):
        if self.q:
            like = f"%{self.q.strip()}%"
            stmt = stmt.where(or_(Credential.full_name.like(like), Credential.city.like(like)))
        if self.state:
            stmt = stmt.where(Credential.state.in_(self.state))
        if self.discipline:
            # disciplines is stored as "R,CT" -> FIND_IN_SET matches one code exactly
            stmt = stmt.where(or_(*(func.find_in_set(d, Credential.disciplines) > 0 for d in self.discipline)))
        if self.status == "Unknown":
            stmt = stmt.where(Credential.valid_thru_date.is_(None))
        elif self.status == "Active":
            stmt = stmt.where(Credential.valid_thru_date >= func.curdate())
        elif self.status == "Expired":
            stmt = stmt.where(Credential.valid_thru_date < func.curdate())
        if self.valid_from:
            stmt = stmt.where(Credential.valid_thru_date >= self.valid_from)
        if self.valid_to:
            stmt = stmt.where(Credential.valid_thru_date <= self.valid_to)
        if self.ce_end_from:
            stmt = stmt.where(Credential.ce_end_date >= self.ce_end_from)
        if self.ce_end_to:
            stmt = stmt.where(Credential.ce_end_date <= self.ce_end_to)
        if self.source_query:
            stmt = stmt.where(Credential.source_query.in_(self.source_query))
        return stmt


def row_to_dict(c: Credential, status: str) -> dict:
    return {
        "id": c.id,
        "full_name": c.full_name,
        "first_name": c.first_name,
        "middle_name": c.middle_name,
        "last_name": c.last_name,
        "city": c.city,
        "state": c.state,
        "zip_code": c.zip_code,
        "country": c.country,
        "credential_string": c.credential_string,
        "disciplines": c.disciplines.split(",") if c.disciplines else [],
        "credential_description": c.credential_description or [],
        "status": status,
        "valid_thru": c.valid_thru_raw,
        "valid_thru_date": c.valid_thru_date,
        "ce_biennium": c.ce_biennium_raw,
        "ce_start_date": c.ce_start_date,
        "ce_end_date": c.ce_end_date,
        "cqr_periods": c.cqr_periods or [],
        "source_query": c.source_query,
        "details_fetched": c.details_fetched_at is not None,
    }


@app.get("/api/records")
def list_records(
    filters: Filters = Depends(),
    sort: Literal["name", "city", "state", "valid_thru", "ce_end"] = "name",
    order: Literal["asc", "desc"] = "asc",
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    db: Session = Depends(get_db),
):
    base = filters.apply(select(Credential, STATUS))
    total = db.scalar(filters.apply(select(func.count(Credential.id))))

    col = SORTABLE[sort]
    ordering = [desc(col) if order == "desc" else col, Credential.first_name, Credential.id]
    rows = db.execute(base.order_by(*ordering).offset((page - 1) * page_size).limit(page_size)).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, -(-total // page_size)),
        "items": [row_to_dict(c, status) for c, status in rows],
    }


@app.get("/api/records.csv")
def export_records(filters: Filters = Depends(), db: Session = Depends(get_db)):
    """Same filters as /api/records, but every matching row as a CSV download."""
    rows = db.scalars(filters.apply(select(Credential)).order_by(Credential.last_name, Credential.first_name))
    buf = io.StringIO()
    buf.write("﻿")   # BOM so Excel reads UTF-8 names correctly
    writer = csv.DictWriter(buf, fieldnames=COLUMNS)
    writer.writeheader()
    for c in rows:
        writer.writerow(to_row(c))
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="arrt_credentials_filtered.csv"'},
    )


@app.get("/api/records/{record_id}")
def get_record(record_id: int, db: Session = Depends(get_db)):
    row = db.execute(select(Credential, STATUS).where(Credential.id == record_id)).first()
    if not row:
        raise HTTPException(404, "Record not found")
    c, status = row
    return {**row_to_dict(c, status), "raw_details": c.raw_details}


@app.get("/api/stats")
def stats(filters: Filters = Depends(), db: Session = Depends(get_db)):
    """Numbers for the stat cards and charts - they follow the current filters."""
    by_status = dict(db.execute(filters.apply(select(STATUS, func.count()).group_by("status"))).all())

    top_states = db.execute(
        filters.apply(select(Credential.state, func.count().label("n")))
        .where(Credential.state.is_not(None))
        .group_by(Credential.state).order_by(desc("n")).limit(10)
    ).all()

    # Count disciplines by splitting "R,CT" in Python (simple and fast at this size)
    discipline_counts: dict[str, int] = {}
    for (value,) in db.execute(filters.apply(select(Credential.disciplines))):
        for code in (value or "").split(","):
            if code:
                discipline_counts[code] = discipline_counts.get(code, 0) + 1

    expiring_soon = db.scalar(
        filters.apply(select(func.count(Credential.id))).where(
            Credential.valid_thru_date >= func.curdate(),
            func.datediff(Credential.valid_thru_date, func.curdate()) <= 90,
        )
    )

    # Renewal horizon: how many credentials expire in each month.
    # It ignores the Valid Thru range filter on purpose, so the chart keeps
    # showing the full picture while one month is selected.
    horizon_filters = copy.copy(filters)
    horizon_filters.valid_from = horizon_filters.valid_to = None
    month = func.date_format(Credential.valid_thru_date, "%Y-%m")
    by_month = db.execute(
        horizon_filters.apply(select(month.label("m"), func.count().label("n")))
        .where(Credential.valid_thru_date.is_not(None))
        .group_by("m").order_by("m")
    ).all()

    return {
        "valid_thru_by_month": [{"month": m, "count": n} for m, n in by_month],
        "with_details": db.scalar(filters.apply(select(func.count(Credential.id)))
                                  .where(Credential.details_fetched_at.is_not(None))),
        "total": sum(by_status.values()),
        "active": by_status.get("Active", 0),
        "expired": by_status.get("Expired", 0),
        "unknown": by_status.get("Unknown", 0),
        "expiring_90_days": expiring_soon,
        "top_states": [{"state": s, "count": n} for s, n in top_states],
        "disciplines": sorted(
            ({"code": k, "count": v} for k, v in discipline_counts.items()), key=lambda d: -d["count"]
        ),
    }


@app.get("/api/suggest")
def suggest(q: str = Query(..., min_length=2), db: Session = Depends(get_db)):
    """Autocomplete for the search box: matching names and cities (prefix match, max 8)."""
    like = f"{q.strip()}%"
    names = db.execute(
        select(Credential.id, Credential.full_name, Credential.city, Credential.state)
        .where(or_(Credential.last_name.like(like), Credential.first_name.like(like), Credential.full_name.like(like)))
        .order_by(Credential.last_name, Credential.first_name).limit(6)
    ).all()
    cities = db.execute(
        select(Credential.city, Credential.state, func.count().label("n"))
        .where(Credential.city.like(like)).group_by(Credential.city, Credential.state)
        .order_by(desc("n")).limit(3)
    ).all()
    return {
        "people": [{"id": i, "name": n, "place": f"{c}, {s}"} for i, n, c, s in names],
        "cities": [{"city": c, "state": s, "count": n} for c, s, n in cities],
    }


@app.get("/api/filters")
def filter_options(db: Session = Depends(get_db)):
    """Values for the dropdowns."""
    states = db.scalars(
        select(Credential.state).where(Credential.state.is_not(None)).distinct().order_by(Credential.state)
    ).all()
    queries = db.scalars(select(Credential.source_query).distinct().order_by(Credential.source_query)).all()

    names: dict[str, str] = {}
    for (desc_list,) in db.execute(select(Credential.credential_description).where(
        Credential.credential_description.is_not(None))):
        for d in desc_list or []:   # JSON null for people without details
            names.setdefault(d["code"], d["name"])
    codes = set()
    for (value,) in db.execute(select(Credential.disciplines).distinct()):
        codes.update(c for c in (value or "").split(",") if c)

    dates = db.execute(select(
        func.min(Credential.valid_thru_date), func.max(Credential.valid_thru_date),
        func.min(Credential.ce_end_date), func.max(Credential.ce_end_date),
    )).one()

    return {
        "states": states,
        "source_queries": queries,
        "disciplines": [{"code": c, "name": names.get(c, c)} for c in sorted(codes)],
        "valid_thru_range": [dates[0], dates[1]],
        "ce_end_range": [dates[2], dates[3]],
    }


@app.get("/api/run-stats")
def run_stats(db: Session = Depends(get_db)):
    """Timings of finished scraper runs, newest first (search runs and details runs)."""
    runs = db.scalars(
        select(ScrapeRun).where(ScrapeRun.finished_at.is_not(None)).order_by(desc(ScrapeRun.id)).limit(10)
    ).all()
    return [
        {
            "run_id": r.id,
            "mode": (r.stats or {}).get("mode", "full"),
            "started_at": r.started_at,
            "finished_at": r.finished_at,
            "total_seconds": r.total_seconds,
            "records_saved": r.records_saved,
            "details_fetched": r.details_fetched,
            "details_failed": r.details_failed,
            "requests_per_second": r.requests_per_second,
            "queries": r.queries or [],
        }
        for r in runs
    ]

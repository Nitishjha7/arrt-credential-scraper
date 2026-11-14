"""
Export the credentials table from MySQL to a CSV file.

    .venv\\Scripts\\python -m scraper.export_csv
    -> data/arrt_credentials.csv

Lists (CQR periods, credential description) are flattened into readable
text so the CSV opens nicely in Excel. "status" is worked out from
valid_thru_date against today's date.
"""

import csv
from datetime import date

from sqlalchemy import select

from backend.db import SessionLocal
from backend.models import Credential

from . import config

COLUMNS = [
    "full_name", "first_name", "middle_name", "last_name", "city", "state", "zip_code", "country",
    "credential_string", "disciplines", "credential_description", "status",
    "valid_thru_raw", "valid_thru_date", "ce_biennium_raw", "ce_start_date", "ce_end_date",
    "cqr_periods", "has_details", "source_query", "details_fetched_at",
]


def status_of(c: Credential) -> str:
    if c.valid_thru_date is None:
        return "No details"
    return "Active" if c.valid_thru_date >= date.today() else "Expired"


def to_row(c: Credential) -> dict:
    row = {col: getattr(c, col, None) for col in COLUMNS}
    row["status"] = status_of(c)
    # ARRT caps "View Details" lookups, so not every person has the popup fields
    row["has_details"] = "yes" if c.details_fetched_at else "no"
    row["credential_description"] = "; ".join(
        f"({d['code']}) {d['name']}" for d in (c.credential_description or [])
    )
    row["cqr_periods"] = "; ".join(
        f"{p['discipline']} {p['start']} to {p['end']}" for p in (c.cqr_periods or [])
    )
    return row


def main() -> None:
    out = config.DATA_DIR / "arrt_credentials.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with SessionLocal() as s, open(out, "w", newline="", encoding="utf-8-sig") as f:  # -sig: Excel-friendly
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        count = 0
        for c in s.scalars(select(Credential).order_by(Credential.last_name, Credential.first_name)):
            writer.writerow(to_row(c))
            count += 1
    print(f"Wrote {count:,} rows to {out}")


if __name__ == "__main__":
    main()

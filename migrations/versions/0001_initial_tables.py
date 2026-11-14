"""Initial tables: scrape_runs and credentials.

Revision ID: 0001
Revises:
Create Date: 2026-11-14
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # One row per scraper run (timings + per-query stats)
    op.create_table(
        "scrape_runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("started_at", sa.DateTime, nullable=False),
        sa.Column("finished_at", sa.DateTime),
        sa.Column("total_seconds", sa.Float),
        sa.Column("records_saved", sa.Integer, nullable=False, server_default="0"),
        sa.Column("details_fetched", sa.Integer, nullable=False, server_default="0"),
        sa.Column("details_failed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("requests_per_second", sa.Float),
        sa.Column("queries", sa.JSON),
        sa.Column("stats", sa.JSON),
        mysql_charset="utf8mb4",
    )

    # One row per person: results-table columns + "View Details" popup fields
    op.create_table(
        "credentials",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("detail_key", sa.String(255), nullable=False, unique=True),
        sa.Column("run_id", sa.Integer, sa.ForeignKey("scrape_runs.id")),
        sa.Column("source_query", sa.String(50), nullable=False, index=True),
        # results table
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("first_name", sa.String(100)),
        sa.Column("middle_name", sa.String(100)),
        sa.Column("last_name", sa.String(100), index=True),
        sa.Column("city", sa.String(100)),
        sa.Column("state", sa.String(10), index=True),
        sa.Column("credential_string", sa.String(255)),
        sa.Column("disciplines", sa.String(100)),
        # details popup
        sa.Column("zip_code", sa.String(20)),
        sa.Column("country", sa.String(100)),
        sa.Column("valid_thru_raw", sa.String(50)),
        sa.Column("valid_thru_date", sa.Date, index=True),
        sa.Column("ce_biennium_raw", sa.String(100)),
        sa.Column("ce_start_date", sa.Date),
        sa.Column("ce_end_date", sa.Date, index=True),
        sa.Column("cqr_periods", sa.JSON),
        sa.Column("credential_description", sa.JSON),
        # safety net
        sa.Column("raw_details", sa.JSON),
        sa.Column("details_fetched_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        mysql_charset="utf8mb4",
    )


def downgrade() -> None:
    op.drop_table("credentials")   # first, because it points at scrape_runs
    op.drop_table("scrape_runs")

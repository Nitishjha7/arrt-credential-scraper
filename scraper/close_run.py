"""
Close a run that was stopped early (Ctrl+C, deadline, crash).

A run only writes its timings when it finishes normally. If it was stopped,
this rebuilds the numbers from what actually reached MySQL - every detail is
saved with a timestamp, so nothing is guessed.

    .venv\\Scripts\\python -m scraper.close_run            # latest unfinished run
    .venv\\Scripts\\python -m scraper.close_run --run 7
"""

import argparse
import json

from sqlalchemy import func, select

from backend.db import SessionLocal
from backend.models import Credential, ScrapeRun

from . import config


def main(run_id: int | None) -> None:
    with SessionLocal.begin() as s:
        q = select(ScrapeRun).where(ScrapeRun.finished_at.is_(None)).order_by(ScrapeRun.id.desc())
        run = s.get(ScrapeRun, run_id) if run_id else s.scalars(q).first()
        if not run:
            print("No unfinished run found.")
            return

        fetched, last_at = s.execute(
            select(func.count(Credential.id), func.max(Credential.details_fetched_at))
            .where(Credential.details_fetched_at >= run.started_at)
        ).one()
        if not fetched:
            print(f"Run #{run.id} saved no details - nothing to close.")
            return

        seconds = (last_at - run.started_at).total_seconds()
        run.finished_at = last_at
        run.total_seconds = round(seconds, 2)
        run.details_fetched = fetched
        run.requests_per_second = round(fetched / seconds, 2) if seconds else None
        run.stats = {
            "run_id": run.id,
            "mode": "details-only",
            "stopped_early": True,
            "details": {"fetched": fetched, "seconds": run.total_seconds,
                        "requests_per_second": run.requests_per_second},
            "total_seconds": run.total_seconds,
        }
        stats = run.stats

    (config.DATA_DIR / "run_stats.json").write_text(json.dumps(stats, indent=2, default=str), encoding="utf-8")
    print(f"Closed run #{stats['run_id']}: {fetched:,} details in {stats['total_seconds']:.0f}s "
          f"({stats['details']['requests_per_second']} req/s)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Close a scraper run that was stopped early.")
    parser.add_argument("--run", type=int, help="run id (default: latest unfinished)")
    main(parser.parse_args().run)

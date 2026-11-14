"""
The main scraper.

    .venv\\Scripts\\python -m scraper.run                       # all queries from config.py
    .venv\\Scripts\\python -m scraper.run --queries first_a --limit 500   # quick test run
    .venv\\Scripts\\python -m scraper.run --workers 8           # faster details

What happens:
  1. Chrome opens. For each query in config.SEARCH_QUERIES the form is filled
     and YOU tick the captcha (one click per query). All searches run first,
     so you can do all the clicks in a couple of minutes and then walk away.
  2. Each search returns every matching row at once. We keep a random,
     repeatable sample (MAX_RECORDS_PER_QUERY), drop duplicates, and save the
     rows to MySQL straight away.
  3. "View Details" is fetched for every saved person, in parallel.
  4. Timings are saved in the scrape_runs table and data/run_stats.json.
"""

import argparse
import asyncio
import json
import random
from datetime import datetime

from playwright.async_api import async_playwright

from . import config, storage
from .browser import chrome_session, get_antiforgery_token, headless_session, run_search
from .details import fetch_all_details
from .parsers import parse_search
from .timer import StageTimer, fmt


async def main(queries: list[dict], limit: int | None, workers: int, skip_details: bool,
               details_limit: int | None, details_only: bool = False) -> None:
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    timer = StageTimer()
    run_id = storage.start_run()
    already_done = storage.people_with_details()
    rng = random.Random(config.RANDOM_SEED)

    query_stats: list[dict] = []
    to_fetch: dict[str, dict] = {}   # person_key -> row (dict also de-duplicates)

    print(f"\nRun #{run_id}: {len(queries)} queries, up to {limit or 'all'} rows each, {workers} workers")
    if already_done:
        print(f"  {len(already_done)} people already have details in MySQL - they will be skipped.")

    # Searches need a visible Chrome for the human captcha; details-only runs don't,
    # so they use a hidden browser that can't be closed by accident.
    session = headless_session if details_only else chrome_session
    async with async_playwright() as pw, session(pw) as (context, page):

        # ---- Step 1 + 2: searches (one captcha each) -----------------------
        for q in ([] if details_only else queries):
            label = q["label"]
            with timer.stage(f"search:{label}"):
                html = await run_search(page, q["first_name"], q["last_name"])
            (config.RAW_DIR / f"search_{label}.html").write_text(html, encoding="utf-8")

            rows = parse_search(html)
            found = len(rows)
            if limit and found > limit:
                rows = rng.sample(rows, limit)
            new_rows = [r for r in rows if r["person_key"] not in to_fetch]
            storage.save_list_rows(new_rows, run_id, label)
            for r in new_rows:
                to_fetch[r["person_key"]] = r

            search_seconds = timer.stages[f"search:{label}"]
            query_stats.append({
                "label": label, "first": q["first_name"], "last": q["last_name"],
                "found": found, "kept": len(new_rows), "seconds": search_seconds,
            })
            print(f"  {label}: site returned {found:,} rows, kept {len(new_rows):,}")

        # ---- Step 3: details (no captcha, parallel) -----------------------
        if details_only:
            # No searches this time: finish people saved by earlier runs.
            people = storage.people_missing_details()
            print(f"  --details-only: {len(people):,} saved people still need details.")
        else:
            people = [r for k, r in to_fetch.items() if k not in already_done and r["detail_key"]]
        if details_limit is not None and len(people) > details_limit:
            # The details endpoint is throttled by the site (~0.7 req/s measured),
            # so we fetch details for a random, repeatable sample only.
            people = rng.sample(people, details_limit)
        details_stats = {"fetched": 0, "failed": 0, "retries": 0, "seconds": 0, "requests_per_second": None}
        if skip_details:
            print("\n  --skip-details: not fetching details.")
        elif people:
            print(f"\n  Fetching details for {len(people):,} people with {workers} workers...")
            token = await get_antiforgery_token(page)
            with timer.stage("details"):
                details_stats = await fetch_all_details(context, token, people, workers)

    # ---- Step 4: save timings --------------------------------------------
    summary = {
        "run_id": run_id,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "workers": workers,
        "records_saved": len(to_fetch),
        "mode": "details-only" if details_only else "full",
        "queries": query_stats,
        "details": details_stats,
        **timer.summary(),
    }
    storage.finish_run(
        run_id,
        total_seconds=summary["total_seconds"],
        records_saved=len(to_fetch),
        details_fetched=details_stats["fetched"],
        details_failed=details_stats["failed"],
        requests_per_second=details_stats["requests_per_second"],
        queries=query_stats,
        stats=summary,
    )
    (config.DATA_DIR / "run_stats.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\n================ DONE ================")
    print(f"  Records saved   : {len(to_fetch):,}")
    print(f"  Details fetched : {details_stats['fetched']:,}  (failed: {details_stats['failed']})")
    print(f"  Details speed   : {details_stats['requests_per_second']} req/s")
    print(f"  Total time      : {fmt(summary['total_seconds'])}")
    print("  Next: .venv\\Scripts\\python -m scraper.export_csv")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape ARRT credentials into MySQL.")
    parser.add_argument("--queries", help="comma-separated labels from config.py, e.g. first_a,first_b")
    parser.add_argument("--limit", type=int, default=config.MAX_RECORDS_PER_QUERY, help="max rows kept per query")
    parser.add_argument("--workers", type=int, default=config.DETAIL_WORKERS, help="parallel details requests")
    parser.add_argument("--skip-details", action="store_true", help="only save the results-table columns")
    parser.add_argument("--details-only", action="store_true",
                        help="no searches (so no captcha): fetch details for people already in MySQL")
    parser.add_argument("--details-limit", type=int, default=config.MAX_DETAILS,
                        help="max people to fetch details for in this run (random sample)")
    args = parser.parse_args()

    chosen = config.SEARCH_QUERIES
    if args.queries:
        wanted = set(args.queries.split(","))
        chosen = [q for q in config.SEARCH_QUERIES if q["label"] in wanted]
        unknown = wanted - {q["label"] for q in chosen}
        if unknown:
            parser.error(f"unknown query label(s): {', '.join(unknown)}")

    asyncio.run(main(chosen, args.limit, args.workers, args.skip_details, args.details_limit, args.details_only))

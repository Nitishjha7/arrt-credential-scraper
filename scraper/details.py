"""
Fetch "View Details" for many people, several at a time.

This endpoint has no captcha. We call it through the same browser session
(context.request), so cookies are shared automatically, and we send the
same headers the page's own jQuery code sends.

Speed vs. politeness: DETAIL_WORKERS requests run in parallel. Failures
are retried with a growing pause (2s, 4s, 8s...), and a 429 "too many
requests" makes us back off longer.
"""

import asyncio
import time

from playwright.async_api import BrowserContext
from tqdm import tqdm

from . import config, storage
from .parsers import parse_details

SAVE_EVERY = 25    # write to MySQL in small batches, so a stopped run loses little


async def fetch_all_details(context: BrowserContext, token: str, people: list[dict], workers: int) -> dict:
    """
    people = [{"person_key": ..., "detail_key": ...}, ...]
    Returns timing stats: {"fetched", "failed", "seconds", "requests_per_second", "retries"}
    """
    headers = {
        "RequestVerificationToken": token,
        "X-Requested-With": "XMLHttpRequest",
        "Referer": config.SEARCH_PAGE_URL,
    }
    semaphore = asyncio.Semaphore(workers)
    pending: list[tuple[str, dict]] = []
    stats = {"fetched": 0, "failed": 0, "retries": 0, "error_statuses": {}}
    progress = tqdm(total=len(people), desc="details", unit="req")

    async def fetch_one(person: dict) -> None:
        async with semaphore:
            for attempt in range(1, config.MAX_RETRIES + 1):
                try:
                    resp = await context.request.post(
                        config.DETAILS_ENDPOINT,
                        form={"key": person["detail_key"]},
                        headers=headers,
                        timeout=config.REQUEST_TIMEOUT_SEC * 1000,
                    )
                    if resp.ok:
                        details = parse_details(await resp.text())
                        if details["raw_details"]:          # an empty popup = something went wrong
                            pending.append((person["person_key"], details))
                            stats["fetched"] += 1
                            return
                    status = str(resp.status)
                    wait = 30 if resp.status == 429 else 2 ** attempt
                except Exception as exc:
                    if "closed" in str(exc).lower():
                        # The Chrome window was closed: every further request would fail,
                        # so stop loudly instead of retrying thousands of times.
                        raise RuntimeError("Chrome was closed - keep its window open while scraping.") from exc
                    status = type(exc).__name__   # e.g. TimeoutError
                    wait = 2 ** attempt
                # remember what went wrong, so the run stats explain slowdowns
                stats["error_statuses"][status] = stats["error_statuses"].get(status, 0) + 1
                stats["retries"] += 1
                await asyncio.sleep(wait)
            stats["failed"] += 1

    async def run_and_save(person: dict) -> None:
        await fetch_one(person)
        progress.update(1)
        if len(pending) >= SAVE_EVERY:
            batch = pending[:]
            pending.clear()
            storage.save_details(batch)

    t0 = time.perf_counter()
    await asyncio.gather(*(run_and_save(p) for p in people))
    storage.save_details(pending)   # whatever is left
    progress.close()

    seconds = round(time.perf_counter() - t0, 2)
    stats["seconds"] = seconds
    stats["requests_per_second"] = round(stats["fetched"] / seconds, 2) if seconds else None
    return stats

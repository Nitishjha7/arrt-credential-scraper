"""
One-time reconnaissance script.

Run it once:
    .venv\\Scripts\\python -m scraper.recon

It performs ONE small search (default: first="a", last="adams", ~85 people),
then clicks "next page" and the first "View Details" button, and records
every network call the page makes. Everything is saved to data/inspect/ so
we can see exactly what the server sends back and write the parser against
real data instead of guesses.

You can try a different search:
    .venv\\Scripts\\python -m scraper.recon --first a --last %%
"""

import argparse
import asyncio
import json

from playwright.async_api import async_playwright

from . import config
from .browser import chrome_session, run_search

# Static assets we don't care about
IGNORED_TYPES = {"image", "stylesheet", "font", "media"}


async def main(first_name: str, last_name: str) -> None:
    out = config.INSPECT_DIR
    out.mkdir(parents=True, exist_ok=True)
    calls: list[dict] = []

    async with async_playwright() as pw, chrome_session(pw) as (context, page):

        # Record every request the page makes from here on
        async def on_response(response):
            req = response.request
            if req.resource_type in IGNORED_TYPES or "arrt.org" not in response.url:
                return
            entry = {
                "n": len(calls) + 1,
                "method": req.method,
                "url": response.url,
                "type": req.resource_type,
                "status": response.status,
                "content_type": response.headers.get("content-type", ""),
                "post_data": req.post_data,
            }
            try:
                body = await response.body()
                entry["size_bytes"] = len(body)
                fname = f"{entry['n']:02d}_{req.method}_{response.url.split('?')[0].rstrip('/').split('/')[-1]}.txt"
                (out / fname).write_bytes(body)
                entry["saved_as"] = fname
            except Exception as exc:  # redirects etc. have no body
                entry["body_error"] = str(exc)
            calls.append(entry)

        page.on("response", on_response)

        # 1) The search itself
        html = await run_search(page, first_name, last_name)
        (out / "search_response.html").write_text(html, encoding="utf-8")
        print("  Search done. Waiting for the grid to render...")
        await page.wait_for_timeout(5000)
        (out / "page_after_search.html").write_text(await page.content(), encoding="utf-8")

        # 2) Try going to page 2 - does that hit the server, or is paging local?
        try:
            await page.locator(
                '[aria-label*="next" i], [title*="next" i], .k-pager-nav:not(.k-disabled)'
            ).first.click(timeout=5000)
            print("  Clicked 'next page'.")
            await page.wait_for_timeout(3000)
        except Exception as exc:
            print(f"  Could not click next page: {exc}")

        # 3) Open one details popup
        try:
            await page.get_by_text("View Details").first.click(timeout=5000)
            print("  Clicked 'View Details'.")
            await page.wait_for_timeout(3000)
        except Exception as exc:
            print(f"  Could not click View Details: {exc}")


    (out / "network_calls.json").write_text(json.dumps(calls, indent=2), encoding="utf-8")
    print(f"\nSaved {len(calls)} network calls to {out}")
    for c in calls:
        print(f"  {c['n']:>2}. {c['method']:4} {c['status']} {c.get('size_bytes', '?'):>9} B  {c['url']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--first", default="a")
    parser.add_argument("--last", default="adams")
    args = parser.parse_args()
    asyncio.run(main(args.first, args.last))

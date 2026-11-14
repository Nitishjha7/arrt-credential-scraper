"""
Everything that needs a real browser lives here.

Why a real browser at all?
--------------------------
The search endpoint is protected by Google reCAPTCHA. We do NOT try to
bypass it (no solver services, no tricks) - that would break the site's
terms of use. Instead we open a normal, visible Chrome window, fill in the
form for you, and wait for a human to tick "I'm not a robot".

Once the captcha is solved, the page's own JavaScript fires the search and
we simply listen to the response. Everything after that (pagination,
details) is automatic.
"""

import asyncio
import subprocess
import time
import urllib.request
from contextlib import asynccontextmanager

from playwright.async_api import Page, Playwright

from . import config


def _chrome_is_listening() -> bool:
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{config.CHROME_DEBUG_PORT}/json/version", timeout=1)
        return True
    except OSError:
        return False


@asynccontextmanager
async def chrome_session(pw: Playwright):
    """
    Start a normal Google Chrome window and connect Playwright to it.

    Why not just pw.chromium.launch()? reCAPTCHA often refuses to work in
    Playwright's bundled browser. A regular Chrome (with its own throw-away
    profile, so your real profile is untouched) behaves like any user's
    browser, and you solve the captcha there yourself.

    Yields (context, page) with the Verify Credentials page loaded.
    """
    config.CHROME_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    chrome = subprocess.Popen([
        config.CHROME_PATH,
        f"--remote-debugging-port={config.CHROME_DEBUG_PORT}",
        f"--user-data-dir={config.CHROME_PROFILE_DIR}",
        "--no-first-run",
        "--no-default-browser-check",
        config.SEARCH_PAGE_URL,
    ])
    try:
        # Wait (max ~20s) for Chrome to open its debugging port
        for _ in range(40):
            if _chrome_is_listening():
                break
            await asyncio.sleep(0.5)
        else:
            raise RuntimeError("Chrome did not start. Check CHROME_PATH in scraper/config.py")

        browser = await pw.chromium.connect_over_cdp(f"http://127.0.0.1:{config.CHROME_DEBUG_PORT}")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()
        if "verify-credentials" not in page.url:
            await page.goto(config.SEARCH_PAGE_URL, wait_until="domcontentloaded")
        await page.wait_for_selector("input#lastname", timeout=60_000)
        yield context, page
        await browser.close()
    finally:
        chrome.terminate()


@asynccontextmanager
async def headless_session(pw: Playwright):
    """
    A hidden, bundled Chromium - used when no captcha is needed (details only).
    No window means nothing can be closed by accident during a long run.
    It just loads the page once to get the session cookies and the
    anti-forgery token, exactly like a visitor would.
    """
    browser = await pw.chromium.launch(headless=True)
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(config.SEARCH_PAGE_URL, wait_until="domcontentloaded")
    await page.wait_for_selector("input#lastname", timeout=60_000)
    try:
        yield context, page
    finally:
        await browser.close()


async def wait_for_captcha(page: Page) -> None:
    """
    Block until the human has solved the captcha.

    grecaptcha.getResponse() returns an empty string until the box is ticked
    (and any image challenge is completed), so we just poll it.
    """
    deadline = time.monotonic() + config.CAPTCHA_WAIT_SEC
    while time.monotonic() < deadline:
        try:
            # grecaptcha appears before its functions are ready, so check both
            token = await page.evaluate(
                "() => (window.grecaptcha && typeof grecaptcha.getResponse === 'function'"
                " && grecaptcha.getResponse()) || ''"
            )
        except Exception:
            token = ""   # page still loading / navigating - just try again
        if token:
            return
        await asyncio.sleep(1)
    raise TimeoutError("Nobody solved the captcha in time.")


async def run_search(page: Page, first_name: str, last_name: str) -> str:
    """
    Fill the form, wait for the human to solve the captcha, then send the
    search and return the response HTML.

    We send the POST ourselves (same URL, fields and headers as the page's
    own jQuery code) instead of clicking Search, because a 40k-row response
    is ~20 MB and Chrome drops bodies that big from its DevTools cache, so
    we couldn't read it back. The captcha token is still the one YOU solved.
    """
    await page.fill("input#lastname", last_name)
    await page.fill("input#firstname", first_name)
    await page.locator("input#lastname").scroll_into_view_if_needed()

    print(
        f"\n  >>> Please tick the captcha in the browser window "
        f"(first='{first_name}', last='{last_name}')."
        "\n      The search starts as soon as it's solved...",
        flush=True,
    )
    await wait_for_captcha(page)
    captcha_token = await page.evaluate("() => grecaptcha.getResponse()")

    response = await page.context.request.post(
        config.SEARCH_ENDPOINT,
        form={"firstName": first_name, "lastName": last_name, "captchaSuccessCode": captcha_token},
        headers={
            "RequestVerificationToken": await get_antiforgery_token(page),
            "X-Requested-With": "XMLHttpRequest",
            "Referer": config.SEARCH_PAGE_URL,
        },
        timeout=config.SEARCH_TIMEOUT_SEC * 1000,
    )
    # A captcha token works only once - clear the box for the next query
    await page.evaluate("() => grecaptcha.reset()")

    if response.status == 424:
        raise RuntimeError("Server rejected the captcha (HTTP 424). Try again.")
    if not response.ok:
        raise RuntimeError(f"Search failed with HTTP {response.status}")
    return await response.text()


async def get_antiforgery_token(page: Page) -> str:
    """
    The page embeds an ASP.NET anti-forgery token in a hidden input. The
    site's JS sends it as a 'RequestVerificationToken' header on every
    AJAX call, so we do the same.
    """
    return await page.input_value('input[name="__RequestVerificationToken"]')

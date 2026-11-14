"""
All the knobs for the scraper live in this one file.

If you want different data, change things here - you shouldn't need to
touch the actual scraping code.
"""

import os
from pathlib import Path

# --------------------------------------------------------------------------
# Where things are
# --------------------------------------------------------------------------
BASE_URL = "https://www.arrt.org"
SEARCH_PAGE_URL = f"{BASE_URL}/pages/verify-credentials"

# These two endpoints are what the page's own JavaScript calls
# (see https://www.arrt.org/js/custom/VerifyCredentialsWidget.js)
SEARCH_ENDPOINT = f"{BASE_URL}/VerifyCredentials/SearchByName"        # needs captcha
DETAILS_ENDPOINT = f"{BASE_URL}/VerifyCredentials/GetDisplayDetails"  # no captcha

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"            # untouched responses, useful for debugging
INSPECT_DIR = DATA_DIR / "inspect"    # output of `python -m scraper.recon`

# --------------------------------------------------------------------------
# What to search for
# --------------------------------------------------------------------------
# The site does a SQL "LIKE 'xyz%'" style match on both names, so:
#   - "a"  in first name  -> everyone whose first name starts with A
#   - "%%" in last name   -> matches ANY last name ("%" is the SQL wildcard;
#                            we need two characters because the form requires
#                            a last name of at least 2 characters)
#
# Each query = one captcha click. Add / remove queries freely.
SEARCH_QUERIES = [
    {"label": "first_a", "first_name": "a",  "last_name": "%%"},
    {"label": "first_b", "first_name": "b",  "last_name": "%%"},
    {"label": "first_c", "first_name": "c",  "last_name": "%%"},
    {"label": "first_d", "first_name": "d",  "last_name": "%%"},
    {"label": "last_sm", "first_name": "%",  "last_name": "sm"},   # Smith, Small, ...
    {"label": "last_pa", "first_name": "%",  "last_name": "pa"},   # Patel, Parker, ...
    {"label": "mix_j_jo", "first_name": "j", "last_name": "jo"},   # John Johnson, ...
]

# A single letter can return ~40k people. We don't need all of them, so we
# take a random (but repeatable, thanks to the seed) sample from each query.
MAX_RECORDS_PER_QUERY = 5000      # set to None to keep everything
RANDOM_SEED = 42

# The "View Details" endpoint is throttled by the site: we measured about
# 0.7 requests/second (bursts of ~15, then a ~15 s pause). Details for all
# 35k people would take ~13 hours, so by default we fetch a random sample.
# Re-run with a bigger --details-limit later; people already done are skipped.
MAX_DETAILS = 3000                # set to None for everyone

# --------------------------------------------------------------------------
# Browser
# --------------------------------------------------------------------------
# reCAPTCHA often refuses to work in Playwright's bundled Chromium (it runs
# in "automation mode"). So we start the user's normal Google Chrome with a
# separate, throw-away profile and let Playwright connect to it over the
# DevTools protocol. A human still solves the captcha.
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
# Override with env vars to run two scrapers side by side (e.g. searches while details run)
CHROME_DEBUG_PORT = int(os.getenv("CHROME_DEBUG_PORT", "9222"))
CHROME_PROFILE_DIR = DATA_DIR / os.getenv("CHROME_PROFILE", "chrome-profile")   # separate from your real profile

# --------------------------------------------------------------------------
# Speed / politeness
# --------------------------------------------------------------------------
DETAIL_WORKERS = 5          # how many detail requests run in parallel
REQUEST_TIMEOUT_SEC = 30    # per detail request
SEARCH_TIMEOUT_SEC = 300    # big searches (40k rows) can take a while
MAX_RETRIES = 3             # retries per detail request before giving up
CAPTCHA_WAIT_SEC = 1800     # how long we wait for a human to tick the captcha (30 min)

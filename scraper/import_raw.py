r"""
Add more people from a search response that is already saved on disk.

Every search saves its full response to data/raw/search_<label>.html
(e.g. all 38,473 people for first_a). The scraper only keeps a sample, so
this lets you grow the dataset later WITHOUT a new search or captcha.

    .venv\Scripts\python -m scraper.import_raw --label first_a --limit 12000

The same random seed is used, so the people already saved come first and
nobody is duplicated (person_key is unique).
"""

import argparse
import random

from . import config, storage
from .parsers import parse_search


def main(label: str, limit: int) -> None:
    path = config.RAW_DIR / f"search_{label}.html"
    rows = parse_search(path.read_text(encoding="utf-8"))
    rng = random.Random(config.RANDOM_SEED)
    sample = rng.sample(rows, min(limit, len(rows)))
    run_id = storage.start_run()
    storage.save_list_rows(sample, run_id, label)
    storage.finish_run(run_id, total_seconds=0, records_saved=len(sample),
                       stats={"mode": "import-raw", "label": label, "found": len(rows), "kept": len(sample)})
    print(f"{label}: {len(rows):,} people in the saved response, {len(sample):,} now in MySQL.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import more rows from a saved search response.")
    parser.add_argument("--label", required=True, help="query label, e.g. first_a")
    parser.add_argument("--limit", type=int, required=True, help="how many people to keep in total")
    args = parser.parse_args()
    main(args.label, args.limit)

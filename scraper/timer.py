"""
Tiny helper to time each stage of the scrape.

Usage:
    timer = StageTimer()
    with timer.stage("search:first_a"):
        ...do work...
    print(timer.summary())
"""

import time
from contextlib import contextmanager


class StageTimer:
    def __init__(self) -> None:
        self.started = time.perf_counter()
        self.stages: dict[str, float] = {}

    @contextmanager
    def stage(self, name: str):
        t0 = time.perf_counter()
        try:
            yield
        finally:
            seconds = round(time.perf_counter() - t0, 2)
            self.stages[name] = seconds
            print(f"  [time] {name}: {fmt(seconds)}", flush=True)

    def total(self) -> float:
        return round(time.perf_counter() - self.started, 2)

    def summary(self) -> dict:
        return {"total_seconds": self.total(), "stages": self.stages}


def fmt(seconds: float) -> str:
    """75.3 -> '1m 15s'"""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{seconds:.1f}s"


import threading
import time

from collections import Counter


_lock = threading.Lock()

_counters = Counter({
    "hits": 0,
    "misses": 0,
    "errors": 0,
    "lookups": 0,
})

_total_lookup_seconds = 0.0



def record_cache_lookup(status: str, duration_seconds: float) -> None:
    """Record the result and duration of a Redis cache lookup."""
    global _total_lookup_seconds

    if status not in {"hit", "miss", "error"}:
        raise ValueError(f"Unknown cache status: {status}")

    with _lock:
        _counters["lookups"] += 1

        key = {
            "hit": "hits",
            "miss": "misses",
            "error": "errors",
        }[status]

        _counters[key] += 1
        _total_lookup_seconds += duration_seconds



def get_cache_metrics() -> dict:
    """Return a snapshot of cache metrics for this process."""
    with _lock:
        counters = dict(_counters)
        total_seconds = _total_lookup_seconds

    lookups = counters["lookups"]

    return {
        **counters,
        "hit_rate_percent": round(
            counters["hits"] / lookups * 100, 2
        ) if lookups else 0.0,
        "average_lookup_ms": round(
            total_seconds / lookups * 1000, 2
        ) if lookups else 0.0,
        "uptime_note": "Metrics reset when the application process restarts.",
    }

"""Retry policy for partner pushes.

Implemented: AC-2.2 — a 4xx marks the Order sync-failed at once, no retry.

NOTE: AC-2.1 (retry a 5xx up to three times with exponential backoff) is NOT
implemented here — a 5xx falls through to the same immediate-fail path as a 4xx.
"""


def classify(status_code):
    """Return the sync disposition for a partner status code."""
    if 400 <= status_code < 500:
        # AC-2.2: a 4xx marks the Order sync-failed without retrying.
        return "sync-failed"
    if status_code >= 500:
        # A 5xx currently fails immediately — no backoff, no retry loop.
        return "sync-failed"
    return "synced"

"""Conservative per-model pacing for sequential RPG TTS requests."""

import time


MIN_INTERVAL_SECONDS = 10.1  # No more than 6 starts in any rolling 60 seconds.
_last_request_at = {}


def wait_before_request(model):
    """Space request starts; callers must stop on HTTP 429, never auto-retry."""
    previous = _last_request_at.get(model)
    if previous is not None:
        remaining = MIN_INTERVAL_SECONDS - (time.monotonic() - previous)
        if remaining > 0:
            time.sleep(remaining)
    _last_request_at[model] = time.monotonic()

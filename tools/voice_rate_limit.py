"""Shared, append-only TTS request ledger and conservative model limits."""

import atexit
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import fcntl
import json
from pathlib import Path
import time


ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = ROOT / "ai/tts-api-attempts.jsonl"
MIN_INTERVAL_SECONDS = 10.1  # At most six starts in a rolling 60-second window.
MAX_ATTEMPTS_24H = 90  # Safety margin below the provider's 100 RPD per model.
_used_models = set()


def _parse_utc(value):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError("TTS request log timestamp lacks timezone")
    return result.astimezone(timezone.utc)


def _recent_attempts(entries, model, now):
    """Count both successes and failed requests; historical aggregates expire."""
    count = 0
    latest = None
    for entry in entries:
        if entry["model"] != model:
            continue
        if entry["kind"] == "request":
            started = _parse_utc(entry["started_utc"])
            if started > now - timedelta(hours=24):
                count += 1
            if latest is None or started > latest:
                latest = started
        elif entry["kind"] == "historical_aggregate":
            if now < _parse_utc(entry["expires_utc"]):
                count += entry["count"]
        else:
            raise ValueError(f"Unknown TTS log entry kind: {entry['kind']}")
    return count, latest


def attempts_last_24h(model):
    if not LOG_PATH.exists():
        return 0
    entries = [json.loads(line) for line in LOG_PATH.read_text(encoding="utf-8").splitlines()]
    return _recent_attempts(entries, model, datetime.now(timezone.utc))[0]


@contextmanager
def request_slot(model, key):
    """Serialize model calls, enforce spacing and log an attempt before POST.

    A rejected HTTP request still occupies one provider request. Never retry it
    inside this context; the caller stops and follows the 90-second/24-hour rule.
    """
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a+", encoding="utf-8") as ledger:
        fcntl.flock(ledger, fcntl.LOCK_EX)
        ledger.seek(0)
        entries = [json.loads(line) for line in ledger if line.strip()]
        now = datetime.now(timezone.utc)
        count, latest = _recent_attempts(entries, model, now)
        if count >= MAX_ATTEMPTS_24H:
            raise RuntimeError(
                f"TTS 24-hour cap reached for {model}: {count}/{MAX_ATTEMPTS_24H}; "
                "do not retry before the next safe window"
            )
        if latest is not None:
            remaining = MIN_INTERVAL_SECONDS - (now - latest).total_seconds()
            if remaining > 0:
                time.sleep(remaining)
                now = datetime.now(timezone.utc)
        ledger.seek(0, 2)
        ledger.write(json.dumps({
            "kind": "request", "model": model, "key": key,
            "started_utc": now.isoformat(timespec="microseconds"),
        }, ensure_ascii=False) + "\n")
        ledger.flush()
        _used_models.add(model)
        print(f"TTS attempt {count + 1}/{MAX_ATTEMPTS_24H} in 24h: {model} {key}", flush=True)
        try:
            yield
        finally:
            fcntl.flock(ledger, fcntl.LOCK_UN)


def _print_summary():
    for model in sorted(_used_models):
        print(f"TTS attempts in last 24h, including refusals: {model} "
              f"{attempts_last_24h(model)}/{MAX_ATTEMPTS_24H}", flush=True)


atexit.register(_print_summary)

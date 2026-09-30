#!/usr/bin/env python3
"""Verify the TTS request-count policy without network calls or real sleeps."""

from datetime import datetime, timedelta, timezone
import unittest

import voice_rate_limit


class VoiceRateLimitTests(unittest.TestCase):
    def test_requests_include_failed_attempts_but_only_for_own_model(self):
        now = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
        entries = [
            {"kind": "request", "model": "flash", "key": "one",
             "started_utc": (now - timedelta(minutes=2)).isoformat()},
            {"kind": "request", "model": "flash", "key": "rejected_429",
             "started_utc": (now - timedelta(minutes=1)).isoformat()},
            {"kind": "request", "model": "flash-lite", "key": "other",
             "started_utc": now.isoformat()},
        ]
        count, latest = voice_rate_limit._recent_attempts(entries, "flash", now)
        self.assertEqual(count, 2)
        self.assertEqual(latest, now - timedelta(minutes=1))

    def test_historical_hold_expires_after_24_hours(self):
        expiry = datetime(2026, 10, 1, 12, 50, tzinfo=timezone.utc)
        entries = [{"kind": "historical_aggregate", "model": "flash",
                    "count": 106, "expires_utc": expiry.isoformat()}]
        self.assertEqual(voice_rate_limit._recent_attempts(
            entries, "flash", expiry - timedelta(seconds=1))[0], 106)
        self.assertEqual(voice_rate_limit._recent_attempts(entries, "flash", expiry)[0], 0)


if __name__ == "__main__":
    unittest.main()

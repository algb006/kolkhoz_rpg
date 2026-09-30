#!/usr/bin/env python3
"""Verify the sequential TTS pacing without network calls or real sleeps."""

import unittest
from unittest.mock import patch

import voice_rate_limit


class VoiceRateLimitTests(unittest.TestCase):
    def setUp(self):
        voice_rate_limit._last_request_at.clear()

    def test_same_model_is_spaced(self):
        clock = iter((0.0, 2.0, 10.1))
        with patch.object(voice_rate_limit.time, "monotonic", side_effect=lambda: next(clock)):
            with patch.object(voice_rate_limit.time, "sleep") as sleeper:
                voice_rate_limit.wait_before_request("gemini-3.8-flash-tts")
                voice_rate_limit.wait_before_request("gemini-3.8-flash-tts")
        sleeper.assert_called_once()
        self.assertAlmostEqual(sleeper.call_args.args[0], 8.1)

    def test_other_model_has_independent_window(self):
        clock = iter((0.0, 0.1))
        with patch.object(voice_rate_limit.time, "monotonic", side_effect=lambda: next(clock)):
            with patch.object(voice_rate_limit.time, "sleep") as sleeper:
                voice_rate_limit.wait_before_request("flash")
                voice_rate_limit.wait_before_request("flash-lite")
        sleeper.assert_not_called()


if __name__ == "__main__":
    unittest.main()

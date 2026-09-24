#!/usr/bin/env python3
"""One resumable, budget-capped draft pass over the approved prologue lines."""

import hashlib
import io
import json
from pathlib import Path
import sqlite3
import sys
import urllib.error
import urllib.request
import wave

from voice_prologue_probe import API, VOICES, api_key, audio_from_response, modality_tokens


ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "db/story.db"
DESIGN_DB = ROOT.parent / "db/design.db"
DEST = Path("/data/kolkhoz/voice/prologue/lines")
MODEL = "gemini-3.8-flash-tts"
MAX_PASS_USD = 0.25


def approved_lines(avatar):
    design = sqlite3.connect(f"file:{DESIGN_DB}?mode=ro", uri=True)
    policy = design.execute(
        "SELECT voice_policy FROM scene WHERE key='scene.start.prologue'"
    ).fetchone()
    design.close()
    if policy != ("engine_allowed",):
        raise RuntimeError(f"prologue not voice-enabled: {policy}")
    story = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    rows = story.execute(
        "SELECT key,text,rev,approved_rev FROM line "
        "WHERE key LIKE ? AND deprecated=0 ORDER BY sort,key",
        (f"scene.start.prologue.{avatar}.t%",),
    ).fetchall()
    story.close()
    if len(rows) != 8 or any(rev != approved for _, _, rev, approved in rows):
        raise RuntimeError(f"expected 8 approved lines for {avatar}, got {rows}")
    return rows


def spent_this_pass():
    return sum(json.loads(path.read_text(encoding="utf-8"))["estimated_usd_from_usage"]
               for path in DEST.glob("*.json"))


def generate(key, text, rev, avatar):
    payload = {
        "model": MODEL,
        "input": [{"type": "user_input", "content": [{"type": "text", "text": text}]}],
        "response_format": {"type": "audio"},
        "generation_config": {"speech_config": [{"voice": VOICES[avatar]}]},
    }
    request = urllib.request.Request(
        API, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"x-goog-api-key": api_key(), "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            data = json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"API HTTP {exc.code}; response suppressed") from None
    audio = audio_from_response(data)
    if not audio:
        raise RuntimeError(f"No WAV for {key}; top-level keys: {list(data)}")
    with wave.open(io.BytesIO(audio), "rb") as wav:
        channels, rate, width, frames = (
            wav.getnchannels(), wav.getframerate(), wav.getsampwidth(), wav.getnframes()
        )
    if (channels, rate, width) != (1, 24000, 2):
        raise RuntimeError(f"Unexpected WAV for {key}: {channels}ch {rate}Hz {width * 8}bit")
    usage = data.get("usage") or data.get("interaction", {}).get("usage") or {}
    input_tokens = modality_tokens(usage, "input_tokens_by_modality", "text")
    output_tokens = modality_tokens(usage, "output_tokens_by_modality", "audio")
    if not input_tokens:
        input_tokens = usage.get("total_input_tokens", 0)
    if not output_tokens:
        output_tokens = usage.get("total_output_tokens", 0)
    if not input_tokens or not output_tokens:
        raise RuntimeError(f"No billable usage for {key}: {usage}")
    cost = input_tokens * 0.50 / 1_000_000 + output_tokens * 9.00 / 1_000_000
    receipt = {
        "key": key, "avatar": avatar, "voice": VOICES[avatar], "model": MODEL,
        "text": text, "rev": rev, "approved_rev": rev,
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "wav_sha256": hashlib.sha256(audio).hexdigest(),
        "duration_seconds": frames / rate, "sample_rate": rate,
        "channels": channels, "bits_per_sample": width * 8,
        "style": None, "inline_tags": [], "usage": usage,
        "estimated_usd_from_usage": cost,
        "interaction_id": data.get("id") or data.get("interaction", {}).get("id"),
        "status": "draft_for_human_review_not_accepted",
    }
    return audio, receipt


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in VOICES:
        raise SystemExit("usage: voice_prologue_lines.py <avatar-key>")
    avatar = sys.argv[1]
    rows = approved_lines(avatar)
    DEST.mkdir(parents=True, exist_ok=True)
    for key, text, rev, _ in rows:
        wav_path = DEST / f"{key}.wav"
        receipt_path = DEST / f"{key}.json"
        if wav_path.exists() and receipt_path.exists():
            print(f"skip existing {key}", flush=True)
            continue
        if wav_path.exists() or receipt_path.exists():
            raise RuntimeError(f"partial output exists for {key}; inspect manually")
        if spent_this_pass() + 0.02 > MAX_PASS_USD:
            raise RuntimeError("pass budget cap nearly reached; stop before next request")
        audio, receipt = generate(key, text, rev, avatar)
        with wav_path.open("xb") as file:
            file.write(audio)
        with receipt_path.open("x", encoding="utf-8") as file:
            json.dump(receipt, file, ensure_ascii=False, indent=2)
            file.write("\n")
        print(f"{key}: {receipt['duration_seconds']:.2f}s, "
              f"in={receipt['usage']['total_input_tokens']}, "
              f"out={receipt['usage']['total_output_tokens']}, "
              f"USD={receipt['estimated_usd_from_usage']:.6f}", flush=True)


if __name__ == "__main__":
    main()

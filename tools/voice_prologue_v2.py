#!/usr/bin/env python3
"""Budget-capped, separate audition of the eight approved prologue voices."""

import hashlib
import io
import json
from pathlib import Path
import sys
import urllib.error
import urllib.request
import wave

from voice_prologue_lines import approved_lines
from voice_prologue_probe import (
    API, EXPECTED_GENDER, VOICES, api_key, audio_from_response,
    modality_tokens, verified_voice_gender,
)


MODEL = "gemini-3.8-flash-tts"
DEST = Path("/data/kolkhoz/voice/prologue/v2")
SAMPLE_CAP_USD = 0.04
FULL_CAP_USD = 0.30
MIN_REMAINING_USD = 0.006

STYLES = {
    "villager": "Неторопливая, основательная мысль про себя; спокойная сельская мелодика без комического говора.",
    "worker": "По-заводскому напористо и просто, с живым слободским ритмом; ударение на действии, без лозунга.",
    "student": "Книжно и увлечённо; молодая ясная дикция, короткая заминка перед выводом.",
    "ex_chairman": "Сухо и осторожно, будто проверяет вывод про себя; сдержанная концовка.",
    "promoted": "Гладко и размеренно; уверенность в порядке, едва заметное снисхождение.",
    "old_fighter": "Жёсткая мысль про себя, короткими тактами и паузами как точки; без крика.",
    "dealer": "Учтиво и иронично; лёгкая одесская вопросительная мелодика в утверждении, без пародии.",
    "acting": "Собранно и практично, экономно; мягче только при мысли о людях.",
}


def selected_rows(mode):
    for avatar in VOICES:
        rows = approved_lines(avatar)
        for key, words, rev, _ in rows:
            if mode == "sample" and not key.endswith(".t8"):
                continue
            yield key, words, rev, avatar


def spent():
    return sum(
        json.loads(path.read_text(encoding="utf-8"))["estimated_usd_from_usage"]
        for path in DEST.glob("*.json")
    )


def request_line(key, words, rev, avatar):
    voice = VOICES[avatar]
    style = STYLES[avatar]
    payload = {
        "model": MODEL,
        "input": [{"type": "user_input", "content": [{
            "type": "text", "text": words,
            "annotations": [{"type": "speech_metadata", "style": style}],
        }]}],
        "response_format": {"type": "audio"},
        "generation_config": {"speech_config": [{"voice": voice}]},
    }
    request = urllib.request.Request(
        API,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
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
        "key": key, "avatar": avatar, "voice": voice,
        "gender": EXPECTED_GENDER[avatar], "model": MODEL,
        "text": words, "rev": rev, "approved_rev": rev,
        "text_sha256": hashlib.sha256(words.encode("utf-8")).hexdigest(),
        "wav_sha256": hashlib.sha256(audio).hexdigest(),
        "duration_seconds": frames / rate, "sample_rate": rate,
        "channels": channels, "bits_per_sample": width * 8,
        "style": style, "inline_tags": [], "usage": usage,
        "estimated_usd_from_usage": cost,
        "interaction_id": data.get("id") or data.get("interaction", {}).get("id"),
        "status": "v2_draft_for_human_review_not_accepted",
    }
    return audio, receipt


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("dry-run", "sample", "full"):
        raise SystemExit("usage: voice_prologue_v2.py <dry-run|sample|full>")
    mode = sys.argv[1]
    rows = list(selected_rows("sample" if mode == "sample" else "full"))
    if mode == "dry-run":
        for key, words, rev, avatar in rows:
            print(f"{key}\trev={rev}\t{VOICES[avatar]}\t{words}")
        return
    cap = SAMPLE_CAP_USD if mode == "sample" else FULL_CAP_USD
    DEST.mkdir(parents=True, exist_ok=True)
    for key, words, rev, avatar in rows:
        wav_path = DEST / f"{key}.wav"
        receipt_path = DEST / f"{key}.json"
        if wav_path.exists() and receipt_path.exists():
            print(f"skip existing {key}", flush=True)
            continue
        if wav_path.exists() or receipt_path.exists():
            raise RuntimeError(f"partial output exists for {key}; inspect manually")
        if spent() + MIN_REMAINING_USD > cap:
            raise RuntimeError("v2 budget cap nearly reached; stop before next request")
        verified_voice_gender(VOICES[avatar], EXPECTED_GENDER[avatar])
        audio, receipt = request_line(key, words, rev, avatar)
        with wav_path.open("xb") as file:
            file.write(audio)
        with receipt_path.open("x", encoding="utf-8") as file:
            json.dump(receipt, file, ensure_ascii=False, indent=2)
            file.write("\n")
        print(f"{key}: {receipt['duration_seconds']:.2f}s, "
              f"USD={receipt['estimated_usd_from_usage']:.6f}", flush=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Eight paid, provisional voice auditions for the prologue; no accepted takes."""

import base64
import hashlib
import io
import json
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request
import wave


API = "https://generativelanguage.googleapis.com/v1beta/interactions"
MODEL = "gemini-3.8-flash-lite-tts"
TEXT = "Дорога длинная, а день только начинается."
DEST = Path("/data/kolkhoz/voice/prologue/probes")
KEYFILE = Path.home() / ".config/kolkhoz/gemini.env"
VOICES = {
    "villager": "Achird",
    "worker": "Iapetus",
    "student": "Puck",
    "ex_chairman": "Schedar",
    "promoted": "Charon",
    "old_fighter": "Algenib",
    "dealer": "Algieba",
    "acting": "Kore",
}
EXPECTED_GENDER = {avatar: "female" if avatar == "acting" else "male"
                   for avatar in VOICES}


def api_key():
    for raw in KEYFILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("export "):
            line = line[7:].strip()
        if line.startswith("GEMINI_API_KEY="):
            return line.split("=", 1)[1].strip().strip("\"'")
    raise RuntimeError("GEMINI_API_KEY absent")


def audio_from_response(value):
    if isinstance(value, dict):
        if isinstance(value.get("data"), str):
            try:
                decoded = base64.b64decode(value["data"], validate=True)
            except ValueError:
                decoded = b""
            if decoded.startswith(b"RIFF") and decoded[8:12] == b"WAVE":
                return decoded
        for nested in value.values():
            result = audio_from_response(nested)
            if result:
                return result
    elif isinstance(value, list):
        for nested in value:
            result = audio_from_response(nested)
            if result:
                return result
    return None


def modality_tokens(usage, field, modality):
    return sum(item.get("tokens", 0) for item in usage.get(field, [])
               if item.get("modality") == modality)


def verified_voice_gender(voice, expected):
    query = urllib.parse.urlencode({"type": "prebuilt", "search": voice,
                                    "page_size": 1000})
    request = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/voices?{query}",
        headers={"x-goog-api-key": api_key()},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.load(response)
    matches = [item for item in data.get("voices", [])
               if item.get("display_name", "").casefold() == voice.casefold()
               and item.get("language_code") == "en-US"]
    if len(matches) != 1 or matches[0].get("gender") != expected:
        raise RuntimeError(f"voice {voice}: expected {expected}, catalogue has "
                           f"{[(item.get('gender'), item.get('language_code')) for item in matches]}")
    return matches[0]["gender"]


def main():
    if len(sys.argv) not in (2, 3) or sys.argv[1] not in VOICES:
        raise SystemExit("usage: voice_prologue_probe.py <avatar-key> [candidate-voice]")
    avatar = sys.argv[1]
    voice = sys.argv[2] if len(sys.argv) == 3 else VOICES[avatar]
    basename = f"{avatar}-{voice}-lite-probe" if len(sys.argv) == 3 else f"{avatar}-lite-probe"
    wav_path = DEST / f"{basename}.wav"
    receipt_path = DEST / f"{basename}.json"
    if wav_path.exists() or receipt_path.exists():
        raise SystemExit(f"probe already exists: {avatar}")
    verified_voice_gender(voice, EXPECTED_GENDER[avatar])
    payload = {
        "model": MODEL,
        "input": [{"type": "user_input", "content": [{"type": "text", "text": TEXT}]}],
        "response_format": {"type": "audio"},
        "generation_config": {"speech_config": [{"voice": voice}]},
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
        raise SystemExit(f"API HTTP {exc.code}; response suppressed to protect credentials")
    audio = audio_from_response(data)
    if not audio:
        raise SystemExit(f"No WAV in response; top-level keys: {list(data)}")
    with wave.open(io.BytesIO(audio), "rb") as wav:
        channels, rate, width, frames = (
            wav.getnchannels(), wav.getframerate(), wav.getsampwidth(), wav.getnframes()
        )
    if (channels, rate, width) != (1, 24000, 2):
        raise SystemExit(f"Unexpected WAV: {channels}ch {rate}Hz {width * 8}bit")
    usage = data.get("usage") or data.get("interaction", {}).get("usage") or {}
    input_tokens = modality_tokens(usage, "input_tokens_by_modality", "text")
    output_tokens = modality_tokens(usage, "output_tokens_by_modality", "audio")
    if not input_tokens:
        input_tokens = usage.get("total_input_tokens", 0)
    if not output_tokens:
        output_tokens = usage.get("total_output_tokens", 0)
    cost = input_tokens * 0.50 / 1_000_000 + output_tokens * 6.00 / 1_000_000
    receipt = {
        "avatar": avatar, "voice": voice, "gender": EXPECTED_GENDER[avatar], "model": MODEL,
        "text": TEXT, "text_sha256": hashlib.sha256(TEXT.encode()).hexdigest(),
        "sha256": hashlib.sha256(audio).hexdigest(), "duration_seconds": frames / rate,
        "usage": usage, "estimated_usd_from_usage": cost,
        "interaction_id": data.get("id") or data.get("interaction", {}).get("id"),
        "status": "audition_only_not_accepted",
    }
    DEST.mkdir(parents=True, exist_ok=True)
    with wav_path.open("xb") as file:
        file.write(audio)
    with receipt_path.open("x", encoding="utf-8") as file:
        json.dump(receipt, file, ensure_ascii=False, indent=2)
        file.write("\n")
    print(f"{avatar}: {frames / rate:.2f}s, in={input_tokens}, out={output_tokens}, USD={cost:.6f}")


if __name__ == "__main__":
    main()

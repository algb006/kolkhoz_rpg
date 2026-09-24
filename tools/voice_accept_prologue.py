#!/usr/bin/env python3
"""Freeze the human-approved demo-prologue TTS originals in the RPG repository."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import wave

from voice_prologue_probe import EXPECTED_GENDER, VOICES


ROOT = Path(__file__).resolve().parent.parent
SOURCE = Path("/data/kolkhoz/voice/prologue/lines")
DEST = ROOT / "voice/accepted/prologue"
DB = ROOT / "db/story.db"
APPROVED_ON = "2026-09-24"
APPROVAL = "Я прослушал. Принимаю работуЮ для демо пролога устроит."


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def keep_exact(path, data):
    if path.exists():
        if path.read_bytes() != data:
            raise RuntimeError(f"accepted file differs; never overwrite: {path}")
        return
    with path.open("xb") as output:
        output.write(data)


def main():
    with sqlite3.connect(f"file:{DB}?mode=ro", uri=True) as con:
        rows = con.execute(
            "SELECT key,text,rev,approved_rev FROM line "
            "WHERE key LIKE 'scene.start.prologue.%' AND deprecated=0 ORDER BY key"
        ).fetchall()
    if len(rows) != 64:
        raise RuntimeError(f"expected 64 current prologue lines, got {len(rows)}")
    if len(list(SOURCE.glob("*.wav"))) != 64 or len(list(SOURCE.glob("*.json"))) != 64:
        raise RuntimeError("draft folder must contain exactly 64 WAV and 64 receipts")

    pending = []
    items = []
    totals = {"requests": 0, "input_tokens": 0, "output_audio_tokens": 0,
              "duration_seconds": 0.0, "estimated_usd_from_usage": 0.0}
    for key, text, rev, approved in rows:
        avatar = key.split(".")[3]
        if avatar not in VOICES or rev != approved or rev != 2:
            raise RuntimeError(f"unexpected avatar or unapproved revision: {key}")
        wav_path = SOURCE / f"{key}.wav"
        receipt_path = SOURCE / f"{key}.json"
        audio = wav_path.read_bytes()
        receipt_bytes = receipt_path.read_bytes()
        receipt = json.loads(receipt_bytes)
        if (receipt["key"] != key or receipt["text"] != text
                or receipt["rev"] != rev or receipt["approved_rev"] != approved
                or receipt["voice"] != VOICES[avatar]
                or receipt.get("gender", EXPECTED_GENDER[avatar]) != EXPECTED_GENDER[avatar]
                or receipt["text_sha256"] != digest(text.encode("utf-8"))
                or receipt["wav_sha256"] != digest(audio)
                or receipt["status"] != "draft_for_human_review_not_accepted"):
            raise RuntimeError(f"draft receipt does not match approved text/audio: {key}")
        with wave.open(str(wav_path), "rb") as wav:
            if (wav.getnchannels(), wav.getframerate(), wav.getsampwidth()) != (1, 24000, 2):
                raise RuntimeError(f"unsupported source WAV format: {key}")
            duration = wav.getnframes() / wav.getframerate()
        if abs(duration - receipt["duration_seconds"]) > 0.0001:
            raise RuntimeError(f"duration mismatch: {key}")

        generated_on = datetime.fromtimestamp(wav_path.stat().st_mtime, timezone.utc).date().isoformat()
        if generated_on != APPROVED_ON:
            raise RuntimeError(f"unexpected source file date: {key} {generated_on}")
        accepted = dict(receipt)
        accepted.update({
            "status": "accepted_for_demo_prologue_pending_sound_mastering",
            "generation_date_utc_from_source_mtime": generated_on,
            "voice_passport": {
                "avatar": avatar, "voice_id": VOICES[avatar],
                "gender": EXPECTED_GENDER[avatar],
                "description_ref": "manual/voice/prologue-pilot.md",
            },
            "acceptance": {
                "date": APPROVED_ON,
                "scope": "demo_prologue",
                "by": "human_project_owner",
                "statement": APPROVAL,
                "original_receipt_sha256": digest(receipt_bytes),
            },
        })
        pending.append((DEST / f"{key}.wav", audio))
        pending.append((DEST / f"{key}.json", encoded(accepted)))
        items.append({
            "key": key, "avatar": avatar, "voice": VOICES[avatar],
            "wav": f"{key}.wav", "receipt": f"{key}.json",
            "rev": rev, "text_sha256": receipt["text_sha256"],
            "wav_sha256": receipt["wav_sha256"],
        })
        totals["requests"] += 1
        totals["input_tokens"] += receipt["usage"]["total_input_tokens"]
        totals["output_audio_tokens"] += receipt["usage"]["total_output_tokens"]
        totals["duration_seconds"] += duration
        totals["estimated_usd_from_usage"] += receipt["estimated_usd_from_usage"]

    manifest = {
        "scene": "scene.start.prologue", "scope": "demo_prologue",
        "status": "accepted_by_human_pending_sound_mastering",
        "acceptance_date": APPROVED_ON, "acceptance_statement": APPROVAL,
        "source": str(SOURCE), "description_ref": "manual/voice/prologue-pilot.md",
        "audio_format": "mono PCM16 WAV, 24000 Hz, unchanged TTS original",
        "mastering_owner": "sound", "mastering_status": "pending",
        "subtitle_authority": "db/story.db, approved_rev=2",
        "totals": totals, "lines": items,
    }
    pending.append((DEST / "manifest.json", encoded(manifest)))
    DEST.mkdir(parents=True, exist_ok=True)
    for path, data in pending:
        keep_exact(path, data)
    print(f"accepted {len(items)} demo-prologue originals in {DEST}; "
          f"source cost ${totals['estimated_usd_from_usage']:.6f}")


if __name__ == "__main__":
    main()

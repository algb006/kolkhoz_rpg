#!/usr/bin/env python3
"""Up to three natural, unaccepted short-t8 auditions per selected avatar."""

import hashlib
import json
from pathlib import Path
import sys

from voice_prologue_lines import approved_lines
from voice_prologue_probe import EXPECTED_GENDER, VOICES, verified_voice_gender
from voice_prologue_v2 import MODEL, STYLES, request_line


ROOT = Path(__file__).resolve().parent.parent
ACCEPTED = ROOT / "voice/accepted/prologue"
DEST = Path("/data/kolkhoz/voice/prologue/v2-t8")
AVATARS = ("dealer", "ex_chairman", "old_fighter")
CAP_USD = 0.30
MAX_CANDIDATES = 3
TARGET_SECONDS = 7.5
SAFETY_USD_PER_REQUEST = 0.006
DELIVERY = (
    "Мысль звучит естественно и законченно, без затяжных пауз между фразами; "
    "не ускорять и не сжимать речь искусственно."
)


def spent():
    return sum(
        json.loads(path.read_text(encoding="utf-8"))["estimated_usd_from_usage"]
        for path in DEST.rglob("scene.start.prologue.*.json")
    )


def approved_t8(avatar):
    rows = [row for row in approved_lines(avatar) if row[0].endswith(".t8")]
    if len(rows) != 1:
        raise RuntimeError(f"missing approved t8 for {avatar}")
    key, words, rev, approved = rows[0]
    accepted = json.loads((ACCEPTED / f"{key}.json").read_text(encoding="utf-8"))
    if (rev, approved) != (2, 2) or accepted["text"] != words:
        raise RuntimeError(f"accepted t8 differs from current text: {key}")
    if accepted["voice"] != VOICES[avatar] or accepted["style"] != STYLES[avatar]:
        raise RuntimeError(f"accepted v2 voice/style differs: {key}")
    return key, words, rev, accepted


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("dry-run", "generate"):
        raise SystemExit("usage: voice_prologue_t8_short.py <dry-run|generate>")
    mode = sys.argv[1]
    for avatar in AVATARS:
        key, words, rev, accepted = approved_t8(avatar)
        style = f"{accepted['style']} {DELIVERY}"
        if mode == "dry-run":
            print(f"{avatar}\t{key}\trev={rev}\t{VOICES[avatar]}\t{words}\t{style}")
            continue
        verified_voice_gender(VOICES[avatar], EXPECTED_GENDER[avatar])
        for number in range(1, MAX_CANDIDATES + 1):
            candidate_dir = DEST / avatar / f"c{number}"
            wav_path = candidate_dir / f"{key}.wav"
            receipt_path = candidate_dir / f"{key}.json"
            if wav_path.exists() and receipt_path.exists():
                print(f"skip existing {avatar} c{number}", flush=True)
                continue
            if wav_path.exists() or receipt_path.exists():
                raise RuntimeError(f"partial output exists: {candidate_dir}")
            if spent() + SAFETY_USD_PER_REQUEST > CAP_USD:
                raise RuntimeError("t8 budget cap nearly reached; stop before next request")
            STYLES[avatar] = style
            audio, receipt = request_line(key, words, rev, avatar)
            receipt["candidate"] = f"c{number}"
            receipt["target_duration_seconds"] = TARGET_SECONDS
            receipt["accepted_v2_wav_sha256"] = accepted["wav_sha256"]
            receipt["status"] = "short_t8_candidate_not_accepted"
            if receipt["text_sha256"] != hashlib.sha256(words.encode("utf-8")).hexdigest():
                raise RuntimeError("generated text hash changed")
            candidate_dir.mkdir(parents=True, exist_ok=True)
            with wav_path.open("xb") as output:
                output.write(audio)
            with receipt_path.open("x", encoding="utf-8") as output:
                json.dump(receipt, output, ensure_ascii=False, indent=2)
                output.write("\n")
            print(f"{avatar} c{number}: {receipt['duration_seconds']:.2f}s, "
                  f"USD={receipt['estimated_usd_from_usage']:.6f}", flush=True)


if __name__ == "__main__":
    main()

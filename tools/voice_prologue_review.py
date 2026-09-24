#!/usr/bin/env python3
"""Validate draft WAV receipts and build listening-only avatar reels."""

import hashlib
import json
from pathlib import Path
import sqlite3
import wave

from voice_prologue_probe import VOICES


ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "db/story.db"
VOICE_ROOT = Path("/data/kolkhoz/voice/prologue")
LINES = VOICE_ROOT / "lines"
REVIEW = VOICE_ROOT / "review"
NAMES = {
    "acting": "Временная", "dealer": "Делец",
    "ex_chairman": "Бывший председатель", "old_fighter": "Вояка",
    "promoted": "Назначенец", "student": "Студент",
    "villager": "Деревенский", "worker": "Рабочий",
}


def main():
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    rows = con.execute(
        "SELECT key,text,rev,approved_rev FROM line "
        "WHERE key LIKE 'scene.start.prologue.%' AND deprecated=0 ORDER BY key"
    ).fetchall()
    con.close()
    if len(rows) != 64:
        raise RuntimeError(f"expected 64 prologue lines; got {len(rows)}")
    by_avatar = {avatar: [] for avatar in VOICES}
    usage = {"requests": 0, "input_tokens": 0, "output_tokens": 0,
             "seconds": 0.0, "usd": 0.0}
    for key, text, rev, approved in rows:
        avatar = key.split(".")[3]
        wav_path = LINES / f"{key}.wav"
        receipt = json.loads((LINES / f"{key}.json").read_text(encoding="utf-8"))
        audio = wav_path.read_bytes()
        if (rev != approved or receipt["key"] != key or receipt["text"] != text
                or receipt["rev"] != rev or receipt["approved_rev"] != approved
                or receipt["voice"] != VOICES[avatar]
                or receipt["text_sha256"] != hashlib.sha256(text.encode()).hexdigest()
                or receipt["wav_sha256"] != hashlib.sha256(audio).hexdigest()):
            raise RuntimeError(f"text/voice/revision/hash mismatch: {key}")
        with wave.open(str(wav_path), "rb") as wav:
            if (wav.getnchannels(), wav.getframerate(), wav.getsampwidth()) != (1, 24000, 2):
                raise RuntimeError(f"bad WAV format: {key}")
            frames = wav.readframes(wav.getnframes())
        by_avatar[avatar].append((key, text, frames))
        usage["requests"] += 1
        usage["input_tokens"] += receipt["usage"]["total_input_tokens"]
        usage["output_tokens"] += receipt["usage"]["total_output_tokens"]
        usage["seconds"] += receipt["duration_seconds"]
        usage["usd"] += receipt["estimated_usd_from_usage"]
    REVIEW.mkdir(parents=True, exist_ok=True)
    lines = ["# Прослушивание пролога", "",
             "Это **черновые**, не принятые дубли Gemini 3.8 Flash TTS. "
             "В монтажах между репликами вставлено 0,6 секунды тишины; "
             "в исходных WAV тишины нет. Слова для игры берутся из субтитров rev=2.", ""]
    silence = b"\0" * int(0.6 * 24000 * 2)
    for avatar, records in by_avatar.items():
        if len(records) != 8:
            raise RuntimeError(f"expected 8 lines for {avatar}; got {len(records)}")
        output = REVIEW / f"{avatar}-all.wav"
        with wave.open(str(output), "wb") as wav:
            wav.setnchannels(1)
            wav.setframerate(24000)
            wav.setsampwidth(2)
            for index, (_, _, frames) in enumerate(records):
                if index:
                    wav.writeframes(silence)
                wav.writeframes(frames)
        lines.extend([f"## {NAMES[avatar]} — {VOICES[avatar]}", "",
                      f"[Слушать все восемь мыслей](review/{avatar}-all.wav)", ""])
        for key, text, _ in records:
            lines.append(f"- [{key.rsplit('.', 1)[-1]}](lines/{key}.wav): {text}")
        lines.append("")
    lines.extend(["## Счёт игрового прохода", "",
                  f"{usage['requests']} запросов · {usage['input_tokens']} входных токенов · "
                  f"{usage['output_tokens']} выходных аудиотокенов · "
                  f"{usage['seconds']:.2f} секунды · ${usage['usd']:.6f}.", "",
                  "Пробы голосов (8 запросов, $0,005394) учтены отдельно.", ""])
    (VOICE_ROOT / "REVIEW.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"validated {usage['requests']} lines; {usage['seconds']:.2f}s; "
          f"in={usage['input_tokens']} out={usage['output_tokens']} "
          f"USD={usage['usd']:.6f}; reels={len(by_avatar)}")


if __name__ == "__main__":
    main()

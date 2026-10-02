#!/usr/bin/env python3
"""Add eight draft plan-sketch thoughts without changing accepted office lines."""

import csv
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parent.parent
SOURCE = "manual/texts/office-plan-sketch-thoughts.tsv"
PREFIX = "scene.office_intro.plan_sketch."
AVATARS = (
    "villager", "worker", "student", "ex_chairman", "promoted",
    "old_fighter", "dealer", "acting",
)


def source_rows():
    with (ROOT / SOURCE).open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file, delimiter="\t"))
    expected = {"office_intro.plan_sketch." + avatar for avatar in AVATARS}
    if len(rows) != 8 or {row["key"] for row in rows} != expected:
        raise ValueError("Ожидались ровно восемь мыслей plan_sketch")
    for row in rows:
        if (row["namespace"], row["kind"], row["status"], row["placeholders"], row["plural"]) != (
                "scene", "body", "review", "{}", "0"):
            raise ValueError("Неверный паспорт строки: " + row["key"])
        if any(not row[field].strip() for field in ("text", "context", "meaning", "intent", "keep")):
            raise ValueError("Пустое поле строки: " + row["key"])
        if row["example"] != row["text"]:
            raise ValueError("Пример отличается от буквального текста")
    return rows


def values(row):
    avatar = row["key"].rsplit(".", 1)[1]
    return {
        "key": "scene." + row["key"], "scene_key": "scene.start.office",
        "namespace": "scene", "kind": "spoken_thought", "speaker_slot": "chairman",
        "variant_key": "office_intro.plan_sketch",
        "grammatical_gender": "female" if avatar == "acting" else "male",
        "thought_avatar": avatar, "thought_place": "office",
        "thought_trigger_kind": "item", "thought_trigger_ref": "office_intro.plan_sketch",
        "condition_ref": f"Выбран avatar.key={avatar}; первый осмотр plan_sketch.",
        **{field: row[field] for field in ("text", "context", "meaning", "intent", "keep")},
        "source_ref": SOURCE, "sort": (AVATARS.index(avatar) + 1) * 100 + 21,
    }


def apply_rows(con, rows):
    """Caller owns the transaction. No approval is inferred from a work order."""
    con.row_factory = sqlite3.Row
    before = [tuple(row) for row in con.execute(
        "SELECT * FROM line WHERE key NOT LIKE ? ORDER BY key", (PREFIX + "%",))]
    inserted = 0
    for row in rows:
        record = values(row)
        existing = con.execute("SELECT * FROM line WHERE key=?", (record["key"],)).fetchone()
        if existing is not None:
            if any(existing[field] != value for field, value in record.items()):
                raise ValueError("Автоматическая перезапись запрещена: " + record["key"])
            continue
        fields = list(record)
        con.execute("INSERT INTO line(" + ",".join(fields) + ") VALUES(" +
                    ",".join("?" for _ in fields) + ")", list(record.values()))
        inserted += 1
    after = [tuple(row) for row in con.execute(
        "SELECT * FROM line WHERE key NOT LIKE ? ORDER BY key", (PREFIX + "%",))]
    if before != after:
        raise RuntimeError("Изменились строки вне восьми новых мыслей")
    if con.execute("PRAGMA foreign_key_check").fetchall():
        raise RuntimeError("Нарушены связи собственной базы")
    exported = dict(con.execute(
        "SELECT full_key,text FROM string_source WHERE full_key LIKE ?", (PREFIX + "%",)))
    if exported != {"scene." + row["key"]: row["text"] for row in rows}:
        raise RuntimeError("Поставка string_source отличается от TSV")
    return inserted


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("dry-run", "apply"):
        raise SystemExit("usage: office_plan_sketch_lines.py <dry-run|apply>")
    rows = source_rows()
    if sys.argv[1] == "dry-run":
        print("Проверено: 8 новых текстов, 0 правок, 0 запросов API")
        return
    con = sqlite3.connect((ROOT / "db/story.db").resolve().as_uri() + "?mode=rw", uri=True)
    con.execute("PRAGMA foreign_keys=ON")
    try:
        with con:
            inserted = apply_rows(con, rows)
    finally:
        con.close()
    print(f"Добавлено: {inserted}; утверждение не выставляется, TTS не запускался")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Validate English draft batches against captured and live Russian sources."""
import csv
import json
from pathlib import Path
import re
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
PARAM = re.compile(r"\{(\w+)\}")
PLURAL = re.compile(r"\|plural\(([^()]*)\)")


def main():
    connection = sqlite3.connect(
        f"file:{ROOT.parent / 'db/strings.db'}?mode=ro", uri=True
    )
    errors = []
    total = 0
    seen = set()
    for path in sorted((ROOT / "manual/texts/en").glob("demo-batch*.tsv")):
        batch = re.search(r"batch\d+", path.name).group()
        snapshot = ROOT / "ai/localization-en-1828-2026-11-17" / f"{batch}-source.json"
        sources = {
            (row["namespace"], row["key"]): row
            for row in json.loads(snapshot.read_text())
        }
        with path.open(newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            if reader.fieldnames != ["namespace", "key", "rev", "en"]:
                errors.append(f"{path.name}: incorrect TSV header")
            rows = list(reader)
        actual = {(row["namespace"], row["key"]) for row in rows}
        if actual != set(sources) or len(rows) != len(actual):
            errors.append(f"{path.name}: source coverage or duplicate mismatch")
        for row in rows:
            key = (row["namespace"], row["key"])
            label = ".".join(key)
            if key in seen:
                errors.append(f"{label}: duplicated across batches")
            seen.add(key)
            source = sources.get(key)
            if source is None:
                continue
            text = row["en"]
            if row["rev"] != str(source["rev"]):
                errors.append(f"{label}: captured revision mismatch")
            live = connection.execute(
                "SELECT rev, source_text FROM string_source "
                "WHERE namespace=? AND key=? AND deprecated=0", key
            ).fetchone()
            if live != (source["rev"], source["source_text"]):
                errors.append(f"{label}: Russian source changed; re-review required")
            if set(PARAM.findall(text)) != set(PARAM.findall(source["source_text"])):
                errors.append(f"{label}: placeholder mismatch")
            if not text or text != text.strip() or re.search(r"[\t\r\nА-Яа-яЁё]", text):
                errors.append(f"{label}: empty, whitespace or untranslated Cyrillic")
            if source["max_len"] is not None and len(text) > source["max_len"]:
                errors.append(f"{label}: {len(text)} exceeds {source['max_len']}")
            plurals = PLURAL.findall(text)
            if bool(plurals) != bool(source["plural"]):
                errors.append(f"{label}: plural flag mismatch")
            for expression in plurals:
                forms = [part.split("=", 1)[0] for part in expression.split(",")]
                if sorted(forms) != ["one", "other"]:
                    errors.append(f"{label}: English plural needs one,other")
            total += 1
    connection.close()
    for error in errors:
        print(error)
    print(f"English draft validation: {total} rows, {len(errors)} errors")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())

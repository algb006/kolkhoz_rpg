#!/usr/bin/env python3
"""Preview an EN TSV import on a private snapshot of the shared strings catalog.

Usage: python3 -B tools/preview-english-import.py BATCH.tsv
Verifies the exact text and source revision of every row after draft import.
The importer can report success while preserving a different accepted row.
"""

import argparse
from contextlib import closing
from pathlib import Path
import sqlite3
import sys
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SHARED_TOOLS = ROOT.parent / "tools"
SHARED_DB = ROOT.parent / "db" / "strings.db"
sys.path.insert(0, str(SHARED_TOOLS))
import strings  # noqa: E402


class PreviewConnection(sqlite3.Connection):
    def close(self):
        """Let the importer finish while retaining the snapshot for verification."""


def read_batch(path):
    rows = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
        if not line.strip() or line.startswith(("#", "namespace\tkey\t")):
            continue
        fields = line.split("\t")
        if len(fields) != 4:
            raise ValueError(f"Line {number}: expected namespace, key, revision and text")
        namespace, key, revision, text = fields
        if not namespace or not key or not revision.isdecimal() or not text.strip():
            raise ValueError(f"Line {number}: incomplete or invalid row")
        if (namespace, key) in rows:
            raise ValueError(f"Line {number}: duplicate {namespace}/{key}")
        rows[namespace, key] = int(revision), text
    if not rows:
        raise ValueError("Expected a nonempty string TSV")
    return rows


def preview(path, rows, connection):
    with patch.object(strings, "connect", return_value=connection):
        if strings.cmd_import([str(path), "--locale", "en", "--status", "draft"]):
            return 1

    mismatches = []
    for (namespace, key), expected in rows.items():
        row = connection.execute(
            """SELECT t.src_rev, t.text FROM string_source v
               JOIN translation t ON t.string_id = v.string_id
               JOIN locale l ON l.id = t.locale_id
               WHERE v.namespace = ? AND v.key = ? AND l.key = 'en'""",
            (namespace, key),
        ).fetchone()
        if row is None or tuple(row) != expected:
            mismatches.append(f"{namespace}/{key}")
    for key in mismatches:
        print(f"Preview mismatch: {key}. Check the accepted EN row and source revision.")
    print(f"Verified exact text and revision for {len(rows) - len(mismatches)}/{len(rows)} rows")
    return int(bool(mismatches))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", type=Path, help="four-column EN string TSV")
    args = parser.parse_args()
    try:
        rows = read_batch(args.batch)
        snapshot = sqlite3.connect(":memory:", factory=PreviewConnection)
        try:
            with closing(sqlite3.connect(SHARED_DB.as_uri() + "?mode=ro", uri=True)) as source:
                source.backup(snapshot)
            snapshot.row_factory = sqlite3.Row
            snapshot.execute("PRAGMA foreign_keys = ON")
            return preview(args.batch, rows, snapshot)
        finally:
            sqlite3.Connection.close(snapshot)
    except (OSError, ValueError, sqlite3.Error) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    raise SystemExit(main())

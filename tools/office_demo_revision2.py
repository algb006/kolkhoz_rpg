#!/usr/bin/env python3
"""Apply only the 24 office thoughts approved in mailbox move 19."""

import csv
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parent.parent
SOURCE = 'manual/texts/orders-clerk-journal-demo-2026-10-12.csv'
AVATARS = {'villager', 'worker', 'student', 'ex_chairman', 'promoted',
           'old_fighter', 'dealer', 'acting'}
ITEMS = {'enter', 'notebooks', 'journal'}


def main():
    with (ROOT / SOURCE).open(encoding='utf-8', newline='') as handle:
        rows = [row for row in csv.DictReader(handle) if row['namespace'] == 'scene']
    expected = {f'scene.office_intro.{item}.{avatar}'
                for item in ITEMS for avatar in AVATARS}
    keys = ['scene.' + row['key'] for row in rows]
    if len(rows) != 24 or set(keys) != expected:
        raise RuntimeError('Expected exactly three existing eight-avatar groups')
    con = sqlite3.connect((ROOT / 'db/story.db').resolve().as_uri() + '?mode=rw', uri=True)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    con.execute('ATTACH DATABASE ? AS shared',
                ((ROOT.parent / 'db/strings.db').resolve().as_uri() + '?mode=ro',))
    changed = 0
    try:
        with con:
            before = {row['key']: tuple(row) for row in con.execute('SELECT * FROM line ORDER BY key')
                      if row['key'] not in expected}
            voice_before = {table: con.execute(f'SELECT * FROM {table} ORDER BY 1').fetchall()
                            for table in ('voice_take', 'voice_file')}
            for source, key in zip(rows, keys):
                row = con.execute('SELECT * FROM line WHERE key=?', (key,)).fetchone()
                if (row is None or row['scene_key'] != 'scene.start.office'
                        or row['namespace'] != 'scene' or row['deprecated']
                        or row['kind'] != 'spoken_thought'
                        or row['thought_avatar'] != key.rsplit('.', 1)[1]):
                    raise RuntimeError('Unexpected thought identity: ' + key)
                fields = ('text', 'meaning', 'intent', 'keep')
                wanted = (source['text_ru'], source['meaning'], source['intent'], source['keep'])
                if row['rev'] == 2:
                    if (row['approved_rev'] != 2 or tuple(row[f] for f in fields) != wanted
                            or row['source_ref'] != SOURCE):
                        raise RuntimeError('Refusing a different revision 2: ' + key)
                    continue
                if row['rev'] != 1 or row['approved_rev'] != 1:
                    raise RuntimeError('Expected approved revision 1: ' + key)
                shared = con.execute(
                    "SELECT s.rev,s.approved_rev,t.text FROM shared.string s "
                    "JOIN shared.namespace n ON n.id=s.namespace_id "
                    "JOIN shared.translation t ON t.string_id=s.id "
                    "JOIN shared.locale l ON l.id=t.locale_id "
                    "WHERE n.key='scene' AND s.key=? AND l.key='ru'", (source['key'],)).fetchone()
                if shared is None or tuple(shared) != (1, 1, row['text']):
                    raise RuntimeError('Baseline DB mismatch before approved update: ' + key)
                con.execute('UPDATE line SET text=?,meaning=?,intent=?,keep=?,source_ref=? WHERE key=?',
                            (*wanted, SOURCE, key))
                if con.execute('SELECT rev FROM line WHERE key=?', (key,)).fetchone()[0] != 2:
                    raise RuntimeError('Revision trigger did not produce 2: ' + key)
                con.execute('UPDATE line SET approved_rev=2 WHERE key=?', (key,))
                changed += 1
            after = {row['key']: tuple(row) for row in con.execute('SELECT * FROM line ORDER BY key')
                     if row['key'] not in expected}
            if before != after:
                raise RuntimeError('Unrelated story lines changed')
            for table, saved in voice_before.items():
                if saved != con.execute(f'SELECT * FROM {table} ORDER BY 1').fetchall():
                    raise RuntimeError('Historical voice ledger changed: ' + table)
            if con.execute('PRAGMA foreign_key_check').fetchall():
                raise RuntimeError('Story foreign-key violation')
    finally:
        con.close()
    print(f'Office rev2: {changed} changed; {24-changed} already exact; no shared DB/audio writes')


if __name__ == '__main__':
    main()

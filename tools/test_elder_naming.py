#!/usr/bin/env python3
"""Check elder naming and the non-destructive pocketbook key handoff."""

import csv
import json
from pathlib import Path
import re
import sqlite3
import unittest

import elder_lines
from voice_office_intro import has_embedded_name


ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / 'manual/texts/named-pages-elder-key-migration.tsv'
AVATARS = {'villager', 'worker', 'student', 'ex_chairman', 'promoted',
           'old_fighter', 'dealer', 'acting'}


class ElderNamingTests(unittest.TestCase):
    def test_migration_keeps_old_rows_and_exact_payload(self):
        with PACKET.open(encoding='utf-8', newline='') as stream:
            rows = list(csv.DictReader(stream, delimiter='\t'))
        self.assertEqual(len(rows), 32)
        current = {r['key']: r for r in rows if r['deprecated'] == '0'}
        retired = [r for r in rows if r['deprecated'] == '1']
        self.assertEqual(len(current), 16)
        self.assertEqual(len(retired), 16)
        self.assertEqual(len({r['source_id'] for r in rows}), 16)
        for row in retired:
            successor = current[row['replaced_by']]
            self.assertNotEqual(row['key'], successor['key'])
            self.assertTrue(successor['key'].startswith('pocketbook.elder.'))
            self.assertEqual(successor['replaced_by'], '')
            for field in ('namespace', 'kind', 'text', 'context', 'meaning',
                          'intent', 'keep', 'placeholders', 'plural',
                          'source_id', 'source_rev', 'source_approved_rev'):
                self.assertEqual(row[field], successor[field], field)
            self.assertEqual(successor['status'], 'review')
            self.assertEqual(successor['text'], successor['example'])
            params = json.loads(successor['placeholders'])
            self.assertEqual(set(params), set(re.findall(r'\{([a-z_]+)\}', row['text'])))
            self.assertTrue(all(p['kind'] == 'name' for p in params.values()))
        for group in ('neutral', 'history.church'):
            self.assertEqual(
                {key.rsplit('.', 1)[1] for key in current
                 if key.startswith(f'pocketbook.elder.{group}.')}, AVATARS)
        history = current['pocketbook.elder.history.church.villager']
        self.assertEqual((history['source_rev'], history['source_approved_rev']), ('2', '1'))

    def test_character_uses_party_name_and_existing_references(self):
        with sqlite3.connect(f'file:{ROOT / "db/story.db"}?mode=ro', uri=True) as con:
            row = con.execute(
                "SELECT title,display_name,gender FROM character WHERE key='elder'"
            ).fetchone()
            self.assertEqual(row, ('Бывший староста', '{person_address}', 'male'))
            self.assertEqual(con.execute('PRAGMA foreign_key_check').fetchall(), [])
            self.assertEqual(con.execute(
                "SELECT count(*) FROM cast_slot WHERE key='elder' AND character_key='elder'"
            ).fetchone()[0], 7)

    def test_seed_dialogue_matches_current_name_free_sources(self):
        with sqlite3.connect(':memory:') as con:
            con.executescript((ROOT / 'db/schema.sql').read_text(encoding='utf-8'))
            elder_lines.setup(con)
            elder_lines.first_meeting(con)
            elder_lines.resident_and_name(con)
            source = sqlite3.connect(f'file:{ROOT / "db/story.db"}?mode=ro', uri=True)
            try:
                for key in ('scene.elder.first_meeting.opening.chairman',
                            'scene.elder.first_meeting.opening.elder',
                            'scene.elder.first_meeting.coat.question.villager',
                            'scene.elder.first_meeting.coat.question.student',
                            'scene.elder.affected_resident_question.answer.cite_elder'):
                    self.assertEqual(con.execute('SELECT text FROM line WHERE key=?', (key,)).fetchone(),
                                     source.execute('SELECT text FROM line WHERE key=?', (key,)).fetchone())
            finally:
                source.close()

    def test_recorded_exit_thoughts_reject_other_embedded_names(self):
        self.assertFalse(has_embedded_name('Сначала найти старосту. Потом осмотреть село.'))
        self.assertFalse(has_embedded_name('Мне надо поговорить. Староста знает эти места.'))
        self.assertTrue(has_embedded_name('Сначала поговорить с Василием.'))
        self.assertTrue(has_embedded_name('Василий Петрович знает эти места.'))
        self.assertTrue(has_embedded_name('Найти {person_address}.'))


if __name__ == '__main__':
    unittest.main()

#!/usr/bin/env python3
"""Validate the initial elder note without editing shared strings or scenes."""

import csv
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
FIELDS = ('namespace', 'key', 'kind', 'text', 'context', 'meaning', 'intent',
          'keep', 'placeholders', 'status', 'example', 'plural')
TEXT = ('Здешний житель, бывший староста — теперь работает в колхозе со всеми. '
        'В голодное время не дал растащить оставшиеся запасы.')


class ElderAboutTests(unittest.TestCase):
    def setUp(self):
        with (ROOT / 'manual/texts/named-pages-elder-about.tsv').open(
                encoding='utf-8', newline='') as stream:
            reader = csv.DictReader(stream, delimiter='\t')
            self.assertEqual(tuple(reader.fieldnames), FIELDS)
            rows = list(reader)
        self.assertEqual(len(rows), 1)
        self.row = rows[0]

    def test_exact_payload(self):
        self.assertEqual(set(self.row), set(FIELDS))
        self.assertEqual(self.row['namespace'], 'ui.office')
        self.assertEqual(self.row['key'], 'directory.elder.about')
        self.assertEqual(self.row['kind'], 'body')
        self.assertEqual(self.row['text'], TEXT)
        self.assertEqual(self.row['example'], TEXT)
        self.assertEqual(TEXT.count('.'), 2)
        self.assertIn('бывший староста', TEXT)
        self.assertNotIn('{person_address}', TEXT)
        self.assertNotIn('{person_family}', TEXT)

    def test_translation_passport_and_initial_context(self):
        self.assertTrue(all(self.row[field].strip() for field in FIELDS))
        self.assertEqual(self.row['placeholders'], '{}')
        self.assertEqual(self.row['plural'], '0')
        self.assertEqual(self.row['status'], 'review')
        self.assertIn('ход 40', self.row['context'])
        self.assertIn('принят boss [43]', self.row['context'])
        self.assertIn('по прямой постановке boss [40]', self.row['context'])
        self.assertIn('председатель любого пола', self.row['keep'])
        self.assertIn('Это начальная запись после пролога', self.row['keep'])
        self.assertIn('без TTS', self.row['context'])
        self.assertFalse(any(char.isdigit() for char in TEXT))

    def test_directory_migration_creates_new_key_and_retires_original(self):
        with (ROOT / 'manual/texts/named-pages-elder-directory-migration.tsv').open(
                encoding='utf-8', newline='') as stream:
            rows = list(csv.DictReader(stream, delimiter='\t'))
        self.assertEqual(len(rows), 2)
        active, retired = rows
        self.assertEqual((active['deprecated'], retired['deprecated']), ('0', '1'))
        self.assertEqual(active['key'], self.row['key'])
        self.assertNotEqual(retired['key'], active['key'])
        self.assertEqual(retired['replaced_by'], active['key'])
        self.assertEqual(active['replaced_by'], '')
        for row in rows:
            self.assertEqual(row['text'], TEXT)
            self.assertEqual(row['example'], TEXT)
            self.assertEqual(row['placeholders'], '{}')
            self.assertEqual(row['source_id'], '20326')
            self.assertEqual(row['source_rev'], '2')
            self.assertEqual(row['source_approved_rev'], '')
        for field in FIELDS:
            self.assertEqual(active[field], self.row[field], field)

    def test_shared_note_has_no_personal_meeting_or_avatar_knowledge(self):
        self.assertIn('boss-rpg-office-portrait-promoted-logic-error-2026-10-02 [2]',
                      self.row['context'])
        for forbidden in ('я', 'меня', 'мне', 'мой', 'встретил', 'церкви',
                          'сюртуке', 'расспросить', 'знаю', 'помню'):
            self.assertNotIn(forbidden, TEXT.lower().split())
        self.assertIn('без первого лица', self.row['keep'])
        self.assertIn('не утверждать, знакомы ли', self.row['keep'])


if __name__ == '__main__':
    unittest.main()

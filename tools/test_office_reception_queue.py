#!/usr/bin/env python3
"""Validate the two office reception UI strings without database writes."""

import csv
from pathlib import Path
import unittest


SOURCE = Path(__file__).resolve().parents[1] / 'manual/texts/office-reception-queue.tsv'
FIELDS = ('namespace', 'key', 'kind', 'text', 'context', 'meaning', 'intent',
          'keep', 'placeholders', 'status', 'example', 'plural')


class ReceptionQueueTests(unittest.TestCase):
    def setUp(self):
        with SOURCE.open(encoding='utf-8', newline='') as stream:
            reader = csv.DictReader(stream, delimiter='\t')
            self.assertEqual(tuple(reader.fieldnames), FIELDS)
            self.rows = list(reader)

    def test_exact_payload(self):
        self.assertEqual(len(self.rows), 2)
        self.assertEqual(
            {(row['namespace'], row['key'], row['kind'], row['text']) for row in self.rows},
            {('ui.office', 'reception.visit_missed', 'body', 'Приходили, не застали'),
             ('ui.hud', 'reception.pending.tip', 'tooltip',
              'В «Приёме» есть просьбы без ответа.')})

    def test_translation_passports_and_review_gate(self):
        for row in self.rows:
            with self.subTest(key=row['key']):
                self.assertEqual(set(row), set(FIELDS))
                self.assertTrue(all(row[field].strip() for field in FIELDS))
                self.assertEqual(row['status'], 'review')
                self.assertEqual(row['placeholders'], '{}')
                self.assertEqual(row['plural'], '0')
                self.assertEqual(row['example'], row['text'])
                self.assertFalse(any(char.isdigit() for char in row['text']))


if __name__ == '__main__':
    unittest.main()

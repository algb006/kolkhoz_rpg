#!/usr/bin/env python3
"""Check additive imports and approval gates using memory-only fixtures."""

from copy import deepcopy
import sqlite3
import unittest

from office_plan_sketch_lines import ROOT, PREFIX, apply_rows, source_rows
from voice_office_intro import pending_approvals


class PlanSketchTests(unittest.TestCase):
    def setUp(self):
        source = sqlite3.connect((ROOT / 'db/story.db').resolve().as_uri() + '?mode=ro', uri=True)
        self.con = sqlite3.connect(':memory:')
        source.backup(self.con)
        source.close()
        self.con.execute('PRAGMA foreign_keys=ON')
        self.rows = source_rows()

    def tearDown(self):
        self.con.close()

    def test_insert_and_repeat_preserve_baseline(self):
        # Discard only the eight fixture additions in an isolated memory DB.
        self.con.execute('DELETE FROM line WHERE key LIKE ?', (PREFIX + '%',))
        self.con.commit()
        with self.con:
            self.assertEqual(apply_rows(self.con, self.rows), 8)
        with self.con:
            self.assertEqual(apply_rows(self.con, self.rows), 0)
        count = self.con.execute(
            "SELECT count(*) FROM line WHERE scene_key='scene.start.office' "
            "AND key NOT LIKE ? AND approved_rev=rev", (PREFIX + '%',)
        ).fetchone()[0]
        self.assertEqual(count, 160)

    def test_differing_existing_text_is_not_overwritten(self):
        with self.con:
            apply_rows(self.con, self.rows)
        altered = deepcopy(self.rows)
        altered[0]['text'] += ' Проверка.'
        with self.assertRaises(ValueError), self.con:
            apply_rows(self.con, altered)
        actual = self.con.execute('SELECT text FROM line WHERE key=?',
                                  ('scene.' + self.rows[0]['key'],)).fetchone()[0]
        self.assertEqual(actual, self.rows[0]['text'])

    def test_unimported_line_is_blocked_even_if_locally_approved(self):
        row = dict(key=PREFIX + 'villager', rev=1, approved_rev=1,
                   string_rev=None, string_approved_rev=None)
        self.assertEqual(pending_approvals([row]), [row['key']])

    def test_stale_approval_is_blocked(self):
        row = dict(key=PREFIX + 'villager', rev=2, approved_rev=1,
                   string_rev=2, string_approved_rev=1)
        self.assertEqual(pending_approvals([row]), [row['key']])

    def test_matching_approvals_are_ready(self):
        row = dict(key=PREFIX + 'villager', rev=1, approved_rev=1,
                   string_rev=1, string_approved_rev=1)
        self.assertEqual(pending_approvals([row]), [])


if __name__ == '__main__':
    unittest.main()

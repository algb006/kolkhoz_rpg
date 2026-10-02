#!/usr/bin/env python3
"""Check additive imports and approval gates using memory-only fixtures."""

from copy import deepcopy
import sqlite3
import unittest

from office_plan_sketch_lines import ROOT, PREFIX, apply_rows, source_rows
from voice_office_intro import pending_approvals
from office_additions_package import duration_status


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
        # Remove only the additions and their voice references in the memory fixture.
        # The live accepted sources and the old portrait history remain untouched.
        voice_refs = 'SELECT key FROM voice_take WHERE line_key LIKE ?'
        self.con.execute(
            'DELETE FROM voice_measurement WHERE file_path IN '
            f'(SELECT path FROM voice_file WHERE take_key IN ({voice_refs}))', (PREFIX + '%',))
        self.con.execute(
            f"DELETE FROM voice_file WHERE take_key IN ({voice_refs}) AND file_role='technical_master'",
            (PREFIX + '%',))
        self.con.execute(f'DELETE FROM voice_file WHERE take_key IN ({voice_refs})', (PREFIX + '%',))
        self.con.execute('DELETE FROM voice_take WHERE line_key LIKE ?', (PREFIX + '%',))
        self.con.execute('DELETE FROM line WHERE key LIKE ?', (PREFIX + '%',))
        baseline = self.con.execute('SELECT * FROM line ORDER BY key').fetchall()
        baseline_takes = self.con.execute('SELECT * FROM voice_take ORDER BY key').fetchall()
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
        self.assertEqual([tuple(row) for row in self.con.execute(
            'SELECT * FROM line WHERE key NOT LIKE ? ORDER BY key', (PREFIX + '%',)
        )], baseline)
        self.assertEqual([tuple(row) for row in self.con.execute(
            'SELECT * FROM voice_take ORDER BY key')], baseline_takes)
        self.assertEqual(self.con.execute('PRAGMA foreign_key_check').fetchall(), [])

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

    def test_additions_duration_policy_does_not_cut_at_eight(self):
        self.assertEqual(duration_status(8.6), 'source_for_mastering_not_hearing_accepted')
        self.assertEqual(duration_status(11), 'source_for_mastering_not_hearing_accepted')
        self.assertEqual(duration_status(11.0001), 'rejected_over_duration_limit')


if __name__ == '__main__':
    unittest.main()

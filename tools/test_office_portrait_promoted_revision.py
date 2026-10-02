#!/usr/bin/env python3
"""Test the single-line correction and preserve other text and voice history."""

import sqlite3
import unittest

from office_portrait_promoted_revision import KEY, OLD_TEXT, ROOT, TEXT, apply_revision
from office_intro_lines import corpus
from voice_office_intro import pending_approvals


class PromotedPortraitRevisionTests(unittest.TestCase):
    def setUp(self):
        self.con = sqlite3.connect(':memory:')
        with sqlite3.connect((ROOT / 'db/story.db').resolve().as_uri() + '?mode=ro', uri=True) as source:
            source.backup(self.con)
        # Reset only the target in memory, so tests work before and after import.
        self.con.execute('UPDATE line SET text=? WHERE key=?', (OLD_TEXT, KEY))
        self.con.execute('UPDATE line SET rev=2,approved_rev=2 WHERE key=?', (KEY,))
        self.con.commit()
        self.con.execute('PRAGMA foreign_keys=ON')

    def tearDown(self):
        self.con.close()

    def test_one_revision_and_idempotence_preserve_relatives_and_takes(self):
        others = self.con.execute('SELECT * FROM line WHERE key<>? ORDER BY key', (KEY,)).fetchall()
        takes = self.con.execute('SELECT * FROM voice_take ORDER BY key').fetchall()
        with self.con:
            self.assertEqual(apply_revision(self.con), 1)
        with self.con:
            self.assertEqual(apply_revision(self.con), 0)
        self.assertEqual(self.con.execute('SELECT text,rev,approved_rev FROM line WHERE key=?',
                                        (KEY,)).fetchone(), (TEXT, 3, None))
        self.assertEqual(others, self.con.execute('SELECT * FROM line WHERE key<>? ORDER BY key',
                                                (KEY,)).fetchall())
        self.assertEqual(takes, self.con.execute('SELECT * FROM voice_take ORDER BY key').fetchall())

    def test_unknown_source_is_not_overwritten(self):
        self.con.execute('UPDATE line SET text=? WHERE key=?', ('Другая редакция.', KEY))
        self.con.commit()
        before = self.con.execute('SELECT * FROM line WHERE key=?', (KEY,)).fetchone()
        with self.assertRaises(ValueError), self.con:
            apply_revision(self.con)
        self.assertEqual(before, self.con.execute('SELECT * FROM line WHERE key=?', (KEY,)).fetchone())

    def test_corpus_and_approval_gate(self):
        self.assertEqual(corpus()['portrait', 'promoted'], TEXT)
        self.assertNotIn('обком', TEXT.lower())
        self.assertIn('портрет я знаю наизусть', TEXT)
        self.assertIn('Куда же я попал?', TEXT)
        row = dict(key=KEY, rev=3, approved_rev=None, string_rev=2, string_approved_rev=2)
        self.assertEqual(pending_approvals([row]), [KEY])


if __name__ == '__main__':
    unittest.main()

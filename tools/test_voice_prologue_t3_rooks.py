"""No-network scope, approval and voice-regression checks for the t3 delta."""

import unittest

import voice_prologue_t3_rooks as t3


class T3RooksTests(unittest.TestCase):
    def approved_row(self):
        return {'key': 'scene.start.prologue.worker.t3', 'text': 'Текст.',
                'string_text': 'Текст.', 'rev': 3, 'approved_rev': 3,
                'string_rev': 3, 'string_approved_rev': 3}

    def test_scope_is_seven_t3_and_never_ex_chairman(self):
        rows = t3.final_texts()
        self.assertEqual(len(rows), 7)
        self.assertEqual({r['avatar'] for r in rows}, set(t3.AVATARS))
        self.assertNotIn('ex_chairman', t3.AVATARS)
        for row in rows:
            self.assertTrue(row['key'].endswith('.t3'))
            self.assertNotIn('кладбищ', row['text'].lower())
            self.assertNotIn('погост', row['text'].lower())

    def test_matching_approved_import_opens_gate(self):
        self.assertEqual(t3.pending([self.approved_row()]), [])

    def test_any_approval_revision_or_text_mismatch_closes_gate(self):
        for field, value in (('rev', 2), ('approved_rev', None),
                             ('string_rev', 2), ('string_approved_rev', None),
                             ('string_text', 'Иной текст.')):
            with self.subTest(field=field):
                row = self.approved_row()
                row[field] = value
                self.assertEqual(t3.pending([row]), [row['key']])

    def test_all_seven_settings_equal_accepted_v2(self):
        t3.validate_v2_settings(t3.final_texts())


if __name__ == '__main__':
    unittest.main()

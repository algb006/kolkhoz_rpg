"""Approval gates must fail before the replacement batch can call TTS."""

import unittest
from unittest.mock import patch

import voice_office_demo_rev2 as batch


class ApprovalGateTests(unittest.TestCase):
    def setUp(self):
        self.source = [dict(key=f'scene.office_intro.{item}.{avatar}', rev=2)
                       for item in batch.ITEMS for avatar in batch.VOICES]

    def select(self, source, pending=False):
        with patch.object(batch, 'source_rows', return_value=source), \
                patch.object(batch, 'pending_approvals', return_value=pending):
            return batch.rows()

    def test_exact_approved_set(self):
        self.assertEqual(len(self.select(self.source)), 24)

    def test_missing_key_rejected(self):
        with self.assertRaises(RuntimeError):
            self.select(self.source[:-1])

    def test_pending_approval_rejected(self):
        with self.assertRaises(RuntimeError):
            self.select(self.source, pending=True)

    def test_old_revision_rejected(self):
        self.source[0]['rev'] = 1
        with self.assertRaises(RuntimeError):
            self.select(self.source)


if __name__ == '__main__':
    unittest.main()

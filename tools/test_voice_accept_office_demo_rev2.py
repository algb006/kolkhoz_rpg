"""Read-only acceptance guards; no TTS or fixture writes."""
import unittest
from unittest.mock import patch
import voice_accept_office_demo_rev2 as acceptance


class AcceptanceTests(unittest.TestCase):
    def test_complete_delivery(self):
        pending = acceptance.prepare()
        self.assertEqual(len(pending), 49)
        self.assertEqual(sum(p.suffix == '.wav' for p, _ in pending), 24)
        self.assertTrue(all(p.parent == acceptance.DEST for p, _ in pending))

    def test_partial_rows_rejected(self):
        with patch.object(acceptance, 'rows', return_value=[]):
            with self.assertRaisesRegex(ValueError, 'Missing or duplicate'):
                acceptance.prepare()

    def test_no_human_receipt_rejected(self):
        with patch.object(acceptance, 'acceptance_block', side_effect=ValueError('Missing receipt')):
            with self.assertRaisesRegex(ValueError, 'Missing receipt'):
                acceptance.prepare()


if __name__ == '__main__':
    unittest.main()

"""Read-only acceptance regression tests; no API or file production."""
import copy
import unittest
from unittest.mock import patch
import voice_accept_office_portrait_rev3 as acceptance


class AcceptanceTests(unittest.TestCase):
    def change_hearing(self, **changes):
        original = acceptance.read_document

        def read(path):
            data, raw = original(path)
            if path == acceptance.EVIDENCE / 'hearing-acceptance.json':
                data = copy.deepcopy(data)
                data.update(changes)
            return data, raw
        return patch.object(acceptance, 'read_document', side_effect=read)

    def test_complete_validated_files(self):
        self.assertEqual(len(acceptance.prepare()), 3)

    def test_previous_revision_cannot_be_accepted(self):
        with self.change_hearing(rev=2):
            with self.assertRaisesRegex(ValueError, 'another date, key or revision'):
                acceptance.prepare()

    def test_different_source_rejected(self):
        with self.change_hearing(source_sha256='0' * 64):
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                acceptance.prepare()


if __name__ == '__main__':
    unittest.main()

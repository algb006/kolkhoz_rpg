"""Приёмка сверяет квитанцию и точные версии до записи; тесты только читают файлы."""
import copy
import unittest
from unittest.mock import patch

import voice_accept_office_additions as acceptance


class AcceptanceTests(unittest.TestCase):
    def test_complete_delivery(self):
        pending = acceptance.prepare()
        self.assertEqual(len(pending), 33)
        self.assertEqual(sum(p.suffix == '.wav' for p, _ in pending), 16)

    def changed_document(self, name, change):
        original = acceptance.read_document

        def read(path):
            data, raw = original(path)
            if path == acceptance.EVIDENCE / name:
                data = copy.deepcopy(data)
                change(data)
            return data, raw
        return patch.object(acceptance, 'read_document', side_effect=read)

    def test_partial_hearing_rejected(self):
        with self.changed_document('hearing-acceptance.json', lambda d: d.update(accepted_count=15)):
            with self.assertRaisesRegex(ValueError, 'полной квитанции'):
                acceptance.prepare()

    def test_old_portrait_cannot_substitute_new_source(self):
        def change(data):
            next(t for t in data['takes'] if '.portrait.' in t['key'])['rev'] = 1
        with self.changed_document('runtime-manifest.json', change):
            with self.assertRaisesRegex(ValueError, 'другому источнику'):
                acceptance.prepare()

    def test_duplicate_runtime_key_rejected(self):
        def change(data):
            data['takes'][-1] = copy.deepcopy(data['takes'][0])
        with self.changed_document('runtime-manifest.json', change):
            with self.assertRaisesRegex(ValueError, 'состав партии'):
                acceptance.prepare()


if __name__ == '__main__':
    unittest.main()

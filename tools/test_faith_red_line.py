#!/usr/bin/env python3
"""Check scoped author-source changes; this is not an LM runtime filter."""

from pathlib import Path
import re
import sqlite3
import unittest


ROOT = Path(__file__).resolve().parents[1]
RETIRED = {
    'dialogue.school_fears.teacher.full_lesson_no_tower',
    'dialogue.school_fears.witch.retelling_no_tower',
    'scene.school_fears.count_cloud.shape_no_tower',
}
FORBIDDEN = re.compile(r'\b(?:поп|попа|попу|попом|попы|попов)\b|опиум\s+народа',
                       re.IGNORECASE)


class FaithRedLineTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect((ROOT / 'db/story.db').as_uri() + '?mode=ro',
                                  uri=True)
        self.addCleanup(self.db.close)

    def test_retired_variants_preserve_history(self):
        rows = self.db.execute(
            "SELECT key,rev,approved_rev,deprecated,condition_ref,text FROM line "
            "WHERE key IN (?,?,?)", tuple(sorted(RETIRED))).fetchall()
        self.assertEqual({row[0] for row in rows}, RETIRED)
        for key, rev, approved, deprecated, condition, text in rows:
            with self.subTest(key=key):
                self.assertEqual((rev, approved, deprecated), (1, None, 1))
                self.assertIn('church_absent', condition)
                self.assertTrue(text)

    def test_active_lines_do_not_assume_church_demolition(self):
        rows = self.db.execute(
            "SELECT key FROM line WHERE deprecated=0 "
            "AND condition_ref LIKE '%church_absent%'").fetchall()
        self.assertEqual(rows, [])

    def test_active_speech_has_no_explicit_forbidden_terms(self):
        for key, text in self.db.execute(
                'SELECT key,text FROM line WHERE deprecated=0'):
            with self.subTest(key=key):
                self.assertIsNone(FORBIDDEN.search(text))
        self.assertIsNone(FORBIDDEN.search('Куда я попал?'))
        self.assertIsNotNone(FORBIDDEN.search('Попы'))

    def test_material_advice_matches_boss_wording(self):
        source = (ROOT / 'manual/texts/site-materials-lamp-tips.md').read_text()
        expected = {
            'stone': 'Разметьте карьер. Камень свален у развалин графской усадьбы.',
            'brick': ('Кирпича больше, чем на складе, в первой эпохе не взять; '
                      'со второй эпохи его можно заказать по лимиту.'),
        }
        for material, text in expected.items():
            rows = [row for row in source.splitlines()
                    if f'`site_without_materials.tip.{material}`' in row]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].split('|')[-2].strip(), text)

    def test_guard_source_does_not_claim_runtime_integration(self):
        source = (ROOT / 'manual/story/lm-guards.md').read_text()
        self.assertIn('не подтверждено', source)
        self.assertIn('не новый параметр API', source)
        self.assertIn('backdrop', source)
        self.assertIn('Владелец подключения — host', source)
        self.assertIn('подключение отложено', source)
        self.assertIn('Кладбище не переносят', source)
        self.assertIn('Характер, жаргон или', source)


if __name__ == '__main__':
    unittest.main()

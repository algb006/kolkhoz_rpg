"""Static proposal regressions; no databases, imports or file writes."""

import re
import unittest

from string_sweep_598 import NEW, REPLACEMENTS, SPECIAL


class SweepTests(unittest.TestCase):
    def test_no_technical_words_in_proposed_text(self):
        banned = re.compile(r'\b(тик\w*|юнит\w*|апгрейд\w*|перк\w*|компонент\w*)\b', re.I)
        for key, text in {**REPLACEMENTS, **NEW}.items():
            self.assertIsNone(banned.search(text), key)

    def test_release_variants_share_exact_binding(self):
        for key in ('ui.office.works.released_by_order', 'ui.office.works.released_by_order_f'):
            self.assertEqual(re.findall(r'\{(\w+)\}', NEW[key]), ['order_number'])
        self.assertTrue(NEW['ui.office.works.released_by_order'].startswith('Освобождён'))
        self.assertTrue(NEW['ui.office.works.released_by_order_f'].startswith('Освобождена'))

    def test_period_and_producer_gates(self):
        self.assertEqual(SPECIAL['ui.office.journal.tick'][0], 'binding_held')
        self.assertEqual(SPECIAL['feed.winter_sowing_lost'][0], 'producer_confirmation')
        self.assertIn('октября', REPLACEMENTS['feed.winter_sowing_lost'])
        self.assertEqual(SPECIAL['hint.hint_41.text'][0], 'design_formula_confirmation')

    def test_keys_unique_across_new_and_existing(self):
        self.assertFalse(set(NEW) & set(REPLACEMENTS))
        self.assertEqual(len(NEW) + len(REPLACEMENTS), 53)

    def test_not_a_new_quest_or_speech(self):
        self.assertTrue(all(k.startswith('ui.office.works.') for k in NEW))
        self.assertFalse(any(k.startswith(('scene.', 'dialogue.')) for k in REPLACEMENTS))


if __name__ == '__main__':
    unittest.main()

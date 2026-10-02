#!/usr/bin/env python3
"""Check content-side Esc coverage; do not modify host or shared databases."""

import csv
from pathlib import Path
import re
import sqlite3
import unittest


ROOT = Path(__file__).resolve().parents[1]


def rows(path):
    with (ROOT / path).open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream, delimiter='\t'))


class DialogueEscapeTests(unittest.TestCase):
    def setUp(self):
        self.registry = rows('ai/scene-registry.tsv')
        self.policy = rows('ai/dialogue-escape-policy.tsv')
        self.disputed = rows('ai/dialogue-escape-disputed.tsv')
        self.by_scene = {row['scene_key']: row for row in self.policy if row['scene_key']}

    def test_covers_registry_and_own_story_addresses(self):
        with sqlite3.connect((ROOT / 'db/story.db').as_uri() + '?mode=ro', uri=True) as con:
            db_keys = {key for (key,) in con.execute('SELECT scene_key FROM scene_script')}
        expected = {row['key'] for row in self.registry} | db_keys
        self.assertEqual(set(self.by_scene), expected)
        self.assertEqual(len(self.by_scene), sum(bool(row['scene_key']) for row in self.policy))
        self.assertEqual(len({row['scope_id'] for row in self.policy}), len(self.policy))

    def test_no_implicit_answer_or_unapproved_partial_chain(self):
        partial = []
        for row in self.policy:
            with self.subTest(scope=row['scope_id']):
                self.assertIsNone(row.get(None), 'Unexpected TSV columns')
                self.assertIn(row['on_escape'], ('', 'cancel_all', 'cancel_part'))
                self.assertEqual(row['escape_option'], '')
                if row['on_escape'] == 'cancel_part':
                    partial.append(row['scene_key'])
                    self.assertEqual(row['checkpoint'], 'first_unconfirmed_step')
                if row['application'] in ('not_applicable', 'outside_authored_corpus'):
                    self.assertEqual(row['on_escape'], '')
        self.assertEqual(partial, ['scene.elder.first_meeting'])

    def test_registered_dialogues_and_non_dialogue_boundaries(self):
        for original in self.registry:
            row = self.by_scene[original['key']]
            if original['kind'] == 'dialogue':
                self.assertEqual(row['application'], 'host_dialogue')
                self.assertTrue(row['on_escape'])
            elif row['application'] == 'dialogue_if_present':
                self.assertEqual(original['kind'], 'cutscene_heads')
            elif row['application'] == 'authored_dialogue_only':
                self.assertEqual(original['kind'], 'model_scene')

    def test_goat_scopes_are_not_new_scene_keys(self):
        scopes = [row for row in self.policy if not row['scene_key']]
        self.assertEqual({row['scope_id'] for row in scopes},
                         {'goat_opening', 'goat_witness', 'goat_recipient',
                          'goat_culprit', 'goat_resolution'})
        self.assertTrue(all(row['on_escape'] == 'cancel_all' for row in scopes))

    def test_own_source_paths_exist_and_disputed_defaults_are_only_questions(self):
        for row in self.policy + self.disputed:
            source = row['source_ref'].split('#', 1)[0]
            if source.startswith('rpg/'):
                self.assertTrue((ROOT.parent / source).is_file(), source)
        self.assertEqual(len({row['case_id'] for row in self.disputed}), len(self.disputed))
        self.assertTrue(all(row['status'] == 'needs_boss' for row in self.disputed))

    def test_new_source_anchors(self):
        inherited = {row['authored_ref'] for row in self.registry}
        fresh = {row['source_ref'] for row in self.policy + self.disputed} - inherited
        for source in fresh:
            if not source.startswith('rpg/') or '#' not in source:
                continue
            path, wanted = source.split('#', 1)
            headings = re.findall(r'^#{1,6}\s+(.+)$',
                                  (ROOT.parent / path).read_text(encoding='utf-8'), re.M)
            anchors = {re.sub(r'[^\w\sЀ-ӿ-]', '', heading.strip().lower()).replace(' ', '-')
                       for heading in headings}
            self.assertIn(wanted, anchors, source)


if __name__ == '__main__':
    unittest.main()

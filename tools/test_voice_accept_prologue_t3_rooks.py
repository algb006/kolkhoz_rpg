"""Acceptance and old-file links are tested without changing live files."""
import sqlite3
import unittest
from unittest.mock import MagicMock, patch

import voice_accept_prologue_t3_rooks as accept


class AcceptanceTests(unittest.TestCase):
    def test_scope_and_hearing(self):
        plan = accept.prepare()
        if plan is None:
            accept.verify_installed()
            return
        rows, _, _, items, untouched = plan
        self.assertEqual(len(rows), 7)
        self.assertEqual(len(items), 7)
        self.assertEqual(len(untouched), 114)
        self.assertNotIn('ex_chairman', {r['avatar'] for r in rows})

    def test_unapproved_import_rejected(self):
        with patch.object(accept.batch, 'pending', return_value=['waiting']):
            with self.assertRaisesRegex(ValueError, 'not approved'):
                accept.prepare()

    def test_no_human_hearing_no_install(self):
        with patch.object(accept, 'hearing_gate', side_effect=ValueError('No hearing')):
            with self.assertRaisesRegex(ValueError, 'No hearing'):
                accept.prepare()

    def test_hearing_survives_mailbox_archive(self):
        thread = MagicMock()
        thread.exists.return_value = False
        thread.stem = accept.THREAD.stem
        archived = MagicMock()
        archived.name = thread.stem + '.20261003-120000.md'
        archived.read_text.return_value = (
            '<!-- MSG seq=7 from=boss to=rpg ts=x status=open -->'
            'Голоса одобряю<!-- /MSG seq=7 -->')
        thread.parent.__truediv__.return_value.glob.return_value = [archived]
        with patch.object(accept, 'THREAD', thread):
            accept.hearing_gate()
        archived.read_text.assert_called_once_with(encoding='utf-8')

    def test_old_master_and_measurement_references_follow_archive(self):
        con = sqlite3.connect(':memory:')
        con.execute('PRAGMA foreign_keys=ON')
        con.executescript('''
            CREATE TABLE voice_take(key TEXT PRIMARY KEY,receipt_path TEXT,status TEXT);
            CREATE TABLE voice_file(path TEXT PRIMARY KEY,take_key TEXT REFERENCES voice_take(key),
                sha256 TEXT,source_path TEXT REFERENCES voice_file(path));
            CREATE TABLE voice_measurement(file_path TEXT REFERENCES voice_file(path));
        ''')
        key = 'scene.start.prologue.worker.t3'
        old = 'a' * 64
        take = f'{key}.rev2.{old[:16]}'
        old_path = f'voice/accepted/prologue/{key}.wav'
        con.execute('INSERT INTO voice_take VALUES(?,?,?)',
                    (take, old_path.replace('.wav', '.json'), 'accepted'))
        con.execute('INSERT INTO voice_file VALUES(?,?,?,NULL)', (old_path, take, old))
        con.execute('INSERT INTO voice_file VALUES(?,?,?,?)',
                    ('old-master.wav', take, 'b' * 64, old_path))
        con.execute('INSERT INTO voice_measurement VALUES(?)', (old_path,))
        con.commit()
        con.execute('BEGIN')
        accept.relocate_history(con, [dict(key=key, old={'wav_sha256': old})])
        archived = accept.stored_path(accept.ARCHIVE / (key + '.wav'))
        self.assertEqual(con.execute('SELECT source_path FROM voice_file '
                                     'WHERE path=?', ('old-master.wav',)).fetchone()[0], archived)
        self.assertEqual(con.execute('SELECT file_path FROM voice_measurement').fetchone()[0],
                         archived)
        self.assertFalse(con.execute('PRAGMA foreign_key_check').fetchall())
        self.assertEqual(con.execute('SELECT status FROM voice_take WHERE key=?',
                                     (take,)).fetchone()[0], 'superseded')
        con.rollback()
        con.close()


if __name__ == '__main__':
    unittest.main()

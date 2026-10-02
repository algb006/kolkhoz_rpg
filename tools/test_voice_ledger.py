#!/usr/bin/env python3
"""Регрессии описи на копии базы в памяти; исходные WAV и записи не меняются."""
import json
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest

from voice_ledger import ROOT, audit, import_measurements, mark_thoughts, sha


class LedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = Path(tempfile.mkdtemp(prefix='rpg-voice-ledger-test-',dir='/home/alex/claudetmp'))

    @classmethod
    def tearDownClass(cls):
        subprocess.run(['bash','/home/alex/kolkhoz/claude/tools/tmp-clean.sh',str(cls.temp)],check=True)

    def setUp(self):
        self.con = sqlite3.connect(':memory:')
        source = sqlite3.connect(f'file:{ROOT}/db/story.db?mode=ro',uri=True)
        source.backup(self.con)
        source.close()
        self.con.execute('PRAGMA foreign_keys=ON')
        # Каждый тест стартует с принятых исходников, а не с внешних мастеров.
        self.con.execute('DELETE FROM voice_measurement')
        self.con.execute("DELETE FROM voice_file WHERE file_role='technical_master'")
        self.con.commit()
        self.initial_takes = self.con.execute('SELECT count(*) FROM voice_take').fetchone()[0]
        self.initial_files = self.con.execute('SELECT count(*) FROM voice_file').fetchone()[0]

    def tearDown(self):
        self.con.close()

    def test_initial_coverage(self):
        errors, report = audit(self.con)
        self.assertEqual(errors,[])
        thoughts = self.con.execute(
            "SELECT key,rev FROM line WHERE kind='spoken_thought' AND deprecated=0"
        ).fetchall()
        current = stale = 0
        for key, rev in thoughts:
            revisions = {row[0] for row in self.con.execute(
                "SELECT text_rev FROM voice_take WHERE line_key=? AND status='accepted'", (key,)
            )}
            current += rev in revisions
            stale += bool(revisions) and rev not in revisions
        self.assertIn(
            f'Мыслей всего: {len(thoughts)}; озвучено по текущему тексту: {current}; '
            f'по старому: {stale}; ждут: {len(thoughts)-current}', report
        )
        self.assertEqual(self.con.execute('SELECT count(*) FROM voice_take').fetchone()[0],self.initial_takes)
        self.assertEqual(self.con.execute('SELECT count(*) FROM voice_measurement').fetchone()[0],0)

    def test_edit_makes_take_stale_without_changing_take(self):
        key = 'scene.start.prologue.worker.t1'
        before = self.con.execute('SELECT * FROM voice_take WHERE line_key=?',(key,)).fetchall()
        self.con.execute('UPDATE line SET text=text || ? WHERE key=?',(' Проверка.',key))
        errors,report = audit(self.con)
        self.assertEqual(errors,[])
        self.assertIn('  Старая редакция: '+key,report)
        self.assertEqual(self.con.execute('SELECT * FROM voice_take WHERE line_key=?',(key,)).fetchall(),before)
        self.assertEqual(self.con.execute('SELECT text_state FROM voice_take_state WHERE line_key=?',(key,)).fetchone()[0],'stale')

    def test_classification_preserves_revisions(self):
        before = self.con.execute('SELECT key,rev,approved_rev,text FROM line ORDER BY key').fetchall()
        mark_thoughts(self.con)
        self.assertEqual(self.con.execute('SELECT key,rev,approved_rev,text FROM line ORDER BY key').fetchall(),before)
        key = 'scene.office_intro.enter.worker'
        self.con.execute('UPDATE line SET text=text || ? WHERE key=?',(' Проверка.',key))
        self.assertEqual(self.con.execute('SELECT rev FROM line WHERE key=?',(key,)).fetchone()[0],2)

    def test_classification_preserves_authored_signals(self):
        rows = self.con.execute('SELECT * FROM line ORDER BY key').fetchall()
        mark_thoughts(self.con)
        self.assertEqual(self.con.execute('SELECT * FROM line ORDER BY key').fetchall(), rows)
        self.assertEqual(self.con.execute(
            "SELECT count(*) FROM line WHERE key LIKE 'scene.office_intro.exit_choice.%' AND thought_trigger_kind='signal'"
        ).fetchone()[0], 8)

    def fixture(self, **changes):
        key = 'scene.start.prologue.worker.t1'
        source,take,checksum = self.con.execute(
            'SELECT path,take_key,sha256 FROM voice_file WHERE take_key IN (SELECT key FROM voice_take WHERE line_key=?)',(key,)
        ).fetchone()
        path = self.temp/(self._testMethodName+'.wav')
        path.write_bytes(b'test-master-file')
        record = dict(key=key,rev=2,avatar='worker',file_role='technical_master',path=str(path),
                      sha256=sha(path),source_sha256=checksum,duration_seconds=1.25,lufs=-19.0,
                      peak_dbtp=-1.0,measured_at_utc='2026-09-27T12:00:00Z',measurement_status='ok',error=None)
        record.update(changes)
        package = self.temp/(self._testMethodName+'.json')
        package.write_text(json.dumps(dict(format='sound.voice-measurements.v1',files=[record],
                                          ffmpeg_version='test',ffprobe_version='test',parameters='ebur128=peak=true')))
        return package,record

    def test_master_is_file_not_new_take(self):
        package,record = self.fixture()
        self.assertEqual(import_measurements(self.con,package),1)
        self.assertEqual(import_measurements(self.con,package),1)
        self.assertEqual(self.con.execute('SELECT count(*) FROM voice_take').fetchone()[0],self.initial_takes)
        self.assertEqual(self.con.execute('SELECT count(*) FROM voice_file').fetchone()[0],self.initial_files+1)

        latest = self.con.execute('SELECT measured_at_utc FROM latest_voice_measurement').fetchone()
        self.assertEqual(latest[0],'2026-09-27T12:00:00Z')
        self.assertEqual(self.con.execute('SELECT count(*) FROM voice_measurement').fetchone()[0],1)
        duration = self.con.execute('SELECT duration_seconds FROM voice_measurement WHERE file_path=?',(record['path'],)).fetchone()[0]
        self.assertEqual(duration,1.25)

    def test_checksum_mismatch_rejected(self):
        package,_ = self.fixture(sha256='0'*64)
        with self.assertRaises(ValueError):
            import_measurements(self.con,package)
        self.assertEqual(self.con.execute('SELECT count(*) FROM voice_measurement').fetchone()[0],0)

    def test_unknown_source_rejected(self):
        package,_ = self.fixture(source_sha256='0'*64)
        with self.assertRaises(ValueError):
            import_measurements(self.con,package)

    def test_nonfinite_number_rejected(self):
        package,_ = self.fixture(lufs=float('nan'))
        with self.assertRaises(ValueError):
            import_measurements(self.con,package)
        self.assertEqual(self.con.execute('SELECT count(*) FROM voice_file').fetchone()[0],self.initial_files)

    def test_wrong_revision_rolls_back_master(self):
        package,_ = self.fixture(rev=1)
        with self.assertRaises(ValueError):
            import_measurements(self.con,package)
        self.assertEqual(self.con.execute('SELECT count(*) FROM voice_file').fetchone()[0],self.initial_files)

    def test_take_without_file_is_reported(self):
        self.con.execute("DELETE FROM voice_file WHERE path LIKE '%worker.t1.wav'")
        errors,_ = audit(self.con)
        self.assertTrue(any(s.startswith('Дубль без файловой записи:') for s in errors))

    def test_missing_and_orphan_files(self):
        self.con.execute("UPDATE voice_file SET path='absent-test.wav' WHERE path LIKE '%worker.t1.wav'")
        errors,report = audit(self.con)
        self.assertTrue(any('Строка без файла: absent-test.wav' in s for s in errors))
        self.assertTrue(any('Файл без строки:' in s and 'worker.t1.wav' in s for s in errors))

    def test_null_measurement_is_not_zero(self):
        package,_ = self.fixture(lufs=None,peak_dbtp=None,duration_seconds=None,
                                 measurement_status='unmeasurable',error='Тест прибора')
        import_measurements(self.con,package)
        self.assertEqual(self.con.execute('SELECT lufs,peak_dbtp,duration_seconds FROM voice_measurement').fetchone(),(None,None,None))

    def test_unknown_measurement_time_preserved(self):
        package,_ = self.fixture(measured_at_utc=None,loudness_provenance='preserved_mastering_report',
                                duration_verified_at_utc='2026-09-27T12:00:00Z')
        import_measurements(self.con,package)
        row = self.con.execute('SELECT measured_at_utc,instrument_json FROM voice_measurement').fetchone()
        self.assertIsNone(row[0])
        self.assertEqual(json.loads(row[1])['loudness_provenance'],'preserved_mastering_report')

    def test_fresh_measurement_keeps_history_without_new_take(self):
        package,_ = self.fixture(measured_at_utc=None,loudness_provenance='preserved_mastering_report')
        import_measurements(self.con,package)
        package,_ = self.fixture()
        import_measurements(self.con,package)
        import_measurements(self.con,package)
        self.assertEqual(self.con.execute('SELECT count(*) FROM voice_measurement').fetchone()[0],2)
        self.assertEqual(self.con.execute('SELECT count(*) FROM voice_measurement WHERE measured_at_utc IS NULL').fetchone()[0],1)
        self.assertEqual(self.con.execute('SELECT count(*) FROM voice_take').fetchone()[0],self.initial_takes)
        self.assertEqual(self.con.execute('SELECT count(*) FROM voice_file').fetchone()[0],self.initial_files+1)

    def test_schema_dump_roundtrip(self):
        rebuilt = sqlite3.connect(':memory:')
        rebuilt.executescript((ROOT/'db/schema.sql').read_text())
        rebuilt.execute('PRAGMA foreign_keys=OFF')
        for path in sorted((ROOT/'db/data').glob('*.sql')):
            rebuilt.executescript(path.read_text())
        self.assertEqual(rebuilt.execute('PRAGMA foreign_key_check').fetchall(),[])
        self.assertEqual(rebuilt.execute('SELECT * FROM line ORDER BY key').fetchall(),
                         self.con.execute('SELECT * FROM line ORDER BY key').fetchall())
        self.assertEqual(rebuilt.execute('SELECT * FROM voice_take ORDER BY key').fetchall(),
                         self.con.execute('SELECT * FROM voice_take ORDER BY key').fetchall())
        rebuilt.close()


if __name__=='__main__':
    unittest.main()

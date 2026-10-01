#!/usr/bin/env python3
"""Freeze heard office sources with provenance; no API, remastering or foreign writes."""
import json
from pathlib import Path
import sqlite3
import wave

from voice_accept_prologue import digest, encoded, keep_exact
from voice_prologue_probe import EXPECTED_GENDER, VOICES

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'voice/draft/office-intro'
DEST = ROOT / 'voice/accepted/office-intro'
SOUND = ROOT.parent / 'sound'
EVIDENCE = SOUND / 'effects/speech_office_intro_part2'
DATE = '2026-10-02'
STATUS = 'accepted_source_for_human_heard_office_masters'


def prepare():
    """Validate the complete delivery before creating any accepted file."""
    hearing_bytes = (EVIDENCE / 'hearing-acceptance.json').read_bytes()
    hearing = json.loads(hearing_bytes)
    runtime_bytes = (EVIDENCE / 'runtime-manifest.json').read_bytes()
    runtime = json.loads(runtime_bytes)
    delivery = json.loads((SOURCE / 'delivery-manifest.json').read_text())
    if hearing['accepted_on'] != DATE or hearing['count'] != 160:
        raise ValueError('Нет квитанции слуховой приёмки всех 160 мыслей')
    masters = {t['key']: t for t in runtime['takes']}
    sources = {t['key']: t for t in delivery['takes']}
    if len(runtime['takes']) != 160 or len(masters) != 160 or set(masters) != set(sources):
        raise ValueError('Неполный или повторённый состав источников/мастеров')
    with sqlite3.connect(f'file:{ROOT / "db/story.db"}?mode=ro', uri=True) as con:
        rows = con.execute(
            "SELECT key,text,rev,approved_rev FROM line "
            "WHERE scene_key='scene.start.office' AND deprecated=0 ORDER BY key"
        ).fetchall()
    if len(rows) != 160 or {r[0] for r in rows} != set(masters):
        raise ValueError('Состав не совпадает с текущими строками кабинета')
    pending, lines = [], []
    for key, text, rev, approved in rows:
        avatar = key.rsplit('.', 1)[1]
        wav_path, receipt_path = SOURCE / f'{key}.wav', SOURCE / f'{key}.json'
        audio, receipt_bytes = wav_path.read_bytes(), receipt_path.read_bytes()
        receipt = json.loads(receipt_bytes)
        master, source = masters[key], sources[key]
        if avatar not in VOICES or rev != approved:
            raise ValueError(f'Неутверждённая строка или неизвестный аватар: {key}')
        expected = {'key': key, 'avatar': avatar, 'voice': VOICES[avatar],
                    'gender': EXPECTED_GENDER[avatar], 'rev': rev,
                    'text_sha256': digest(text.encode()), 'wav_sha256': digest(audio)}
        if any(receipt[k] != v or source[k] != v for k, v in expected.items()):
            raise ValueError(f'Источник/квитанция не совпали: {key}')
        if receipt['text'] != text or receipt['approved_rev'] != approved:
            raise ValueError(f'Текст или его утверждение не совпали: {key}')
        if (master['accepted_on'] != DATE or master['source_sha256'] != expected['wav_sha256']
                or any(master[k] != expected[k] for k in ('avatar', 'voice', 'rev', 'text_sha256'))):
            raise ValueError(f'Принятый мастер относится к другому источнику: {key}')
        master_path = SOUND / 'audio' / master['path']
        if digest(master_path.read_bytes()) != master['sha256']:
            raise ValueError(f'Мастер изменился после приёмки: {key}')
        with wave.open(str(wav_path), 'rb') as wav:
            if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) != (1, 2, 24000):
                raise ValueError(f'Формат исходника не совпал: {key}')
            if abs(wav.getnframes() / wav.getframerate() - receipt['duration_seconds']) > 0.0001:
                raise ValueError(f'Длительность исходника не совпала: {key}')
        accepted = dict(receipt)
        accepted.update(status=STATUS, source_status=receipt['status'],
                        voice_passport={'avatar': avatar, 'voice_id': VOICES[avatar],
                                        'gender': EXPECTED_GENDER[avatar],
                                        'description_ref': 'manual/voice/prologue-pilot.md'},
                        acceptance={'date': DATE, 'by': 'human_project_owner',
                                    'statement': hearing['human_quote'], 'scope': 'office_intro_160',
                                    'basis': 'human_heard_sound_masters_not_unprocessed_source_playback',
                                    'sound_receipt': str(EVIDENCE / 'hearing-acceptance.json'),
                                    'sound_receipt_sha256': digest(hearing_bytes),
                                    'boss_receipt': 'boss-all-office-in-this-build-2026-10-02#16',
                                    'original_receipt_sha256': digest(receipt_bytes),
                                    'master_path': str(master_path), 'master_sha256': master['sha256']})
        # Missing generation timestamps stay missing; file mtime is not an API timestamp.
        pending.extend([(DEST / f'{key}.wav', audio), (DEST / f'{key}.json', encoded(accepted))])
        lines.append(dict(expected, wav=f'{key}.wav', receipt=f'{key}.json',
                          original_receipt_sha256=digest(receipt_bytes),
                          master_path=str(master_path), master_sha256=master['sha256']))
    if any(sum(t['avatar'] == avatar for t in lines) != 20 for avatar in VOICES):
        raise ValueError('Состав должен быть 20 мыслей на аватар')
    manifest = {'scene': 'scene.start.office', 'status': STATUS,
                'acceptance_date': DATE, 'acceptance_statement': hearing['human_quote'],
                'basis': 'sound-rpg-office-human-accepted-2026-10-02#1; boss-all-office-in-this-build-2026-10-02#16',
                'source_directory': str(SOURCE), 'count': 160,
                'audio_format': 'unchanged source mono PCM16 WAV 24000 Hz; game uses sound mono PCM24 48000 Hz masters',
                'sound_hearing_receipt_sha256': digest(hearing_bytes),
                'sound_runtime_manifest_sha256': digest(runtime_bytes),
                'new_generations': 0, 'regenerations': 0,
                'excludes': 'Other scenes, clock/queue remasters and in-engine acoustic balance.',
                'lines': lines}
    pending.append((DEST / 'manifest.json', encoded(manifest)))
    for path, data in pending:
        if path.exists() and path.read_bytes() != data:
            raise ValueError(f'Не перезаписывать существующую принятую поставку: {path}')
    return pending


def main():
    pending = prepare()
    DEST.mkdir(parents=True, exist_ok=True)
    for path, data in pending:
        keep_exact(path, data)
    print('Приняты 160 источников; исходные WAV/квитанции неизменны; API 0.')


if __name__ == '__main__':
    main()

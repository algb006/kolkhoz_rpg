#!/usr/bin/env python3
"""Зафиксировать принятые на слух 16 источников, не меняя старые дубли и звук."""
import argparse
import json
from pathlib import Path
import wave

from voice_accept_prologue import digest, encoded, keep_exact
from voice_office_intro import pending_approvals, source_rows
from voice_prologue_probe import EXPECTED_GENDER, VOICES

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'voice/draft/office-intro/additions-20261002'
DEST = ROOT / 'voice/accepted/office-intro-additions-20261002'
SOUND = ROOT.parent / 'sound'
EVIDENCE = SOUND / 'effects/speech_office_additions_v1'
DATE = '2026-10-02'
STATUS = 'accepted_source_for_human_heard_office_additions_masters'
BASIS = 'boss-all-office-recommendations-map-2026-10-02#35,#36; sound commit 2ac6e9a'


def read_document(path):
    raw = path.read_bytes()
    return json.loads(raw), raw


def prepare():
    """Проверить всю партию и существующие назначения до первой записи."""
    hearing, hearing_bytes = read_document(EVIDENCE / 'hearing-acceptance.json')
    runtime, runtime_bytes = read_document(EVIDENCE / 'runtime-manifest.json')
    delivery, delivery_bytes = read_document(SOURCE / 'delivery-manifest.json')
    if (hearing.get('accepted_on') != DATE or hearing.get('accepted_count') != 16
            or hearing.get('excluded_keys') != [] or not hearing.get('quote')):
        raise ValueError('Нет полной квитанции слуховой приёмки 16 мыслей')
    rows = list(source_rows('plan_sketch')) + list(source_rows('portrait'))
    if pending_approvals(rows):
        raise ValueError('Редакции мыслей не утверждены в обеих базах')
    sources = {t['key']: t for t in delivery['files']}
    masters = {t['key']: t for t in runtime['takes']}
    keys = {r['key'] for r in rows}
    if (len(rows) != 16 or len(sources) != 16 or len(delivery['files']) != 16
            or set(sources) != keys or len(masters) != 168
            or len(runtime['takes']) != 168 or not keys <= set(masters)):
        raise ValueError('Неполный или повторённый состав партии')
    pending, lines = [], []
    for row in rows:
        key, avatar, text, rev = (row[k] for k in ('key', 'avatar', 'text', 'rev'))
        if rev != (1 if '.plan_sketch.' in key else 2):
            raise ValueError(f'Неожиданная редакция партии: {key}')
        wav_path = SOURCE / f'rev-{rev}' / f'{key}.wav'
        receipt_path = wav_path.with_suffix('.json')
        audio = wav_path.read_bytes()
        receipt, receipt_bytes = read_document(receipt_path)
        source, master = sources[key], masters[key]
        expected = dict(key=key, avatar=avatar, rev=rev, voice=VOICES[avatar],
                        gender=EXPECTED_GENDER[avatar], text_sha256=digest(text.encode()))
        if any(receipt.get(k) != v or source.get(k) != v for k, v in expected.items()):
            raise ValueError(f'Источник, пол, голос или редакция не совпали: {key}')
        if (receipt['text'] != text or receipt['approved_rev'] != rev
                or receipt['wav_sha256'] != digest(audio)
                or source['wav_sha256'] != digest(audio)
                or source['receipt_sha256'] != digest(receipt_bytes)
                or Path(source['wav']).resolve() != wav_path.resolve()
                or Path(source['receipt']).resolve() != receipt_path.resolve()):
            raise ValueError(f'Текст, путь или хэш квитанции/звука не совпал: {key}')
        if (master['accepted_on'] != DATE or master['source_sha256'] != digest(audio)
                or any(master[k] != expected[k] for k in ('avatar', 'voice', 'rev', 'text_sha256'))):
            raise ValueError(f'Принятый мастер относится к другому источнику: {key}')
        master_path = SOUND / 'audio' / master['path']
        if digest(master_path.read_bytes()) != master['sha256']:
            raise ValueError(f'Мастер изменился после приёмки: {key}')
        with wave.open(str(wav_path)) as wav:
            if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) != (1, 2, 24000):
                raise ValueError(f'Неверный формат исходника: {key}')
            seconds = wav.getnframes() / wav.getframerate()
        if abs(seconds - receipt['duration_seconds']) > 0.0001 or seconds > 11:
            raise ValueError(f'Длительность исходника не совпала: {key}')
        accepted = dict(receipt)
        accepted.update(status=STATUS, source_status=receipt['status'],
                        voice_passport={'avatar': avatar, 'voice_id': VOICES[avatar],
                                        'gender': EXPECTED_GENDER[avatar],
                                        'description_ref': 'manual/voice/prologue-pilot.md'},
                        acceptance={'date': DATE, 'by': 'human_project_owner',
                                    'statement': hearing['quote'], 'scope': 'office_additions_16',
                                    'basis': 'human_heard_sound_masters_not_unprocessed_source_playback',
                                    'sound_receipt': str(EVIDENCE / 'hearing-acceptance.json'),
                                    'sound_receipt_sha256': digest(hearing_bytes),
                                    'boss_receipt': BASIS,
                                    'original_receipt_sha256': digest(receipt_bytes),
                                    'master_path': str(master_path), 'master_sha256': master['sha256']})
        # Неизвестное время генерации остаётся неизвестным; время копии его не заменяет.
        pending.extend([(DEST / f'{key}.wav', audio),
                        (DEST / f'{key}.json', encoded(accepted))])
        lines.append(dict(expected, wav=f'{key}.wav', receipt=f'{key}.json',
                          wav_sha256=digest(audio), original_receipt_sha256=digest(receipt_bytes),
                          master_path=str(master_path), master_sha256=master['sha256']))
    if any(sum(t['avatar'] == avatar for t in lines) != 2 for avatar in VOICES):
        raise ValueError('Ожидались две мысли каждого аватара')
    manifest = dict(scene='scene.start.office', status=STATUS, count=16,
                    acceptance_date=DATE, acceptance_statement=hearing['quote'], basis=BASIS,
                    source_directory=str(SOURCE),
                    audio_format='unchanged source mono PCM16/24000; game uses sound PCM24/48000 masters',
                    sound_hearing_receipt_sha256=digest(hearing_bytes),
                    sound_runtime_manifest_sha256=digest(runtime_bytes),
                    delivery_manifest_sha256=digest(delivery_bytes), new_generations=0,
                    regenerations=0, historical_portraits='voice/accepted/office-intro/; rev1 unchanged',
                    excludes='In-engine mix, runtime import and external backup integrity.', lines=lines)
    pending.append((DEST / 'manifest.json', encoded(manifest)))
    for path, data in pending:
        if path.exists() and path.read_bytes() != data:
            raise ValueError(f'Не перезаписывать принятую поставку: {path}')
    return pending


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    pending = prepare()
    if not args.check_only:
        DEST.mkdir(parents=True, exist_ok=True)
        for path, data in pending:
            keep_exact(path, data)
    print(f'Проверены 16 источников и приёмка; файлов {len(pending)}; API 0; запись: {not args.check_only}.')


if __name__ == '__main__':
    main()

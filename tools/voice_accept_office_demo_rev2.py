#!/usr/bin/env python3
"""Freeze 24 human-heard rev2 originals without replacing historical files."""
import argparse
import json
import re
import wave
from pathlib import Path

from voice_accept_prologue import digest, encoded, keep_exact
from voice_office_demo_rev2 import rows
from voice_prologue_probe import VOICES, EXPECTED_GENDER

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'voice/draft/office-intro/demo-r2-20261012'
DEST = ROOT / 'voice/accepted/office-intro-demo-rev2-20261012'
EVIDENCE = ROOT.parent / 'sound/effects/speech_office_demo_rev2_20261012'
SLUG = 'boss-rpg-office-rev2-accepted-2026-10-12'
DATE = '2026-10-12'
STATUS = 'accepted_source_for_human_heard_office_demo_rev2'


def acceptance_block():
    mailbox = ROOT.parent / 'claude/mailbox'
    active = mailbox / (SLUG + '.md')
    paths = [active] if active.exists() else list((mailbox / 'trash').glob(SLUG + '.*.md'))
    blocks = set()
    for path in paths:
        match = re.search(rb'<!-- MSG seq=1 from=boss to=rpg .*?<!-- /MSG seq=1 -->',
                          path.read_bytes(), re.S)
        if match:
            blocks.add(match[0])
    if len(blocks) != 1 or '«озвучка норм»'.encode() not in next(iter(blocks), b''):
        raise ValueError('Missing unique boss-relayed human acceptance of 24 takes')
    return blocks.pop()


def prepare():
    block = acceptance_block()
    manifest_bytes = (SOURCE / 'manifest.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    candidate_bytes = (EVIDENCE / 'candidate-manifest.json').read_bytes()
    candidate = json.loads(candidate_bytes)
    current = rows()
    keys = {r['key'] for r in current}
    source_index = {r['key']: r for r in manifest['takes']}
    masters = {r['key']: r for r in candidate['takes']}
    if (manifest['count'] != 24 or candidate['count'] != 24
            or len(manifest['takes']) != 24 or len(candidate['takes']) != 24
            or set(source_index) != keys or set(masters) != keys):
        raise ValueError('Missing or duplicate source/master keys')
    pending, lines = [], []
    for row in current:
        key, avatar = row['key'], row['avatar']
        audio = (SOURCE / (key + '.wav')).read_bytes()
        receipt_bytes = (SOURCE / (key + '.json')).read_bytes()
        receipt = json.loads(receipt_bytes)
        expected = dict(key=key, rev=2, avatar=avatar, voice=VOICES[avatar],
                        gender=EXPECTED_GENDER[avatar], text_sha256=digest(row['text'].encode()),
                        wav_sha256=digest(audio))
        if (any(receipt.get(k) != v for k, v in expected.items())
                or receipt != source_index[key] or receipt['approved_rev'] != 2
                or receipt['text'] != row['text']):
            raise ValueError('Source text/voice/hash mismatch: ' + key)
        master = masters[key]
        master_path = ROOT.parent / 'sound/audio' / master['path']
        if (master['rev'] != 2 or master['source_sha256'] != expected['wav_sha256']
                or master['text_sha256'] != expected['text_sha256']
                or digest(master_path.read_bytes()) != master['master_sha256']):
            raise ValueError('Human-hearing master provenance mismatch: ' + key)
        with wave.open(str(SOURCE / (key + '.wav'))) as wav:
            if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) != (1, 2, 24000):
                raise ValueError('Unexpected source format: ' + key)
            seconds = wav.getnframes() / wav.getframerate()
        if any(abs(seconds - n) > 0.0001 for n in
               (receipt['duration_seconds'], master['seconds'])):
            raise ValueError('Source/master duration mismatch: ' + key)
        accepted = dict(receipt)
        accepted.update(status=STATUS, source_status=receipt['status'],
                        source_generation_time_utc=receipt.get('generated_utc'),
                        voice_passport=dict(avatar=avatar, voice_id=VOICES[avatar],
                                            gender=EXPECTED_GENDER[avatar],
                                            description_ref='manual/voice/prologue-pilot.md'),
                        acceptance=dict(date=DATE, by='human_project_owner', statement='озвучка норм',
                                        scope='office_demo_rev2_24',
                                        basis='human_heard_sound_masters_not_unprocessed_source_playback',
                                        boss_receipt=SLUG + '#1', boss_block_sha256=digest(block),
                                        original_receipt_sha256=digest(receipt_bytes),
                                        master_path=str(master_path), master_sha256=master['master_sha256']))
        pending.extend([(DEST / (key + '.wav'), audio),
                        (DEST / (key + '.json'), encoded(accepted))])
        lines.append(dict(expected, wav=key + '.wav', receipt=key + '.json',
                          master_path=str(master_path), master_sha256=master['master_sha256']))
    accepted_manifest = dict(status=STATUS, count=24, revision=2,
                             acceptance_date=DATE, acceptance_statement='озвучка норм',
                             boss_receipt=SLUG + '#1', boss_block_sha256=digest(block),
                             source_directory=str(SOURCE),
                             source_manifest_sha256=digest(manifest_bytes),
                             hearing_candidate_manifest_sha256=digest(candidate_bytes),
                             new_generations=0, regenerations=0,
                             historical_revisions='voice/accepted/office-intro rev1 remains immutable',
                             replaces_keys=sorted(keys),
                             excludes='Sound accepted_on, UE handoff and external backup verification',
                             lines=lines)
    pending.append((DEST / 'manifest.json', encoded(accepted_manifest)))
    for path, data in pending:
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Never overwrite differing accepted content: ' + str(path))
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
    print(f'Validated 24 accepted rev2 sources / 49 files; API 0; write: {not args.check_only}.')


if __name__ == '__main__':
    main()

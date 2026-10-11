#!/usr/bin/env python3
"""Freeze the heard portrait rev3 source without overwriting prior revisions."""
import argparse
import json
import re
import wave

from voice_accept_prologue import digest, encoded, keep_exact
from voice_accept_office_additions import read_document
from voice_office_intro import pending_approvals, source_rows
from voice_prologue_probe import EXPECTED_GENDER, VOICES
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEY = 'scene.office_intro.portrait.promoted'
DATE = '2026-10-11'
SOURCE = ROOT / 'voice/draft/office-intro/portrait-promoted-r3-20261002'
DEST = ROOT / 'voice/accepted/office-intro-portrait-promoted-rev3-20261011'
SOUND = ROOT.parent / 'sound'
EVIDENCE = SOUND / 'effects/speech_office_portrait_promoted_rev3'
BOSS = ROOT.parent / 'claude/mailbox/boss-rpg-portrait-rev3-accepted-2026-10-11.md'
STATUS = 'accepted_source_for_human_heard_office_portrait_rev3'


def prepare():
    """Validate canonical text, hearing provenance and all outputs before writing."""
    row = next(r for r in source_rows('portrait') if r['key'] == KEY)
    if pending_approvals([row]) or row['rev'] != 3 or row['text'] != row['string_text']:
        raise ValueError('Portrait rev3 text is unapproved or inconsistent')
    receipt, receipt_bytes = read_document(SOURCE / f'{KEY}.json')
    hearing, hearing_bytes = read_document(EVIDENCE / 'hearing-acceptance.json')
    runtime, _ = read_document(EVIDENCE / 'runtime-manifest.json')
    block = re.search(rb'<!-- MSG seq=1 from=boss to=rpg .*?<!-- /MSG seq=1 -->',
                      BOSS.read_bytes(), re.S)
    if not block or '«принимаю»'.encode() not in block[0]:
        raise ValueError('Missing exact boss-relayed human acceptance')
    if (hearing.get('date') != DATE or hearing.get('human_quote') != 'принимаю'
            or hearing.get('key') != KEY or hearing.get('rev') != 3):
        raise ValueError('Hearing receipt is for another date, key or revision')
    matches = [t for t in runtime['takes'] if t['key'] == KEY]
    if len(matches) != 1:
        raise ValueError('Missing or duplicate master key')
    master = matches[0]
    audio = (SOURCE / f'{KEY}.wav').read_bytes()
    expected = dict(key=KEY, rev=3, avatar='promoted', voice=VOICES['promoted'],
                    gender=EXPECTED_GENDER['promoted'], text_sha256=digest(row['text'].encode()),
                    wav_sha256=digest(audio))
    if any(receipt.get(k) != v for k, v in expected.items()):
        raise ValueError('Source receipt does not match text, voice or audio')
    if receipt['text'] != row['text'] or receipt['approved_rev'] != 3:
        raise ValueError('Source subtitle or approval does not match')
    if (master.get('accepted_on') != DATE or master.get('source_sha256') != expected['wav_sha256']
            or any(master.get(k) != expected[k] for k in ('rev', 'avatar', 'voice', 'text_sha256'))):
        raise ValueError('Accepted master is for another source or revision')
    master_path = SOUND / 'audio' / master['path']
    if (digest(master_path.read_bytes()) != master['sha256']
            or hearing['master_sha256'] != master['sha256']
            or hearing['source_sha256'] != expected['wav_sha256']
            or hearing['text_sha256'] != expected['text_sha256']):
        raise ValueError('Hearing or master checksum mismatch')
    with wave.open(str(SOURCE / f'{KEY}.wav')) as wav:
        if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) != (1, 2, 24000):
            raise ValueError('Unsupported original WAV format')
        seconds = wav.getnframes() / wav.getframerate()
    if any(abs(seconds - n) > 0.0001 for n in
           (receipt['duration_seconds'], master['seconds'], hearing['duration_s'], 7.24)):
        raise ValueError('Duration mismatch; do not trim or accelerate')
    accepted = dict(receipt)
    accepted.update(status=STATUS, source_status=receipt['status'],
                    voice_passport=dict(avatar='promoted', voice_id=VOICES['promoted'],
                                        gender=EXPECTED_GENDER['promoted'],
                                        description_ref='skills/chairman-apparatchik-voice/SKILL.md'),
                    acceptance=dict(date=DATE, by='human_project_owner', statement='принимаю',
                                    scope='office_portrait_promoted_rev3',
                                    basis='human_heard_sound_master_not_unprocessed_source_playback',
                                    boss_receipt='boss-rpg-portrait-rev3-accepted-2026-10-11#1',
                                    boss_block_sha256=digest(block[0]),
                                    sound_receipt=str(EVIDENCE / 'hearing-acceptance.json'),
                                    sound_receipt_sha256=digest(hearing_bytes),
                                    original_receipt_sha256=digest(receipt_bytes),
                                    master_path=str(master_path), master_sha256=master['sha256']))
    manifest = dict(scene='scene.start.office', count=1, status=STATUS,
                    acceptance_date=DATE, acceptance_statement='принимаю',
                    source_directory=str(SOURCE), new_generations=0, regenerations=0,
                    audio_format='unchanged source mono PCM16/24000; sound master PCM24/48000',
                    excludes='UE package verification and external backup integrity.',
                    historical_revisions='office-intro rev1; office-intro-additions-20261002 rev2 unchanged',
                    lines=[dict(expected, wav=f'{KEY}.wav', receipt=f'{KEY}.json',
                                master_path=str(master_path), master_sha256=master['sha256'])])
    pending = [(DEST / f'{KEY}.wav', audio), (DEST / f'{KEY}.json', encoded(accepted)),
               (DEST / 'manifest.json', encoded(manifest))]
    for path, data in pending:
        if path.exists() and path.read_bytes() != data:
            raise ValueError(f'Never overwrite a differing accepted file: {path}')
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
    print(f'Validated 1 heard rev3 original, {len(pending)} files; API 0; write: {not args.check_only}.')


if __name__ == '__main__':
    main()

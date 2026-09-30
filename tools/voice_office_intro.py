#!/usr/bin/env python3
"""Resumable, budget-capped first TTS pass for 160 approved office thoughts."""

import hashlib
import json
from pathlib import Path
import sqlite3
import sys

from voice_prologue_probe import EXPECTED_GENDER, VOICES, verified_voice_gender
from voice_prologue_v2 import request_line


ROOT = Path(__file__).resolve().parent.parent
STORY_DB = ROOT / 'db/story.db'
STRINGS_DB = ROOT.parent / 'db/strings.db'
DESIGN_DB = ROOT.parent / 'db/design.db'
DEST = Path('/data/tmp/rpg-office-voice-draft-20260930')
EXPECTED_PER_AVATAR = 20
PASS_CAP_USD = 0.35
MIN_REMAINING_USD = 0.006


def source_rows():
    design = sqlite3.connect(f'file:{DESIGN_DB}?mode=ro', uri=True)
    policy = design.execute(
        "SELECT voice_policy FROM scene WHERE key='scene.start.office'"
    ).fetchone()
    design.close()
    if policy != ('engine_allowed',):
        raise RuntimeError(f'office scene not voice-enabled: {policy}')

    story = sqlite3.connect(f'file:{STORY_DB}?mode=ro', uri=True)
    story.row_factory = sqlite3.Row
    story.execute(
        'ATTACH DATABASE ? AS strings',
        (f'file:{STRINGS_DB}?mode=ro',),
    )
    rows = story.execute(
        "SELECT l.key, l.text, l.rev, l.approved_rev, l.thought_avatar avatar,"
        "       s.rev string_rev, s.approved_rev string_approved_rev,"
        "       tr.text string_text"
        "  FROM line l"
        "  LEFT JOIN strings.namespace ns ON ns.key=l.namespace"
        "  LEFT JOIN strings.string s ON s.namespace_id=ns.id"
        "    AND s.key=substr(l.key,length(l.namespace)+2)"
        "  LEFT JOIN strings.locale loc ON loc.key='ru'"
        "  LEFT JOIN strings.translation tr ON tr.string_id=s.id"
        "    AND tr.locale_id=loc.id"
        " WHERE l.scene_key='scene.start.office'"
        "   AND l.kind='spoken_thought' AND l.deprecated=0"
        " ORDER BY l.sort,l.key"
    ).fetchall()
    story.close()
    if len(rows) != len(VOICES) * EXPECTED_PER_AVATAR:
        raise RuntimeError(f'expected 160 office thoughts, found {len(rows)}')
    for avatar in VOICES:
        group = [row for row in rows if row['avatar'] == avatar]
        if len(group) != EXPECTED_PER_AVATAR:
            raise RuntimeError(f'{avatar}: expected 20 thoughts, found {len(group)}')
    for row in rows:
        key = row['key']
        if row['text'] != row['string_text'] or row['rev'] != row['string_rev']:
            raise RuntimeError(f'story/strings mismatch: {key}')
        if key.startswith('scene.office_intro.exit_choice.') and any(
            name in row['text'] for name in ('Федот', 'Кузьмич', 'Рябинин')
        ):
            raise RuntimeError(f'fixed name in pre-recorded line: {key}')
    return rows


def pending_approvals(rows):
    return [row['key'] for row in rows
            if row['approved_rev'] != row['rev']
            or row['string_approved_rev'] != row['string_rev']]


def spent():
    return sum(
        json.loads(path.read_text(encoding='utf-8'))['estimated_usd_from_usage']
        for path in DEST.glob('scene.office_intro.*.json')
    )


def verify_existing(row):
    key = row['key']
    wav_path = DEST / f'{key}.wav'
    receipt_path = DEST / f'{key}.json'
    if not wav_path.exists() and not receipt_path.exists():
        return False
    if not wav_path.exists() or not receipt_path.exists():
        raise RuntimeError(f'partial output: {key}')
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    wav_hash = hashlib.sha256(wav_path.read_bytes()).hexdigest()
    text_hash = hashlib.sha256(row['text'].encode('utf-8')).hexdigest()
    if (receipt.get('key') != key or receipt.get('rev') != row['rev']
            or receipt.get('text_sha256') != text_hash
            or receipt.get('wav_sha256') != wav_hash
            or receipt.get('voice') != VOICES[row['avatar']]):
        raise RuntimeError(f'existing output does not match current source: {key}')
    return True


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ('dry-run', 'probe', 'generate'):
        raise SystemExit('usage: voice_office_intro.py <dry-run|probe|generate>')
    mode = sys.argv[1]
    rows = source_rows()
    pending = pending_approvals(rows)
    print(f'office thoughts: {len(rows)}; awaiting approval: {len(pending)}')
    if mode == 'dry-run':
        for key in pending[:8]:
            print(f'  draft: {key}')
        return
    if pending:
        raise RuntimeError('No paid TTS while office lines remain unapproved')
    DEST.mkdir(parents=True, exist_ok=True)
    for row in rows:
        key, avatar, words, rev = row['key'], row['avatar'], row['text'], row['rev']
        if verify_existing(row):
            print(f'skip existing {key}', flush=True)
            continue
        if spent() + MIN_REMAINING_USD > PASS_CAP_USD:
            raise RuntimeError('office voice budget cap reached before next request')
        verified_voice_gender(VOICES[avatar], EXPECTED_GENDER[avatar])
        audio, receipt = request_line(key, words, rev, avatar)
        receipt['status'] = 'office_draft_for_human_review_not_accepted'
        with (DEST / f'{key}.wav').open('xb') as file:
            file.write(audio)
        with (DEST / f'{key}.json').open('x', encoding='utf-8') as file:
            json.dump(receipt, file, ensure_ascii=False, indent=2)
            file.write('\n')
        print(f"{key}: {receipt['duration_seconds']:.2f}s; "
              f"USD={receipt['estimated_usd_from_usage']:.6f}", flush=True)
        if mode == 'probe':
            break


if __name__ == '__main__':
    main()

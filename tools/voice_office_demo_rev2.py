#!/usr/bin/env python3
"""Single-pass approved office replacements; preserve all earlier recordings."""

from datetime import datetime, timezone
import html
import json
from pathlib import Path
import sys

from voice_office_intro import source_rows, pending_approvals, verify_existing
from voice_prologue_probe import VOICES, EXPECTED_GENDER, verified_voice_gender
from voice_prologue_v2 import MODEL, request_line
from voice_rate_limit import attempts_last_24h, MAX_ATTEMPTS_24H

ROOT = Path(__file__).resolve().parent.parent
STAGE = Path('/data/tmp/rpg-office-demo-rev2-20261012')
DEST = ROOT / 'voice/draft/office-intro/demo-r2-20261012'
PUBLIC = Path('/data/kolkhoz/voice/office-demo-rev2-20261012')
CAP_USD = 0.10
RESERVE_USD = 0.006
ITEMS = {'enter', 'notebooks', 'journal'}


def rows():
    selected = [dict(row) for row in source_rows()
                if row['key'].split('.')[2] in ITEMS]
    expected = {f'scene.office_intro.{item}.{avatar}' for item in ITEMS for avatar in VOICES}
    if len(selected) != 24 or {row['key'] for row in selected} != expected:
        raise RuntimeError('Expected exactly 24 existing thought replacements')
    if pending_approvals(selected) or any(row['rev'] != 2 for row in selected):
        raise RuntimeError('Matching approved rev2 required in both DBs')
    return selected


def exact_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise RuntimeError('Refusing different existing artifact: ' + str(path))
        return
    with path.open('xb') as handle:
        handle.write(data)


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def publish():
    takes = []
    for row in rows():
        if not verify_existing(row, DEST):
            continue
        key = row['key']
        receipt = json.loads((DEST / (key + '.json')).read_text())
        for suffix in ('.wav', '.json'):
            exact_write(PUBLIC / (key + suffix), (DEST / (key + suffix)).read_bytes())
        takes.append(receipt)
    manifest = {'status': 'draft_for_human_hearing_not_accepted', 'count': len(takes),
                'revision': 2, 'model': MODEL, 'cost_cap_usd': CAP_USD,
                'estimated_usd_from_usage': sum(t['estimated_usd_from_usage'] for t in takes),
                'approval': 'boss-rpg-orders-demo-texts-2026-10-11 moves 19 and 21',
                'pricing_source': 'https://ai.google.dev/gemini-api/docs/pricing',
                'new_generations': len(takes), 'regenerations': 0, 'takes': takes}
    # A growing manifest is an index; the source WAV/receipt are immutable.
    for base in (DEST, PUBLIC):
        (base / 'manifest.json').write_bytes(encode(manifest))
    parts = ['<!doctype html><html lang="ru"><meta charset="utf-8">',
             '<title>Кабинет — три новые мысли</title>',
             '<h1>Кабинет — новые мысли rev2</h1><p>Черновые исходники: на прослушивание, не приняты.</p>']
    for take in takes:
        parts.append('<section><h2>' + html.escape(take['avatar'] + ' / ' + take['key'].split('.')[2])
                     + '</h2><p>' + html.escape(take['text']) + '</p><audio controls src="'
                     + take['key'] + '.wav"></audio><p>Принять / переснять / исправить текст</p></section>')
    parts.append('</html>')
    (PUBLIC / 'index.html').write_text('\n'.join(parts), encoding='utf-8')
    print(f"Review package: {len(takes)}/24; USD={manifest['estimated_usd_from_usage']:.6f}; {PUBLIC}")


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ('dry-run', 'generate', 'publish'):
        raise SystemExit('usage: voice_office_demo_rev2.py dry-run|generate|publish')
    selected = rows()
    if sys.argv[1] == 'dry-run':
        print(f'Approved matched rows: {len(selected)}; cap USD={CAP_USD:.2f}; recent requests={attempts_last_24h(MODEL)}')
        return
    if sys.argv[1] == 'publish':
        publish()
        return
    missing = [row for row in selected if not verify_existing(row, DEST)]
    if attempts_last_24h(MODEL) + len(missing) > MAX_ATTEMPTS_24H:
        raise RuntimeError('Full batch exceeds remaining safe request allowance')
    spent = sum(json.loads(path.read_text())['estimated_usd_from_usage']
                for path in DEST.glob('scene.*.json'))
    genders = set()
    for row in missing:
        if spent + RESERVE_USD > CAP_USD:
            raise RuntimeError('Budget cap reached; no automatic retry or extra takes')
        avatar, key = row['avatar'], row['key']
        if avatar not in genders:
            verified_voice_gender(VOICES[avatar], EXPECTED_GENDER[avatar])
            genders.add(avatar)
        audio, receipt = request_line(key, row['text'], row['rev'], avatar)
        receipt.update(status='office_demo_rev2_draft_for_hearing_not_accepted',
                       generated_utc=datetime.now(timezone.utc).isoformat(),
                       approval='boss-rpg-orders-demo-texts-2026-10-11 [19], sync [21]',
                       pricing_verified_on='2026-10-12',
                       pricing_source='https://ai.google.dev/gemini-api/docs/pricing')
        raw = encode(receipt)
        for base in (STAGE, DEST):
            exact_write(base / (key + '.wav'), audio)
            exact_write(base / (key + '.json'), raw)
        spent += receipt['estimated_usd_from_usage']
        print(f"Recorded {key}: {receipt['duration_seconds']:.2f}s; USD={receipt['estimated_usd_from_usage']:.6f}", flush=True)
        if spent > CAP_USD:
            raise RuntimeError('Last response exhausted budget; output preserved; stop')
    publish()


if __name__ == '__main__':
    main()

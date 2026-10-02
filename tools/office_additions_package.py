#!/usr/bin/env python3
"""Inventory new office sources without accepting takes or altering audio."""

import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import wave

from voice_office_additions import DEST, PASS_CAP_USD, spent
from voice_office_intro import pending_approvals, source_rows, verify_existing

ROOT = Path(__file__).resolve().parent.parent
MAX_DURATION_SECONDS = 11
DURATION_POLICY_REF = 'boss-all-office-recommendations-map-2026-10-02 [26]'


def duration_status(duration):
    # Only this two-item additions batch; no change to prologue/other thoughts.
    return ('source_for_mastering_not_hearing_accepted' if duration <= MAX_DURATION_SECONDS
            else 'rejected_over_duration_limit')


def main():
    rows = [row for item in ('plan_sketch', 'portrait') for row in source_rows(item)]
    if pending_approvals(rows):
        raise ValueError('Current text is not approved in both databases')
    files = []
    for row in rows:
        directory = DEST / f"rev-{row['rev']}"
        if not verify_existing(row, directory):
            raise ValueError('Missing take: ' + row['key'])
        path = directory / (row['key'] + '.wav')
        receipt_path = path.with_suffix('.json')
        receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
        with wave.open(str(path)) as wav:
            if (wav.getnchannels(), wav.getframerate(), wav.getsampwidth()) != (1, 24000, 2):
                raise ValueError('Unexpected source format: ' + row['key'])
            duration = wav.getnframes() / wav.getframerate()
        if abs(duration - receipt['duration_seconds']) > .0001:
            raise ValueError('Receipt duration mismatch: ' + row['key'])
        files.append(dict(
            key=row['key'], engine_key=row['key'].replace('.', '_'),
            item=row['key'].split('.')[-2], avatar=row['avatar'], rev=row['rev'],
            text=row['text'], text_sha256=receipt['text_sha256'],
            wav=str(path.relative_to(ROOT)), wav_sha256=receipt['wav_sha256'],
            receipt=str(receipt_path.relative_to(ROOT)),
            receipt_sha256=hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
            voice=receipt['voice'], gender=receipt['gender'], style=receipt['style'],
            duration_seconds=duration, estimated_usd_from_usage=receipt['estimated_usd_from_usage'],
            status=duration_status(duration),
        ))
    cost = spent()
    if cost > PASS_CAP_USD:
        raise ValueError('Pass budget exceeded')
    ready = [f['key'] for f in files if f['duration_seconds'] <= MAX_DURATION_SECONDS]
    rejected = [f['key'] for f in files if f['duration_seconds'] > MAX_DURATION_SECONDS]
    manifest = dict(
        format='rpg.office-additions-delivery.v1',
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        approval_ref='boss-all-office-recommendations-map-2026-10-02 [18,20]; portrait [4]',
        source_format=dict(channels=1, sample_rate=24000, bits_per_sample=16),
        max_duration_seconds=MAX_DURATION_SECONDS, duration_policy_ref=DURATION_POLICY_REF,
        budget_usd=PASS_CAP_USD, cumulative_estimated_usd_from_usage=cost,
        ready_for_mastering_keys=ready, rejected_duration_keys=rejected,
        hearing_accepted=False, files=files,
    )
    (DEST / 'delivery-manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
    )
    fields = ['key', 'rev', 'avatar', 'voice', 'duration_seconds',
              'estimated_usd_from_usage', 'status', 'wav_sha256', 'text_sha256']
    with (ROOT / 'ai/office-additions-pass-2026-10-02.tsv').open('w', newline='', encoding='utf-8') as out:
        writer = csv.DictWriter(out, fieldnames=fields, delimiter='\t',
                                lineterminator='\n', extrasaction='ignore')
        writer.writeheader()
        writer.writerows(files)
    print(f'Источников: {len(files)}; в пределах {MAX_DURATION_SECONDS} с: {len(ready)}; '
          f'длиннее: {len(rejected)}; USD={cost:.6f}')
    for f in files:
        if f['duration_seconds'] > MAX_DURATION_SECONDS:
            print(f"  {f['key']}: {f['duration_seconds']:.2f} с — на редактуру")


if __name__ == '__main__':
    main()

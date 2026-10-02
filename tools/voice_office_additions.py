#!/usr/bin/env python3
"""Approval-gated voice pass for eight plan thoughts and eight portrait replacements."""

import json
import sys

from voice_office_intro import (
    DEST as BASE_DEST, EXPECTED_GENDER, VOICES, pending_approvals,
    request_line, source_rows, verified_voice_gender, verify_existing,
)

DEST = BASE_DEST / 'additions-20261002'
PASS_CAP_USD = 0.08
MIN_REMAINING_USD = 0.006


def spent():
    return sum(json.loads(path.read_text(encoding='utf-8'))['estimated_usd_from_usage']
               for path in DEST.rglob('scene.office_intro.*.json'))


def main():
    if len(sys.argv) not in (2, 3) or sys.argv[1] not in ('dry-run', 'generate'):
        raise SystemExit('usage: voice_office_additions.py <dry-run|generate> [plan_sketch|portrait|all]')
    batch = sys.argv[2] if len(sys.argv) == 3 else 'all'
    if batch not in ('plan_sketch', 'portrait', 'all'):
        raise SystemExit('invalid voice batch')
    items = ('plan_sketch', 'portrait') if batch == 'all' else (batch,)
    rows = [row for item in items for row in source_rows(item)]
    pending = pending_approvals(rows)
    print(f'office additions: {len(rows)}; awaiting approval/import: {len(pending)}')
    if sys.argv[1] == 'dry-run':
        for row in rows:
            print(f"  {row['key']}: rev={row['rev']}, voice={VOICES[row['avatar']]}")
        return
    if pending:
        raise RuntimeError('No paid TTS before approval and matching strings import')
    DEST.mkdir(parents=True, exist_ok=True)
    for row in rows:
        version_dir = DEST / f"rev-{row['rev']}"
        if verify_existing(row, version_dir):
            print('skip existing ' + row['key'], flush=True)
            continue
        if spent() + MIN_REMAINING_USD > PASS_CAP_USD:
            raise RuntimeError('office additions voice budget cap reached')
        avatar = row['avatar']
        verified_voice_gender(VOICES[avatar], EXPECTED_GENDER[avatar])
        audio, receipt = request_line(row['key'], row['text'], row['rev'], avatar)
        receipt['status'] = 'office_additions_draft_for_review_not_accepted'
        version_dir.mkdir(parents=True, exist_ok=True)
        with (version_dir / (row['key'] + '.wav')).open('xb') as file:
            file.write(audio)
        with (version_dir / (row['key'] + '.json')).open('x', encoding='utf-8') as file:
            json.dump(receipt, file, ensure_ascii=False, indent=2)
            file.write('\n')
        print(f"{row['key']}: {receipt['duration_seconds']:.2f}s; "
              f"USD={receipt['estimated_usd_from_usage']:.6f}", flush=True)


if __name__ == '__main__':
    main()

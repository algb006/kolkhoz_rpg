#!/usr/bin/env python3
"""Preserve completed English API originals in the backed-up RPG voice tree."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = Path('/data/kolkhoz/voice/en-demo-1829-20261117')
DEST = ROOT / 'voice/draft/en-demo-1829-20261117'


def exact_copy(path, raw):
    if path.exists():
        if path.read_bytes() != raw:
            raise RuntimeError('Refusing a different existing original: ' + str(path))
    else:
        with path.open('xb') as handle:
            handle.write(raw)


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    for path in sorted(WORK.glob('scene.*.json')):
        try:
            raw = path.read_bytes()
            receipt = json.loads(raw)
        except json.JSONDecodeError:
            continue  # A working receipt can still be in the writer's open file.
        wav = path.with_suffix('.wav')
        if wav.exists():
            audio = wav.read_bytes()
            if receipt.get('wav_sha256') and hashlib.sha256(audio).hexdigest() != receipt['wav_sha256']:
                raise RuntimeError('Working WAV hash mismatch: ' + wav.name)
            exact_copy(DEST / wav.name, audio)
        exact_copy(DEST / path.name, raw)
    takes = [json.loads(path.read_text()) for path in sorted(DEST.glob('scene.*.json'))]
    manifest = dict(locale='en', status='draft_for_human_hearing_not_accepted',
        completed=sum(t['status']=='english_draft_for_hearing_not_accepted' for t in takes),
        unique_interactions=len({t.get('interaction_id') for t in takes if t.get('interaction_id')}),
        estimated_usd_from_usage=sum(t.get('estimated_usd_from_usage') or 0 for t in takes),
        unresolved_usage=sum(t.get('estimated_usd_from_usage') is None for t in takes),
        source_working_copy=str(WORK), canonical_originals=str(DEST), takes=takes)
    (DEST/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(f"Preserved in RPG voice tree: {manifest['completed']} English takes, {manifest['unique_interactions']} interactions, unresolved {manifest['unresolved_usage']}")


if __name__=='__main__':
    main()

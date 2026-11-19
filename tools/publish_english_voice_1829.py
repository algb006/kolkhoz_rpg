#!/usr/bin/env python3
"""Preserve completed English API originals in the backed-up RPG voice tree."""
import hashlib
import json
from pathlib import Path

from voice_english_demo_1829 import summary

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
        archived = DEST / 'superseded-kolkhoz-20261118' / path.name
        destination = archived.parent if archived.exists() else DEST
        if archived.exists() and archived.read_bytes() != raw:
            raise RuntimeError('Working receipt differs from superseded original: ' + path.name)
        wav = path.with_suffix('.wav')
        if wav.exists():
            audio = wav.read_bytes()
            if receipt.get('wav_sha256') and hashlib.sha256(audio).hexdigest() != receipt['wav_sha256']:
                raise RuntimeError('Working WAV hash mismatch: ' + wav.name)
            exact_copy(destination / wav.name, audio)
        exact_copy(destination / path.name, raw)
    manifest = summary()
    manifest.update(unique_interactions=len({
        t['interaction_id'] for t in manifest['takes'] + manifest['superseded_takes'] + manifest['candidate_takes']
        if t.get('interaction_id')}), source_working_copy=str(WORK), canonical_originals=str(DEST))
    (DEST/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(f"Preserved in RPG voice tree: {manifest['completed']} English takes, {manifest['unique_interactions']} interactions, unresolved {manifest['unresolved_usage']}")


if __name__=='__main__':
    main()

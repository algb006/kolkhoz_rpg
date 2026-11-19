#!/usr/bin/env python3
"""Record the accepted English demo once, with v2 voices and existing quotas."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import urllib.error
import urllib.request
import wave

from voice_prologue_probe import (
    API, VOICES, EXPECTED_GENDER, api_key, audio_from_response,
    modality_tokens, verified_voice_gender,
)
from voice_rate_limit import request_slot, attempts_last_24h, MAX_ATTEMPTS_24H

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'voice/draft/en-demo-1829-20261117'
SOURCE = ROOT / 'manual/texts/en/demo-batch03-prologue-office-intro-1828-2026-11-17.tsv'
MODEL = 'gemini-3.8-flash-tts'
CAP = 0.60
RESERVE = 0.04
STYLE = {
    'villager': 'Unhurried, grounded private thought. Calm rural cadence, no comic dialect.',
    'worker': 'Direct and plain, with a lively working rhythm. Emphasize action, without slogans.',
    'student': 'Young, educated and engaged. Clear diction, a small hesitation before a conclusion.',
    'ex_chairman': 'Dry and cautious, checking a conclusion privately. A restrained ending.',
    'promoted': 'Smooth and measured. Confidence in procedure, a barely noticeable condescension.',
    'old_fighter': 'Firm private thought in short beats, pauses like full stops. Never shouting.',
    'dealer': 'Courteous and quietly ironic. A slight questioning melody in statements, never parody.',
    'acting': 'Collected, practical and economical. Softer only when thinking about people.',
}


def digest(value):
    return hashlib.sha256(value).hexdigest()


def sources():
    with SOURCE.open(newline='') as handle:
        rows = list(csv.DictReader(handle, delimiter='\t'))
    connection = sqlite3.connect(f"file:{ROOT.parent / 'db/strings.db'}?mode=ro", uri=True)
    accepted = sqlite3.connect(f"file:{ROOT / 'db/story.db'}?mode=ro", uri=True)
    active = dict(accepted.execute(
        "SELECT v.line_key,v.voice FROM voice_take v JOIN line l ON l.key=v.line_key "
        "WHERE v.status='accepted' AND l.deprecated=0 AND v.text_rev=l.rev "
        "AND l.approved_rev=l.rev AND l.thought_place IN ('prologue','office')"
    ))
    for row in rows:
        live = connection.execute(
            "SELECT t.text,t.status,t.src_rev,s.rev FROM string_source s "
            "JOIN translation t ON t.string_id=s.string_id "
            "JOIN locale l ON l.id=t.locale_id "
            "WHERE s.namespace=? AND s.key=? AND l.key='en' AND s.deprecated=0",
            (row['namespace'], row['key'])
        ).fetchone()
        revision = int(row['rev'])
        if live != (row['en'], 'ok', revision, revision):
            raise RuntimeError('Exact accepted English required: ' + row['key'])
        row['full_key'] = row['namespace'] + '.' + row['key']
        row['avatar'] = row['key'].split('.')[2] if row['key'].startswith('start.') else row['key'].split('.')[-1]
        if active.get(row['full_key']) != VOICES[row['avatar']]:
            raise RuntimeError('Current accepted Russian/v2 voice mismatch: ' + row['key'])
    if len(rows) != 232 or {r['full_key'] for r in rows} != set(active):
        raise RuntimeError('Expected exactly 232 active prologue/office lines')
    connection.close()
    accepted.close()
    avatar_order = {avatar: i for i, avatar in enumerate(VOICES)}
    rows.sort(key=lambda row: (
        0 if row['key'].startswith('start.') else 1,
        int(row['key'].split('.')[-1][1:]) if row['key'].startswith('start.') else row['key'].split('.')[1],
        avatar_order[row['avatar']],
    ))
    return rows


def receipts():
    return [json.loads(path.read_text()) for path in sorted(DEST.glob('scene.*.json'))]


def prepare_replacements(rows):
    """Preserve the five explicitly superseded takes before recording replacements."""
    impact = json.loads((ROOT / 'ai/kolkhoz-term-1829-voice-impact-2026-11-18.json').read_text())
    expected = {
        'scene.start.prologue.' + suffix
        for suffix in ('acting.t3', 'dealer.t3', 'old_fighter.t8', 'student.t3', 'worker.t3')
    }
    if {item['key'] for item in impact} != expected or len(impact) != 5:
        raise RuntimeError('Replacement authority covers exactly five takes')
    current = {row['full_key']: row for row in rows}
    archive = DEST / 'superseded-kolkhoz-20261118'
    pending = []
    for item in impact:
        key = item['key']
        if current[key]['en'] != item['proposed_text']:
            raise RuntimeError('Replacement transcript changed: ' + key)
        archived_receipt = archive / (key + '.json')
        receipt_path = archived_receipt if archived_receipt.exists() else DEST / (key + '.json')
        receipt = json.loads(receipt_path.read_text())
        if (receipt.get('text') != item['old_text']
            or receipt.get('text_sha256') != digest(item['old_text'].encode())
            or receipt.get('estimated_usd_from_usage') != item['old_cost_usd']
            or receipt.get('status') != 'english_draft_for_hearing_not_accepted'
            or receipt.get('voice') != VOICES[current[key]['avatar']]):
            raise RuntimeError('Unexpected superseded receipt: ' + key)
        for suffix in ('.wav', '.json'):
            target = archive / (key + suffix)
            source = DEST / (key + suffix)
            candidate = target if target.exists() else source
            if not candidate.is_file():
                raise RuntimeError('Missing superseded file: ' + key + suffix)
            if suffix == '.wav' and digest(candidate.read_bytes()) != receipt['wav_sha256']:
                raise RuntimeError('Superseded WAV hash mismatch: ' + key)
            if not target.exists():
                pending.append((source, target))
    archive.mkdir(parents=True, exist_ok=True)
    for source, target in pending:
        if target.exists():
            raise RuntimeError('Refusing archive overwrite: ' + target.name)
        source.rename(target)
    print('Five superseded raw pairs preserved; old usage remains in the pass cap.', flush=True)


def write_new(path, data):
    with path.open('xb') as handle:
        handle.write(data)


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def verify_existing(row):
    key = row['full_key']
    receipt_path = DEST / (key + '.json')
    wav_path = DEST / (key + '.wav')
    if not receipt_path.exists() and not wav_path.exists():
        return False
    if not receipt_path.exists() or not wav_path.exists():
        raise RuntimeError('Partial output needs review: ' + key)
    receipt = json.loads(receipt_path.read_text())
    if (receipt.get('status') != 'english_draft_for_hearing_not_accepted'
        or receipt.get('text_sha256') != digest(row['en'].encode())
        or receipt.get('rev') != int(row['rev'])
        or receipt.get('voice') != VOICES[row['avatar']]
        or receipt.get('wav_sha256') != digest(wav_path.read_bytes())
        or receipt.get('estimated_usd_from_usage') is None):
        raise RuntimeError('Existing English output needs review: ' + key)
    return True


def record(row):
    key, avatar = row['full_key'], row['avatar']
    style = 'English. Read the exact transcript as private internal thought, without additions. ' + STYLE[avatar]
    payload = dict(model=MODEL, input=[dict(type='user_input', content=[dict(
        type='text', text=row['en'], annotations=[dict(type='speech_metadata', style=style)]
    )])], response_format=dict(type='audio'), generation_config=dict(speech_config=[dict(voice=VOICES[avatar])]))
    request = urllib.request.Request(API, data=json.dumps(payload).encode(),
        headers={'x-goog-api-key': api_key(), 'Content-Type': 'application/json'}, method='POST')
    receipt = dict(key=key, locale='en', avatar=avatar, voice=VOICES[avatar],
        gender=EXPECTED_GENDER[avatar], model=MODEL, text=row['en'], rev=int(row['rev']),
        src_rev=int(row['rev']), text_sha256=digest(row['en'].encode()), style=style,
        generated_utc=datetime.now(timezone.utc).isoformat(),
        approval='rpg-boss-english-voice-price-1829-2026-11-17 [2]',
        pricing_source='https://ai.google.dev/gemini-api/docs/pricing',
        estimated_usd_from_usage=None, status='unresolved_usage_or_output')
    superseded = DEST / 'superseded-kolkhoz-20261118' / (key + '.json')
    if superseded.exists():
        old = json.loads(superseded.read_text())
        receipt.update(replacement_authority='boss-rpg-ending-strings-2026-11-18 [5]',
            supersedes_interaction_id=old.get('interaction_id'),
            superseded_receipt=str(superseded.relative_to(ROOT)))
    started = False
    audio = None
    try:
        with request_slot(MODEL, 'en:' + key):
            started = True
            with urllib.request.urlopen(request, timeout=120) as response:
                data = json.load(response)
        usage = data.get('usage') or data.get('interaction', {}).get('usage') or {}
        receipt['usage'] = usage
        receipt['interaction_id'] = data.get('id') or data.get('interaction', {}).get('id')
        text_tokens = modality_tokens(usage, 'input_tokens_by_modality', 'text') or usage.get('total_input_tokens')
        audio_tokens = modality_tokens(usage, 'output_tokens_by_modality', 'audio') or usage.get('total_output_tokens')
        if text_tokens and audio_tokens:
            receipt['estimated_usd_from_usage'] = text_tokens * 0.5 / 1_000_000 + audio_tokens * 9 / 1_000_000
        audio = audio_from_response(data)
        if audio is None or receipt['estimated_usd_from_usage'] is None:
            raise RuntimeError('Missing WAV or billable usage; no automatic retry')
        with wave.open(io.BytesIO(audio), 'rb') as wav:
            channels, rate, width, frames = wav.getnchannels(), wav.getframerate(), wav.getsampwidth(), wav.getnframes()
        receipt.update(wav_sha256=digest(audio), duration_seconds=frames/rate,
            channels=channels, sample_rate=rate, bits_per_sample=width*8)
        if (channels,rate,width) != (1,24000,2):
            raise RuntimeError('Unexpected WAV format; preserve output, stop')
        receipt['status'] = 'english_draft_for_hearing_not_accepted'
    except Exception as exc:
        if not started:
            raise
        receipt['error_kind'] = type(exc).__name__
        if isinstance(exc, urllib.error.HTTPError):
            receipt['http_status'] = exc.code
        # Never persist response bodies, headers, URLs with credentials or exception text.
        if audio is not None:
            write_new(DEST / (key + '.wav'), audio)
        write_new(DEST / (key + '.json'), encode(receipt))
        raise RuntimeError('Paid request stopped; receipt preserved, usage may be unresolved: ' + key) from None
    write_new(DEST / (key + '.wav'), audio)
    write_new(DEST / (key + '.json'), encode(receipt))
    return receipt


def summary():
    takes = receipts()
    superseded = [json.loads(path.read_text()) for path in sorted(
        DEST.glob('superseded-*/scene.*.json'))]
    candidates = [json.loads(path.read_text()) for path in sorted(
        DEST.glob('candidate-*/scene.*.json'))]
    billable = takes + superseded + candidates
    unique = [r.get('interaction_id') for r in billable if r.get('interaction_id')]
    if len(unique) != len(set(unique)):
        raise RuntimeError('Duplicate interaction IDs in English receipts')
    value = dict(locale='en', total_expected=232,
        completed=sum(r['status']=='english_draft_for_hearing_not_accepted' for r in takes),
        receipt_count=len(billable), superseded_receipt_count=len(superseded),
        unresolved_usage=sum(r.get('estimated_usd_from_usage') is None for r in billable),
        estimated_usd_from_usage=sum(r.get('estimated_usd_from_usage') or 0 for r in billable),
        cap_usd=CAP, status='draft_not_hearing_accepted', takes=takes,
        superseded_takes=superseded, candidate_takes=candidates)
    if DEST.exists():
        (DEST / 'manifest.json').write_bytes(encode(value))
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['plan','generate','prepare-replacements'])
    parser.add_argument('--limit',type=int,default=90)
    args=parser.parse_args()
    if not 1 <= args.limit <= 90:
        raise RuntimeError('Window limit must be 1..90; existing quota guard stays unchanged')
    rows=sources()
    if args.mode == 'prepare-replacements':
        prepare_replacements(rows)
    missing=[r for r in rows if not verify_existing(r)]
    state=summary()
    print(f"English inventory {len(rows)}; missing {len(missing)}; spent ${state['estimated_usd_from_usage']:.7f}; model attempts {attempts_last_24h(MODEL)}/{MAX_ATTEMPTS_24H}",flush=True)
    if args.mode in ('plan', 'prepare-replacements'):
        return
    previous_window=ROOT/'ai/localization-en-1828-2026-11-17/voice-window01-result.json'
    if previous_window.exists():
        hearing_path=ROOT/'ai/english-voice-hearing-four-1829-2026-11-17.json'
        hearing=json.loads(hearing_path.read_text())
        if hearing.get('status')!='human_accepted' or not hearing.get('acceptance_source'):
            raise RuntimeError('The next daily window requires the human hearing decision')
        not_before=hearing.get('continuation_not_before_utc')
        if not_before and datetime.now(timezone.utc)<datetime.fromisoformat(not_before):
            raise RuntimeError('The scheduled daily window is not open before '+not_before)
    budget=(ROOT/'ai/gemini-budget-balance.txt').read_text()
    if '1829' not in budget or '$0,60' not in budget:
        raise RuntimeError('Separate human-facing budget/cap entry required before paid work')
    if state['unresolved_usage']:
        raise RuntimeError('Unresolved usage forbids further paid requests')
    DEST.mkdir(parents=True,exist_ok=True)
    verified=set()
    count=0
    try:
        for row in missing:
            if count>=args.limit or attempts_last_24h(MODEL)>=MAX_ATTEMPTS_24H:
                print('Window complete or safe daily request cap reached; no retry.',flush=True)
                break
            if state['estimated_usd_from_usage']+RESERVE>CAP:
                print('Budget reserve reached; stop before the next request.',flush=True)
                break
            if row['avatar'] not in verified:
                verified_voice_gender(VOICES[row['avatar']],EXPECTED_GENDER[row['avatar']])
                verified.add(row['avatar'])
            receipt=record(row)
            count+=1
            state=summary()
            print(f"English {state['completed']}/232 {row['full_key']}: {receipt['duration_seconds']:.2f}s; total ${state['estimated_usd_from_usage']:.7f}",flush=True)
            if state['estimated_usd_from_usage']>CAP:
                raise RuntimeError('Last output exhausted the cap; preserve receipt and stop')
    finally:
        state=summary()
        print(f"Window result: {count} new takes; total {state['completed']}/232; known spend ${state['estimated_usd_from_usage']:.7f}; unresolved {state['unresolved_usage']}",flush=True)


if __name__=='__main__':
    main()

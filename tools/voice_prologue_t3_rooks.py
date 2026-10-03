#!/usr/bin/env python3
"""One approval-gated replacement pass for seven t3 lines; never accept audio."""

import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys

from story import connect
from voice_office_intro import verify_existing
from voice_prologue_probe import EXPECTED_GENDER, VOICES, verified_voice_gender
from voice_prologue_v2 import MODEL, STYLES, request_line

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'manual/texts/prologue-t3-rooks-approved.tsv'
DEST = Path('/data/tmp/rpg-prologue-t3-rooks-20261003')
REVIEW = Path('/data/kolkhoz/voice/prologue/t3-rooks-20261003')
BASELINE = ROOT / 'voice/accepted/prologue'
AUTHORITY = 'boss-rpg-prologue-cemetery-not-seen-2026-10-03#3'
PASS_CAP_USD = 0.03
RESERVE_USD = 0.006
AVATARS = tuple(a for a in VOICES if a != 'ex_chairman')


def final_texts():
    with SOURCE.open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream, delimiter='\t'))
    if len(rows) != 7 or {r['avatar'] for r in rows} != set(AVATARS):
        raise RuntimeError('expected exactly seven changed avatars')
    for row in rows:
        if (row['key'] != f"scene.start.prologue.{row['avatar']}.t3"
                or row['approval_ref'] != AUTHORITY):
            raise RuntimeError('replacement scope or approval differs')
    return rows


def prepare_texts():
    """Update only own database, with the human's text approval from boss [3]."""
    con = connect()
    # Full tuples guard every unselected line, including ex_chairman's metadata.
    baseline = {r['key']: tuple(r) for r in con.execute('SELECT * FROM line')}
    changed = set()
    try:
        for source in final_texts():
            key, avatar = source['key'], source['avatar']
            current = con.execute('SELECT * FROM line WHERE key=?', (key,)).fetchone()
            if current is None:
                raise RuntimeError(f'missing source: {key}')
            context = ('Дорожный пролог, 0:48. Слышно карканье грачей; вдали видна часовня. '
                       'Кладбище и его ограда с телеги не различимы. '
                       f'Внутренняя мысль аватара {avatar}; субтитр и голос, без собеседника.')
            meaning = ('Видимая часовня связывает место с жизнью села до колхоза; '
                       'грачи — слышимый предмет внимания, не доказательство возраста села. '
                       'Местный узнаёт знакомое место, приезжие его осмысляют.')
            keep = (current['keep'] + ' Не называть кладбище или ограду видимыми, '
                    'не объявлять часовню близкой; птицы не предвещают беду.')
            if current['rev'] == 3 and current['text'] == source['text']:
                if (current['approved_rev'] != 3 or current['context'] != context
                        or current['meaning'] != meaning
                        or current['source_ref'] != 'manual/texts/prologue-t3-rooks-approved.tsv'):
                    raise RuntimeError(f'partial or divergent preparation: {key}')
                continue
            if (current['rev'], current['approved_rev']) != (2, 2):
                raise RuntimeError(f'unexpected source revision: {key}')
            old = json.loads((BASELINE / (key + '.json')).read_text(encoding='utf-8'))
            if current['text'] != old['text']:
                raise RuntimeError(f'old accepted text differs: {key}')
            con.execute('UPDATE line SET text=?,context=?,meaning=?,keep=?,source_ref=? WHERE key=?',
                        (source['text'], context, meaning, keep,
                         'manual/texts/prologue-t3-rooks-approved.tsv', key))
            con.execute('UPDATE line SET approved_rev=rev WHERE key=?', (key,))
            if con.execute('SELECT rev FROM line WHERE key=?', (key,)).fetchone()[0] != 3:
                raise RuntimeError(f'expected exactly one revision increment: {key}')
            changed.add(key)
        selected = {r['key'] for r in final_texts()}
        after = list(con.execute('SELECT * FROM line'))
        for row in after:
            if row['key'] not in selected and tuple(row) != baseline[row['key']]:
                raise RuntimeError(f'unrelated line changed: {row["key"]}')
        if {r['key'] for r in after} != set(baseline):
            raise RuntimeError('source key inventory changed')
        con.commit()
        print(f'Own story text prepared: {len(changed)} changed; no foreign DB writes.')
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def source_rows():
    con = connect(design=True)
    con.execute('ATTACH DATABASE ? AS strings',
                (f'file:{ROOT.parent / "db/strings.db"}?mode=ro',))
    policy = con.execute("SELECT voice_policy FROM design.scene WHERE key='scene.start.prologue'").fetchone()
    if tuple(policy) != ('engine_allowed',):
        raise RuntimeError('prologue is not voice-enabled')
    rows = []
    for source in final_texts():
        row = con.execute(
            "SELECT l.key,l.text,l.rev,l.approved_rev,l.thought_avatar avatar,"
            " s.rev string_rev,s.approved_rev string_approved_rev,tr.text string_text"
            " FROM line l LEFT JOIN strings.namespace ns ON ns.key=l.namespace"
            " LEFT JOIN strings.string s ON s.namespace_id=ns.id"
            " AND s.key=substr(l.key,length(l.namespace)+2)"
            " LEFT JOIN strings.locale loc ON loc.key='ru'"
            " LEFT JOIN strings.translation tr ON tr.string_id=s.id AND tr.locale_id=loc.id"
            " WHERE l.key=? AND l.deprecated=0", (source['key'],)).fetchone()
        if row is None or row['text'] != source['text'] or row['avatar'] != source['avatar']:
            raise RuntimeError('own text does not match approved handoff')
        rows.append(dict(row))
    con.close()
    return rows


def pending(rows):
    return [r['key'] for r in rows if not (
        r['rev'] == r['approved_rev'] == 3
        and r['text'] == r['string_text']
        and r['string_rev'] == r['string_approved_rev'] == r['rev'])]


def validate_v2_settings(rows):
    for row in rows:
        old = json.loads((BASELINE / (row['key'] + '.json')).read_text(encoding='utf-8'))
        avatar = row['avatar']
        if (old['voice'] != VOICES[avatar] or old['model'] != MODEL
                or old['style'] != STYLES[avatar] or old.get('inline_tags') != []):
            raise RuntimeError(f'voice v2 settings differ: {avatar}')


def spent():
    return sum(json.loads(p.read_text(encoding='utf-8'))['estimated_usd_from_usage']
               for p in DEST.glob('scene.start.prologue.*.json'))


def copy_review(rows):
    REVIEW.mkdir(parents=True, exist_ok=True)
    manifest = []
    for row in rows:
        if not verify_existing(row, DEST):
            raise RuntimeError(f'missing recorded take: {row["key"]}')
        key = row['key']
        for suffix in ('.wav', '.json'):
            src, dest = DEST / (key + suffix), REVIEW / (key + suffix)
            if dest.exists() and dest.read_bytes() != src.read_bytes():
                raise RuntimeError(f'review copy already differs: {dest}')
            if not dest.exists():
                shutil.copy2(src, dest)
        receipt = json.loads((DEST / (key + '.json')).read_text(encoding='utf-8'))
        manifest.append({k: receipt[k] for k in (
            'key', 'avatar', 'text', 'voice', 'style', 'rev', 'text_sha256',
            'wav_sha256', 'duration_seconds', 'estimated_usd_from_usage')})
    report = {'status': 'draft_pending_human_hearing', 'approval_ref': AUTHORITY,
              'timing_seconds': 48, 'spent_usd_from_usage': spent(), 'lines': manifest}
    for directory in (DEST, REVIEW):
        path = directory / 'manifest.json'
        encoded = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
        if path.exists() and path.read_text(encoding='utf-8') != encoded:
            raise RuntimeError(f'manifest differs: {path}')
        if not path.exists():
            with path.open('x', encoding='utf-8') as stream:
                stream.write(encoded)
    print(f'Review: {REVIEW}; total USD={spent():.7f}')


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ('prepare-texts', 'dry-run', 'generate', 'review'):
        raise SystemExit('usage: voice_prologue_t3_rooks.py <prepare-texts|dry-run|generate|review>')
    if sys.argv[1] == 'prepare-texts':
        prepare_texts()
        return
    rows = source_rows()
    validate_v2_settings(rows)
    waiting = pending(rows)
    print(f'Seven t3 lines; pending approval/import: {len(waiting)}')
    if sys.argv[1] == 'dry-run':
        for row in rows:
            print(f"{row['key']} rev={row['rev']} imported={row['string_rev']} {VOICES[row['avatar']]}")
        return
    if waiting:
        raise RuntimeError('No paid TTS before matching approved strings import')
    if sys.argv[1] == 'review':
        copy_review(rows)
        return
    DEST.mkdir(parents=True, exist_ok=True)
    # Check all voices before the first paid request; requests remain serial.
    for row in rows:
        verified_voice_gender(VOICES[row['avatar']], EXPECTED_GENDER[row['avatar']])
    for row in rows:
        if verify_existing(row, DEST):
            print('skip existing ' + row['key'], flush=True)
            continue
        if spent() + RESERVE_USD > PASS_CAP_USD:
            raise RuntimeError('t3 pass cap reached; no further request')
        audio, receipt = request_line(row['key'], row['text'], row['rev'], row['avatar'])
        receipt.update(status='t3_rooks_draft_pending_human_hearing', approval_ref=AUTHORITY,
                       generated_completed_at_utc=datetime.now(timezone.utc).isoformat(),
                       candidate=1, timing_seconds=48)
        for suffix, contents in (('.wav', audio), ('.json',
                (json.dumps(receipt, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))):
            with (DEST / (row['key'] + suffix)).open('xb') as stream:
                stream.write(contents)
        print(f"{row['key']}: {receipt['duration_seconds']:.2f}s, "
              f"USD={receipt['estimated_usd_from_usage']:.7f}", flush=True)
    copy_review(rows)


if __name__ == '__main__':
    main()

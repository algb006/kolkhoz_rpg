#!/usr/bin/env python3
"""Install only the seven human-heard t3 originals and preserve v2 history."""

import argparse
import json
import wave

from story import connect
from voice_accept_prologue import digest, encoded, keep_exact
from voice_ledger import audit, import_accepted, stored_path
import voice_prologue_t3_rooks as batch

ROOT = batch.ROOT
DEST = ROOT / 'voice/accepted/prologue'
ARCHIVE = ROOT / 'voice/superseded/prologue-v2-t3-20261003'
SOURCE_RECEIPTS = ROOT / 'voice/source-receipts/prologue-t3-rooks-20261003'
THREAD = ROOT.parent / 'claude/mailbox/boss-rpg-prologue-cemetery-not-seen-2026-10-03.md'
BASIS = 'boss-rpg-prologue-cemetery-not-seen-2026-10-03#7'
DATE = '2026-10-03'
STATEMENT = 'Голоса одобряю'


def hearing_gate():
    source = THREAD
    if not source.exists():
        archives = sorted(p for p in (THREAD.parent / 'trash').glob(THREAD.stem + '.*.md')
                          if '.torn.' not in p.name)
        if not archives:
            raise ValueError('Hearing approval thread is missing')
        source = archives[-1]
    text = source.read_text(encoding='utf-8')
    block = text.split('<!-- MSG seq=7 from=boss to=rpg ', 1)[-1]
    if block == text or STATEMENT not in block.split('<!-- /MSG seq=7 -->', 1)[0]:
        raise ValueError('No hearing approval for the seven new takes')


def prepare():
    hearing_gate()
    rows = batch.source_rows()
    if batch.pending(rows):
        raise ValueError('Texts differ or are not approved in both databases')
    raw_manifest = (DEST / 'manifest.json').read_bytes()
    manifest = json.loads(raw_manifest)
    if manifest.get('replacement_basis') == BASIS:
        return None
    if len(manifest['lines']) != 64:
        raise ValueError('Expected 64 accepted prologue lines')
    items = {r['key']: r for r in manifest['lines']}
    if len(items) != 64 or manifest['acceptance_date'] != '2026-09-26':
        raise ValueError('Unexpected baseline manifest')
    untouched = {p.name: digest(p.read_bytes()) for p in DEST.iterdir()
                 if p.suffix in ('.wav', '.json') and p.name != 'manifest.json'
                 and p.stem not in {r['key'] for r in rows}}
    replacements = []
    for row in rows:
        key, avatar = row['key'], row['avatar']
        if not batch.verify_existing(row, batch.DEST):
            raise ValueError(f'Missing approved source: {key}')
        old_audio = (DEST / (key + '.wav')).read_bytes()
        old_raw = (DEST / (key + '.json')).read_bytes()
        old = json.loads(old_raw)
        new_raw = (batch.DEST / (key + '.json')).read_bytes()
        new = json.loads(new_raw)
        audio = (batch.DEST / (key + '.wav')).read_bytes()
        if (old['rev'] != 2 or old['wav_sha256'] != digest(old_audio)
                or items[key]['wav_sha256'] != digest(old_audio)
                or new['text'] != row['text'] or new['approved_rev'] != 3
                or new['gender'] != batch.EXPECTED_GENDER[avatar]
                or new['voice'] != old['voice'] or new['style'] != old['style']
                or new['model'] != old['model'] or new['inline_tags'] != old['inline_tags']
                or new['status'] != 't3_rooks_draft_pending_human_hearing'):
            raise ValueError(f'Unexpected original or v2 settings: {key}')
        with wave.open(str(batch.DEST / (key + '.wav'))) as wav:
            if (wav.getnchannels(), wav.getframerate(), wav.getsampwidth()) != (1, 24000, 2):
                raise ValueError(f'Unexpected WAV format: {key}')
            if abs(wav.getnframes() / wav.getframerate() - new['duration_seconds']) > .0001:
                raise ValueError(f'Duration differs: {key}')
        new.update(status='accepted_for_demo_prologue_pending_sound_mastering',
                   source_status=new['status'], voice_passport=old['voice_passport'],
                   source_generation_time_utc=new['generated_completed_at_utc'],
                   generation_time_kind='completion',
                   acceptance=dict(date=DATE, scope='demo_prologue_t3_replacement',
                       by='human_project_owner', statement=STATEMENT, basis=BASIS,
                       original_receipt_sha256=digest(new_raw)))
        replacements.append(dict(key=key, old_audio=old_audio, old_raw=old_raw,
                                 old=old, audio=audio, receipt=new, source_raw=new_raw))
    return rows, raw_manifest, manifest, replacements, untouched


def relocate_history(con, replacements):
    """Move own ledger paths, including all measurement and master references."""
    con.execute('PRAGMA defer_foreign_keys=ON')
    for item in replacements:
        key, old = item['key'], item['old']
        old_path = stored_path(DEST / (key + '.wav'))
        archived = stored_path(ARCHIVE / (key + '.wav'))
        take = f'{key}.rev2.{old["wav_sha256"][:16]}'
        current = con.execute('SELECT take_key,sha256 FROM voice_file WHERE path=?',
                              (old_path,)).fetchone()
        if current is None or tuple(current) != (take, old['wav_sha256']):
            raise ValueError(f'Old ledger source differs: {key}')
        if con.execute('SELECT 1 FROM voice_file WHERE path=?', (archived,)).fetchone():
            raise ValueError(f'Archive already registered: {key}')
        con.execute('UPDATE voice_file SET path=? WHERE path=?', (archived, old_path))
        con.execute('UPDATE voice_file SET source_path=? WHERE source_path=?',
                    (archived, old_path))
        con.execute('UPDATE voice_measurement SET file_path=? WHERE file_path=?',
                    (archived, old_path))
        con.execute("UPDATE voice_take SET receipt_path=?,status='superseded' WHERE key=?",
                    (stored_path(ARCHIVE / (key + '.json')), take))


def verify_installed():
    hearing_gate()
    rows = batch.source_rows()
    if batch.pending(rows):
        raise ValueError('Current approved text changed')
    manifest = json.loads((DEST / 'manifest.json').read_bytes())
    keys = {r['key'] for r in rows}
    if manifest.get('replacement_basis') != BASIS or len(manifest['lines']) != 64:
        raise ValueError('Replacement manifest is missing')
    archived = json.loads((ARCHIVE / 'manifest.json').read_bytes())
    if {r['key'] for r in archived['lines']} != keys or len(archived['lines']) != 7:
        raise ValueError('Wrong archive scope')
    before = json.loads((ARCHIVE / 'package_manifest_before_replacement.json').read_bytes())
    for entry in before['lines']:
        directory = ARCHIVE if entry['key'] in keys else DEST
        if digest((directory / entry['wav']).read_bytes()) != entry['wav_sha256']:
            raise ValueError('A preserved v2 original changed')
    for entry in manifest['lines']:
        receipt = json.loads((DEST / entry['receipt']).read_bytes())
        audio = (DEST / entry['wav']).read_bytes()
        if digest(audio) != entry['wav_sha256'] or digest(audio) != receipt['wav_sha256']:
            raise ValueError('Accepted WAV changed')
        if entry['key'] in keys:
            row = next(r for r in rows if r['key'] == entry['key'])
            if (receipt['text'] != row['text'] or receipt['rev'] != 3
                    or receipt['acceptance'].get('basis') != BASIS):
                raise ValueError('Wrong acceptance or revision')
            original = SOURCE_RECEIPTS / (entry['key'] + '.json')
            if digest(original.read_bytes()) != receipt['acceptance']['original_receipt_sha256']:
                raise ValueError('Original API receipt changed')
    con = connect()
    try:
        errors, report = audit(con)
        if errors or con.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError(f'Ledger audit failed: {errors}')
        print(report[-1])
    finally:
        con.close()
    print('Verified: seven rev3 accepted originals, seven archived rev2; no API.')


def install(plan):
    rows, old_manifest_bytes, manifest, replacements, untouched = plan
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    SOURCE_RECEIPTS.mkdir(parents=True, exist_ok=True)
    keep_exact(ARCHIVE / 'package_manifest_before_replacement.json', old_manifest_bytes)
    archive_manifest = dict(manifest)
    archive_manifest.update(status='superseded_subset_v2_t3', replacement_date=DATE,
                            replacement_basis=BASIS, count=7,
                            totals_scope='historical_full_64_line_package_before_replacement',
                            lines=[r for r in manifest['lines'] if r['key'] in
                                   {row['key'] for row in rows}])
    keep_exact(ARCHIVE / 'manifest.json', encoded(archive_manifest))
    for item in replacements:
        keep_exact(ARCHIVE / (item['key'] + '.wav'), item['old_audio'])
        keep_exact(ARCHIVE / (item['key'] + '.json'), item['old_raw'])
        keep_exact(SOURCE_RECEIPTS / (item['key'] + '.json'), item['source_raw'])
    con = connect()
    try:
        con.execute('BEGIN')
        relocate_history(con, replacements)
        for item in replacements:
            (DEST / (item['key'] + '.wav')).write_bytes(item['audio'])
            (DEST / (item['key'] + '.json')).write_bytes(encoded(item['receipt']))
        changed = {r['key']: r for r in replacements}
        for entry in manifest['lines']:
            receipt = json.loads((DEST / entry['receipt']).read_bytes())
            entry.update(acceptance_date=receipt['acceptance']['date'],
                         acceptance_statement=receipt['acceptance']['statement'])
            if entry['key'] in changed:
                new = changed[entry['key']]['receipt']
                entry.update(rev=3, text_sha256=new['text_sha256'],
                             wav_sha256=new['wav_sha256'], acceptance_basis=BASIS)
        manifest.update(replacement_basis=BASIS, last_replacement_date=DATE,
                        last_replacement_statement=STATEMENT,
                        replaced_keys=list(changed),
                        replacement_source=str(batch.DEST),
                        replacement_archive=str(ARCHIVE.relative_to(ROOT)),
                        replacement_cost_usd=sum(r['receipt']['estimated_usd_from_usage']
                                                 for r in replacements),
                        subtitle_authority='db/story.db; 7 t3 rev3, other 57 rev2',
                        mastering_status='pending_seven_t3_replacements')
        totals = dict(requests=64, input_tokens=0, output_audio_tokens=0,
                      duration_seconds=0., estimated_usd_from_usage=0.)
        for entry in manifest['lines']:
            receipt = json.loads((DEST / entry['receipt']).read_bytes())
            totals['input_tokens'] += receipt['usage']['total_input_tokens']
            totals['output_audio_tokens'] += receipt['usage']['total_output_tokens']
            totals['duration_seconds'] += receipt['duration_seconds']
            totals['estimated_usd_from_usage'] += receipt['estimated_usd_from_usage']
        manifest['totals'] = totals  # Cost of the selected 64, not lifetime expenditure.
        (DEST / 'manifest.json').write_bytes(encoded(manifest))
        import_accepted(con, DEST)
        if any(digest((DEST / name).read_bytes()) != checksum
               for name, checksum in untouched.items()):
            raise ValueError('An unrelated accepted file changed')
        errors, _ = audit(con)
        if errors or con.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError(f'Ledger audit failed: {errors}')
        con.commit()
    except Exception:
        con.rollback()
        for item in replacements:
            (DEST / (item['key'] + '.wav')).write_bytes(item['old_audio'])
            (DEST / (item['key'] + '.json')).write_bytes(item['old_raw'])
        (DEST / 'manifest.json').write_bytes(old_manifest_bytes)
        raise
    finally:
        con.close()
    verify_installed()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    plan = prepare()
    if plan is None:
        verify_installed()
    elif args.check_only:
        print('Prepared seven replacements; archive and acceptance checked; API 0.')
    else:
        install(plan)


if __name__ == '__main__':
    main()

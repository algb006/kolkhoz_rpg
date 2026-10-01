#!/usr/bin/env python3
"""Опись мыслей и дублей. Только импорт существующих файлов, без API и обработки WAV."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parent.parent
AVATARS = ('villager','worker','student','ex_chairman','promoted','old_fighter','dealer','acting')


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def json_text(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def resolve(path, root=ROOT):
    path = Path(path)
    return path if path.is_absolute() else root / path


def stored_path(path, root=ROOT):
    path = Path(path).resolve()
    try:
        return str(path.relative_to(root.resolve()))
    except ValueError:
        return str(path)


def mark_thoughts(con):
    """Однократная классификация не меняет текст, rev или его утверждение."""
    trigger = con.execute("SELECT sql FROM sqlite_master WHERE type='trigger' AND name='line_source_changed'").fetchone()[0]
    con.execute('SAVEPOINT classify_thoughts')
    con.execute('DROP TRIGGER line_source_changed')
    try:
        for key, scene, variant in con.execute(
            "SELECT key,scene_key,variant_key FROM line WHERE scene_key IN ('scene.start.prologue','scene.start.office')"
        ).fetchall():
            existing = con.execute(
                'SELECT kind,thought_avatar,thought_place,thought_trigger_kind,thought_trigger_ref FROM line WHERE key=?',
                (key,),
            ).fetchone()
            # Authored signals (e.g. exit_choice) must not become item clicks on reimport.
            if existing[0] == 'spoken_thought' and all(existing[1:]):
                continue
            if scene.endswith('prologue'):
                avatar = key.split('.')[-2]
                place, kind, ref = 'prologue', 'scene', f'{scene}#{key.split(".")[-1]}'
            else:
                avatar = key.split('.')[-1]
                place, kind, ref = 'office', 'item', variant
                if ref == 'office_intro.enter':
                    kind, ref = 'scene', scene
            if avatar not in AVATARS or not ref:
                raise ValueError(f'Не размечается мысль: {key}')
            con.execute(
                'UPDATE line SET kind=?,thought_avatar=?,thought_place=?,thought_trigger_kind=?,thought_trigger_ref=? WHERE key=?',
                ('spoken_thought',avatar,place,kind,ref,key),
            )
    except Exception:
        con.execute('ROLLBACK TO classify_thoughts')
        con.execute('RELEASE classify_thoughts')
        raise
    else:
        con.execute(trigger)
        con.execute('RELEASE classify_thoughts')


def import_accepted(con, directory, root=ROOT):
    count = 0
    for receipt in sorted(Path(directory).rglob('*.json')):
        if receipt.name == 'manifest.json':
            continue
        d = json.loads(receipt.read_text(encoding='utf-8'))
        wav = receipt.with_suffix('.wav')
        checksum = sha(wav)
        if checksum != d['wav_sha256']:
            raise ValueError(f'Сумма WAV не совпадает: {wav}')
        line = con.execute('SELECT rev,text,thought_avatar FROM line WHERE key=?',(d['key'],)).fetchone()
        if line is None or line[2] != d['avatar']:
            raise ValueError(f'Нет мысли нужного аватара: {d["key"]}')
        text_hash = hashlib.sha256(d['text'].encode()).hexdigest()
        if d.get('text_sha256') != text_hash:
            raise ValueError(f'Сумма текста квитанции не совпадает: {receipt}')
        if line[0] == d['rev'] and line[1] != d['text']:
            raise ValueError(f'Одна редакция имеет разные тексты: {receipt}')
        if d['rev'] > line[0]:
            raise ValueError(f'Квитанция из будущей редакции: {receipt}')
        take = f'{d["key"]}.rev{d["rev"]}.{checksum[:16]}'
        settings = {k:d[k] for k in ('style','inline_tags','sample_rate','channels','bits_per_sample') if k in d}
        values = (take,d['key'],d['rev'],text_hash,d['avatar'],d['voice'],json_text(d['voice_passport']),
                  d['model'],json_text(settings),stored_path(receipt,root),d.get('source_generation_time_utc'),'accepted')
        old = con.execute('SELECT * FROM voice_take WHERE key=?',(take,)).fetchone()
        if old and tuple(old) != values:
            raise ValueError(f'Изменился существующий дубль: {take}')
        if not old:
            con.execute('INSERT INTO voice_take VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',values)
        file_values = (stored_path(wav,root),take,'accepted_original',checksum,None,None,d.get('duration_seconds'))
        old_file = con.execute('SELECT * FROM voice_file WHERE path=?',(file_values[0],)).fetchone()
        if old_file and tuple(old_file) != file_values:
            raise ValueError(f'Изменилось представление: {wav}')
        if not old_file:
            con.execute('INSERT INTO voice_file VALUES(?,?,?,?,?,?,?)',file_values)
        count += 1
    return count


def import_measurements(con, package, root=ROOT):
    con.execute('SAVEPOINT import_measurements')
    try:
        result = _import_measurements(con,package,root)
    except Exception:
        con.execute('ROLLBACK TO import_measurements')
        con.execute('RELEASE import_measurements')
        raise
    con.execute('RELEASE import_measurements')
    return result


def _import_measurements(con, package, root=ROOT):
    data = json.loads(Path(package).read_text(encoding='utf-8'))
    if data.get('schema',data.get('format')) != 'sound.voice-measurements.v1':
        raise ValueError('Ожидается schema/format=sound.voice-measurements.v1')
    if data.get('provenance_report'):
        if sha(resolve(data['provenance_report'],root)) != data.get('provenance_report_sha256'):
            raise ValueError('Не совпадает сумма отчёта происхождения измерений')
    instrument = {k:v for k,v in data.items() if k not in ('files',)}
    seen = set()
    for d in data['files']:
        path = resolve(d['path'],root).resolve()
        name = stored_path(path,root)
        if name in seen:
            raise ValueError(f'Дубль файла в пакете: {name}')
        seen.add(name)
        if sha(path) != d['sha256']:
            raise ValueError(f'Измерен другой WAV: {name}')
        file = con.execute('SELECT take_key,file_role,sha256,source_sha256 FROM voice_file WHERE path=?',(name,)).fetchone()
        if not file:
            if d['file_role'] != 'technical_master' or not d['source_sha256']:
                raise ValueError(f'Неизвестный исходник: {name}')
            sources = con.execute("SELECT path,take_key FROM voice_file WHERE sha256=? AND file_role='accepted_original'",(d['source_sha256'],)).fetchall()
            if len(sources) != 1:
                raise ValueError(f'Неоднозначный/неизвестный исходник мастера: {name}')
            source, take = sources[0]
            if sha(resolve(source,root)) != d['source_sha256']:
                raise ValueError(f'Исходник мастера изменился: {source}')
            con.execute('INSERT INTO voice_file VALUES(?,?,?,?,?,?,?)',
                        (name,take,'technical_master',d['sha256'],source,d['source_sha256'],None))
            file = (take,'technical_master',d['sha256'],d['source_sha256'])
        if tuple(file[1:]) != (d['file_role'],d['sha256'],d['source_sha256']):
            raise ValueError(f'Файл или связь мастера изменились: {name}')
        take = con.execute('SELECT line_key,text_rev,avatar FROM voice_take WHERE key=?',(file[0],)).fetchone()
        if tuple(take) != (d['key'],d['rev'],d['avatar']):
            raise ValueError(f'Замер привязан к чужому дублю: {name}')
        for field in ('duration_seconds','lufs','peak_dbtp'):
            value = d[field]
            if value is not None and (isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value)):
                raise ValueError(f'Нечисловое измерение {field}: {name}')
        if sha(path) != d['sha256']:
            raise ValueError(f'WAV изменился при импорте: {name}')
        provenance = dict(instrument)
        for field in ('loudness_provenance','duration_verified_at_utc'):
            if field in d:
                provenance[field] = d[field]
        identity = hashlib.sha256(json_text({'file':d,'instrument':instrument}).encode()).hexdigest()
        values = (identity,name,d['sha256'],d['measured_at_utc'],d['duration_seconds'],d['lufs'],d['peak_dbtp'],
                  d['measurement_status'],d['error'],json_text(provenance))
        old = con.execute('SELECT * FROM voice_measurement WHERE key=?',(identity,)).fetchone()
        if old and tuple(old) != values:
            raise ValueError(f'Замер переписан под прежним временем: {name}')
        if not old:
            con.execute('INSERT INTO voice_measurement VALUES(?,?,?,?,?,?,?,?,?,?)',values)
    return len(seen)


def audit(con, root=ROOT, accepted=None):
    """Вернуть ошибки и сводку; нулевые клетки печатаются явно."""
    errors = []
    valid_files = set()
    measured = set()
    files = con.execute('SELECT path,take_key,sha256,source_path,source_sha256 FROM voice_file').fetchall()
    for path,take,checksum,source,source_hash in files:
        actual = resolve(path,root)
        if not actual.is_file():
            errors.append(f'Строка без файла: {path}')
        elif sha(actual) != checksum:
            errors.append(f'Сумма файла изменилась: {path}')
        else:
            valid_files.add(path)
        if source:
            ref = con.execute('SELECT take_key,sha256 FROM voice_file WHERE path=?',(source,)).fetchone()
            if ref is None or tuple(ref) != (take,source_hash):
                errors.append(f'Чужой исходник мастера: {path}')
        for m in con.execute('SELECT measured_sha256,measurement_status FROM voice_measurement WHERE file_path=?',(path,)):
            if m[0] != checksum:
                errors.append(f'Замер другого файла: {path}')
        latest = con.execute('SELECT measured_sha256,measurement_status FROM latest_voice_measurement WHERE file_path=?',(path,)).fetchone()
        if latest and tuple(latest) == (checksum,'ok') and path in valid_files:
            measured.add(path)
    registered = {resolve(r[0],root).resolve() for r in files}
    accepted = Path(accepted) if accepted is not None else root/'voice/accepted'
    orphans = [p for p in accepted.rglob('*.wav') if p.resolve() not in registered]
    errors.extend(f'Файл без строки: {stored_path(p,root)}' for p in orphans)
    for receipt in accepted.rglob('*.json'):
        if receipt.name != 'manifest.json' and not receipt.with_suffix('.wav').is_file():
            errors.append(f'Квитанция без WAV: {stored_path(receipt,root)}')
    current, stale, measured_lines = set(),set(),set()
    for key,line,rev,avatar,status,now,line_avatar in con.execute(
        'SELECT t.key,t.line_key,t.text_rev,t.avatar,t.status,l.rev,l.thought_avatar FROM voice_take t JOIN line l ON l.key=t.line_key'
    ):
        if avatar != line_avatar or rev > now:
            errors.append(f'Неверный аватар/редакция дубля: {key}')
        receipt,text_hash = con.execute('SELECT receipt_path,text_sha256 FROM voice_take WHERE key=?',(key,)).fetchone()
        if not resolve(receipt,root).is_file():
            errors.append(f'Нет квитанции дубля: {receipt}')
        if rev == now:
            text = con.execute('SELECT text FROM line WHERE key=?',(line,)).fetchone()[0]
            if hashlib.sha256(text.encode()).hexdigest() != text_hash:
                errors.append(f'Редакция совпала, но текст дубля другой: {key}')
        paths = {p for p,t,_,_,_ in files if t == key}
        if not paths:
            errors.append(f'Дубль без файловой записи: {key}')
        if status == 'accepted' and paths & valid_files:
            (current if rev == now else stale).add(line)
            if rev == now and paths & measured:
                measured_lines.add(line)
    groups = {}
    for key,avatar,place,kind,ref in con.execute(
        "SELECT key,thought_avatar,thought_place,thought_trigger_kind,thought_trigger_ref FROM line WHERE kind='spoken_thought' AND deprecated=0"
    ):
        groups.setdefault((place,kind,ref),{}).setdefault(avatar,set()).add(key)
    report = []
    for (place,kind,ref),members in sorted(groups.items()):
        for avatar in AVATARS:
            keys = members.get(avatar,set())
            report.append(f'{place} / {kind}:{ref} / {avatar}: всего {len(keys)}; '
                          f'текущий текст {len(keys&current)}; старый {len(keys&stale)}; '
                          f'ждут {len(keys-current)}; не измерено {len((keys&current)-measured_lines)}')
            for key in sorted(keys&stale):
                report.append(f'  Старая редакция: {key}')
    missing = sum(not resolve(p,root).is_file() for p,_,_,_,_ in files)
    no_files = sum(not any(t==key for _,t,_,_,_ in files)
                   for key, in con.execute('SELECT key FROM voice_take'))
    report.append(f'Файлов без строки: {len(orphans)}; строк без файла: {missing}; дублей без файловой записи: {no_files}; '
                  f'файлов без успешного замера: {len(valid_files-measured)}')
    report.append(f'Мыслей всего: {sum(len(k) for m in groups.values() for k in m.values())}; '
                  f'озвучено по текущему тексту: {len(current)}; по старому: {len(stale)}; '
                  f'ждут: {sum(len(k-current) for m in groups.values() for k in m.values())}')
    return errors,report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('import-accepted','import-measurements'))
    parser.add_argument('package',nargs='?')
    args = parser.parse_args()
    with sqlite3.connect(ROOT/'db/story.db') as con:
        con.execute('PRAGMA foreign_keys=ON')
        con.execute('BEGIN')
        if args.command == 'import-accepted':
            mark_thoughts(con)
            count = import_accepted(con,ROOT/'voice/accepted')
        else:
            if not args.package:
                parser.error('нужен путь JSON пакета замеров')
            count = import_measurements(con,args.package)
        if con.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Нарушены внешние ключи')
    print(f'Импортировано/проверено записей: {count}. API и TTS не запускались.')


if __name__ == '__main__':
    main()

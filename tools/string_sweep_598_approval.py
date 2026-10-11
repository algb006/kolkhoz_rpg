#!/usr/bin/env python3
"""Record boss move 2 against the delivered snapshot, without DB resnapshot/import."""

import csv
import sqlite3
import sys
from string_sweep_598 import BASE, REPLACEMENTS, NEW


def main():
    if sys.argv[1:] not in ([], ['--verify-import']):
        raise SystemExit('usage: string_sweep_598_approval.py [--verify-import]')
    verified = bool(sys.argv[1:])
    path = BASE.with_suffix('.csv')
    with path.open(newline='', encoding='utf-8') as source:
        reader = csv.DictReader(source)
        fields = reader.fieldnames
        records = list(reader)
    expected = {**REPLACEMENTS, **NEW}
    if len(records) != 53 or {r['key'] for r in records} != set(expected):
        raise ValueError('Not the delivered 53-row snapshot')
    if not verified and any('verified' in r['status'] for r in records):
        raise ValueError('Refusing to downgrade an import receipt to approval only')
    if verified:
        shared = BASE.parents[3] / 'db/strings.db'
        with sqlite3.connect(f'file:{shared}?mode=ro', uri=True) as con:
            for r in records:
                got = con.execute("""SELECT t.text,s.rev,s.approved_rev FROM string s
                    JOIN namespace n ON n.id=s.namespace_id JOIN translation t ON t.string_id=s.id
                    JOIN locale l ON l.id=t.locale_id WHERE l.is_source=1 AND n.key||'.'||s.key=?""",
                    (r['key'],)).fetchone()
                wanted = r['before'] if r['key'] == 'ui.office.own.black_cash' else expected[r['key']]
                if not got or got[0] != wanted:
                    raise ValueError('Import differs: ' + r['key'])
                if r['origin'] != 'design' and r['key'] != 'ui.office.own.black_cash' and got[1] != got[2]:
                    raise ValueError('Import not approved: ' + r['key'])
    for r in records:
        key = r['key']
        wanted = r['before'] if key == 'ui.office.own.black_cash' else expected[key]
        if r['after'] not in (expected[key], wanted):
            raise ValueError('Changed literal proposal: ' + key)
        r['after'] = wanted
        r['status'] = ('retained_verified' if key == 'ui.office.own.black_cash' else 'imported_verified') if verified else ('approved_retained' if key == 'ui.office.own.black_cash' else 'approved_pending_import')
        r['note'] += '' if 'Approval: sweep thread [2].' in r['note'] else ' Approval: sweep thread [2].'
        if key == 'ui.office.own.black_cash':
            r['note'] = 'Approval: sweep thread [2]. Retain Чёрная касса; valid period term, Epoch II shadow gate unchanged. Prior rename proposal rejected.'
    with path.open('w', newline='', encoding='utf-8') as target:
        writer = csv.DictWriter(target, fieldnames=fields, lineterminator='\n')
        writer.writeheader(); writer.writerows(records)
    with BASE.with_suffix('.txt').open('w', encoding='utf-8') as target:
        target.write('Ревизия строк №598 — решение босса, 12 октября 2026\n\n')
        target.write('52 формулировки импортированы; «Чёрная касса» сохранена. Все 53 текста сверены с общей базой.\n' if verified else '52 формулировки утверждены; название «Чёрная касса» сохранено. Квитанция импорта ещё ожидается.\n')
        target.write('Ключ | Было | Утверждено | Статус\n')
        for r in records:
            status = 'Название сохранено' if key_is_retained(r) else ('Импорт сверён' if verified else 'Утверждено; импорт ожидается')
            target.write(' | '.join((r['key'], r['before'], r['after'], status)) + '\n')
        target.write('\nUE показывает игровое время вместо номера шага. Core проверяет, что потеря озимых фиксируется только после октября.\n')
        target.write('Подсказка о довольстве следует принятой формуле предела по худшему показателю. Пять новых ключей и родовые варианты освобождения утверждены.\n')
        target.write('«Партия» в поставках поросят и птицы остаётся партией товара. Открытие теневых денег в первой эпохе не вводится.\n')
    print('Import verified: 53/53 literal rows; no DB/audio writes.' if verified else 'Approval recorded: 52 approved wordings, 1 retained; no DB or audio writes.')


def key_is_retained(row):
    return row['key'] == 'ui.office.own.black_cash'


if __name__ == '__main__':
    main()

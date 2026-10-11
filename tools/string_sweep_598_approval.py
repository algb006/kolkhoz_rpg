#!/usr/bin/env python3
"""Record boss move 2 against the delivered snapshot, without DB resnapshot/import."""

import csv
from string_sweep_598 import BASE, REPLACEMENTS, NEW


def main():
    path = BASE.with_suffix('.csv')
    with path.open(newline='', encoding='utf-8') as source:
        reader = csv.DictReader(source)
        fields = reader.fieldnames
        records = list(reader)
    expected = {**REPLACEMENTS, **NEW}
    if len(records) != 53 or {r['key'] for r in records} != set(expected):
        raise ValueError('Not the delivered 53-row snapshot')
    for r in records:
        key = r['key']
        wanted = r['before'] if key == 'ui.office.own.black_cash' else expected[key]
        if r['after'] not in (expected[key], wanted):
            raise ValueError('Changed literal proposal: ' + key)
        r['after'] = wanted
        r['status'] = 'approved_retained' if key == 'ui.office.own.black_cash' else 'approved_pending_import'
        r['note'] += '' if 'Approval: sweep thread [2].' in r['note'] else ' Approval: sweep thread [2].'
        if key == 'ui.office.own.black_cash':
            r['note'] = 'Approval: sweep thread [2]. Retain Чёрная касса; valid period term, Epoch II shadow gate unchanged. Prior rename proposal rejected.'
    with path.open('w', newline='', encoding='utf-8') as target:
        writer = csv.DictWriter(target, fieldnames=fields)
        writer.writeheader(); writer.writerows(records)
    with BASE.with_suffix('.txt').open('w', encoding='utf-8') as target:
        target.write('Ревизия строк №598 — решение босса, 12 октября 2026\n\n')
        target.write('52 формулировки утверждены; название «Чёрная касса» сохранено. Квитанция импорта ещё ожидается.\n')
        target.write('Ключ | Было | Утверждено | Статус\n')
        for r in records:
            status = 'Название сохранено' if r['status'] == 'approved_retained' else 'Утверждено; импорт ожидается'
            target.write(' | '.join((r['key'], r['before'], r['after'], status)) + '\n')
        target.write('\nUE показывает игровое время вместо номера шага. Core проверяет, что потеря озимых фиксируется только после октября.\n')
        target.write('Подсказка о довольстве следует принятой формуле предела по худшему показателю. Пять новых ключей и родовые варианты освобождения утверждены.\n')
        target.write('«Партия» в поставках поросят и птицы остаётся партией товара. Открытие теневых денег в первой эпохе не вводится.\n')
    print('Approval recorded: 52 approved wordings, 1 retained; no DB or audio writes.')


if __name__ == '__main__':
    main()

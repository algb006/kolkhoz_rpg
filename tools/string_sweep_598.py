#!/usr/bin/env python3
"""Build a read-only, keyed proposal snapshot; never import shared strings."""

import csv
import json
from pathlib import Path
import re
import sqlite3

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / 'manual/texts/string-sweep-598-2026-10-12'

# Existing keys are retained. Design-origin rows require upstream source edits.
REPLACEMENTS = {
    'ui.office.works.summary_lead': 'Наряды выдаёт учётчик. Пока он не назначен, выдавайте наряды сами. Любой наряд можно изменить.',
    'glossary.work_order': 'Запись, кому и где работать в течение суток. Наряды выдаёт учётчик, а пока он не назначен — председатель. Председатель может изменить любой наряд.',
    'glossary.zyab': 'Осенняя вспашка поля под весенний сев. После уборки и вывоза урожая людей направляют на вспашку по наряду учётчика или председателя. Весной остаётся бороновать и сеять.',
    'hint.hint_15.text': 'В неутеплённом скотном дворе скот зимой мёрзнет. До холодов утеплите двор; если не успеваете закончить глиняное утепление, предусмотрена соломенная шуба на одну зиму.',
    'hint.hint_24.text': 'Пока везут материалы для улучшения, постройка работает в полную силу. Вполсилы — только с началом работ.',
    'hint.hint_25.text': 'Улучшение полностью устраняет износ: ветхую постройку бывает выгоднее улучшить, чем ремонтировать.',
    'hint.hint_28.text': 'Производство остановилось не из-за поломки: готовую продукцию некуда складывать. Проверьте, вывозит ли её возчик.',
    'hint.hint_36.text': 'Письмо идёт неделю, плата за отправку не нужна. Переписка с районом — в журнале входящих и исходящих.',
    'hint.hint_41.text': 'Если сытость, общее дело, потребности или отдых падают ниже 20, общее довольство ограничено удвоенным значением худшего из этих показателей.',
    'quest.quest_e1_08.body': 'До холодов утеплить скотный двор: подойдёт утеплённый двор или соломенная шуба на одну зиму.',
    'quest.quest_e1_16.body': 'Утеплить хотя бы одну постройку до следующей зимы.',
    'quest.quest_e1_00.body': 'Разметить село: где дворы, где склады, где дороги. Разметка ничего не стоит. Перенос уже устроенного хозяйства может потребовать времени и новых работ.',
    'unit.manure_pile.advice': 'Отвести сразу с запасом под будущее стадо. Для смены места заполненной кучи придётся очистить старую площадку; полная очистка занимает до девяти месяцев.',
    'unit.silage_trench.advice': 'Ближе к полям: осенью сюда везут зелёную массу. Место выбирайте с запасом под будущее стадо.',
    'alarm.winter_crop_unsowable.title': 'Озимая после поздней уборки',
    'alarm.winter_crop_unsowable.tip': 'Перед озимой поставьте культуру с ранней уборкой или пар. Обычный срок сева — август–сентябрь года перед урожаем. В октябре ещё можно сеять, если хватает тепла, но урожай будет меньше. Не посеяли до конца октября — поле останется под паром.',
    'feed.winter_sowing_lost': 'Поле{place}: до конца октября озимые не посеяны — урожая озимых в следующем году не будет.',
    'alarm.site_without_materials.tip': 'Привезите материалы по лимиту, купите их или измените очередь снабжения стройки. Без материалов работы не начнутся.',
    'unit.farm_office.blurb': 'Правление и кабинет председателя: здесь работают его помощники. Потеря правления заканчивает игру.',
    'ui.office.journal.tick': 'Время',
    'ui.office.personal.development': 'Развитие и умения',
    'ui.office.works.nomenclature': 'Что производить',
    'ui.office.outside.requests': 'Заявки и поставки района',
    'ui.office.works.delegation': 'Полномочия помощников',
    'ui.office.works.feed_table': 'Кормление стада',
    'ui.office.own.black_cash': 'Теневые деньги и запасы',
    'unit.granary.level2.name': 'Улучшенный зерновой амбар',
    'perk.single.name': 'Отдельные умения',
    'perk.owner_eye_4.name': '«То же по объектам хозяйства»',
    'perk.gas_stoves.effect': 'Открывает газ в баллонах и улучшение домов',
    'hint.build.name': 'Строительство',
    'ui.office.subject.unit': 'объект хозяйства',
    'perk.word_2.effect': 'Одна из составляющих довольства семьи растёт быстрее',
    'catalog.build_menu.units.name': 'Объекты хозяйства',
    'unit.goods_store.blurb': 'Закрытый склад хозяйственного двора: инструмент, промтовары, ткани, железо, керосин. Отсюда снабжают всё хозяйство.',
    'unit.chicken_farm.blurb': 'Недорогая птицеферма без специалистов: яйца идут почти сразу, кормят любым зерном. Даёт ещё мясо и навоз.',
    'unit.road.blurb': 'Связывает объекты хозяйства: без подъезда работы не начнутся. Грунтовка бесплатна, но раскисает; гравий и асфальт держат погоду.',
    'unit.phone_line.blurb': 'Подключает к телефону постройки с электричеством: заявки в район уходят сразу, по утрам приходит сводка погоды.',
    'unit.wooden_house.blurb': 'Основное жильё на всю игру: дом с двором, который можно постепенно улучшать.',
    'unit.village_council.place': 'В любом селении: сельсовет можно построить и в деревнях.',
    'unit.wooden_house.advice': 'Подальше от построек с неприятным запахом; дом у воды — семье выгодно держать уток.',
    'unit.brick_house.advice': 'Подальше от построек с неприятным запахом; дом у воды — семье выгодно держать уток.',
    'unit.barrack.advice': 'Подальше от построек с неприятным запахом.',
    'unit.specialist_dorm.advice': 'Подальше от построек с неприятным запахом.',
    'unit.visitor_dorm.advice': 'Подальше от построек с неприятным запахом.',
    'catalog.build_menu.units_upgrade.blurb': 'Улучшает объект хозяйства до следующей ступени. Набор ступеней у каждого объекта свой.',
    'catalog.build_menu.units_remove.blurb': 'Сносит объект хозяйства за трудодни, материалы не возвращаются. Сначала его нужно опустошить. Размеченная, но не начатая стройка отменяется бесплатно.',
    'catalog.place_tag.module.name': 'Часть объекта хозяйства',
}

NEW = {
    'ui.office.works.repeat_yesterday': 'Повторить вчерашние наряды',
    'ui.office.works.reassign': 'Переставить',
    'ui.office.works.raise_in_queue': 'Поднять в очереди',
    'ui.office.works.released_by_order': 'Освобождён от должности: приказ № {order_number}',
    'ui.office.works.released_by_order_f': 'Освобождена от должности: приказ № {order_number}',
}

SPECIAL = {
    'ui.office.journal.tick': (
        'binding_held', 'office.md §18; string.context: before journal number',
        'The old label describes a raw simulation-step number. Use the proposed time label only with calendar/time presentation, not the raw integer. Boss decides the producer/binding; no new mechanic.'),
    'hint.hint_41.text': (
        'design_formula_confirmation', 'metrics.md §7, lower-threshold law',
        'The current string promises doubled negative influence, while design caps total satisfaction at twice the lowest component below 20. Proposed text follows that formula, not a silent doubling of weights. Boss confirms the formula/source alignment.'),
    'feed.winter_sowing_lost': (
        'producer_confirmation', 'farming.md: October late sowing, November fallow',
        'Emit only after October has ended with sowing incomplete; preserve {place}. A September emission would make even this correct text false. Confirm producer timing before import.'),
    'hint.hint_15.text': (
        'proposal', 'livestock.md: start cattle ladder, straw fallback',
        'Straw is an alternative if clay cannot finish before winter, not permission to overlay already-started clay work. No new trigger or mortality mechanic.'),
    'unit.silage_trench.advice': (
        'proposal', 'livestock.md §11; existing unit place/advice',
        'Remove the unsupported absolute one-time placement claim; preserve the fields-side delivery advice. No free relocation promised.'),
}
OFFICE_TERMS = {'ui.office.works.nomenclature', 'ui.office.outside.requests',
                'ui.office.works.delegation', 'ui.office.works.feed_table',
                'ui.office.own.black_cash'}
STATUS_RU = {
    'proposal': 'На утверждение',
    'design_term_decision': 'Название решает босс',
    'new_key_proposal': 'Новый ключ — на утверждение',
    'binding_held': 'Ждёт согласования отображаемого значения',
    'producer_confirmation': 'Ждёт проверки срока события',
    'design_formula_confirmation': 'Ждёт подтверждения формулы',
}


def snapshot():
    path = ROOT.parent / 'db/strings.db'
    with sqlite3.connect(f'file:{path}?mode=ro', uri=True) as con:
        con.row_factory = sqlite3.Row
        result = con.execute("""SELECT n.key||'.'||s.key AS full_key, t.text,
            s.origin,s.source_table,s.source_key,s.source_column,s.rev,s.approved_rev,
            s.context,s.max_len,s.plural
            FROM string s JOIN namespace n ON n.id=s.namespace_id
            JOIN translation t ON t.string_id=s.id JOIN locale l ON l.id=t.locale_id
            WHERE l.is_source=1 AND s.deprecated=0""")
        return {r['full_key']: dict(r) for r in result}


def main():
    if BASE.with_suffix('.csv').exists():
        with BASE.with_suffix('.csv').open(newline='', encoding='utf-8') as existing:
            if any(r['status'].startswith('approved') or 'verified' in r['status'] for r in csv.DictReader(existing)):
                raise ValueError('Refusing to overwrite approved delivery with a new snapshot')
    source = snapshot()
    records = []
    for key, after in REPLACEMENTS.items():
        r = source[key]
        before = r['text']
        if set(re.findall(r'\{(\w+)\}', before)) != set(re.findall(r'\{(\w+)\}', after)):
            raise ValueError('Changed existing placeholders: ' + key)
        if r['max_len'] is not None and len(after) > r['max_len']:
            raise ValueError('Display limit exceeded: ' + key)
        status, basis, note = SPECIAL.get(key, ('proposal', 'boss orders-demo [11], econ complexity §1/§4', 'Wording only; no mechanical change.'))
        if key in OFFICE_TERMS:
            status = 'design_term_decision'
            basis = 'office.md §8; rules.md §6; livestock.md §11; role-lines.md §7'
            note = 'Boss decides design-term naming; display proposal, not an accepted rename.'
        route = 'design source -> sync' if r['origin'] == 'design' else 'boss shared hand string'
        records.append(dict(key=key, before=before, after=after, status=status,
                            origin=r['origin'], route=route, source_table=r['source_table'] or '',
                            source_key=r['source_key'] or '', source_column=r['source_column'] or '',
                            baseline_rev=r['rev'], placeholders=','.join(sorted(set(re.findall(r'\{(\w+)\}', after)))),
                            basis=basis, note=note))
    for key, after in NEW.items():
        if key in source:
            raise ValueError('Proposed new key already exists: ' + key)
        note = 'Existing action label, not a new action; exact new key/binding requires boss approval.'
        if 'released_by_order' in key:
            note = 'Choose by actual resident gender, never by name. order_number is the existing dismissal-order number; releases take effect next morning. New placeholder registration required.'
        records.append(dict(key=key, before='—', after=after, status='new_key_proposal',
                            origin='new', route='boss new hand string', source_table='',source_key='',source_column='',baseline_rev='',
                            placeholders=','.join(sorted(set(re.findall(r'\{(\w+)\}', after)))),
                            basis='society.md §1 clerk rules, orders.md; existing queue action',note=note))
    with BASE.with_suffix('.csv').open('w', newline='', encoding='utf-8') as out:
        writer = csv.DictWriter(out, fieldnames=list(records[0]), lineterminator='\n')
        writer.writeheader(); writer.writerows(records)
    with BASE.with_suffix('.txt').open('w', encoding='utf-8') as out:
        out.write('Ревизия игровых строк №598 — предложения, 12 октября 2026\n\n')
        out.write('Это таблица для утверждения, не квитанция импорта. Новых квестов, подсказок и механик нет.\n')
        out.write('Ключ | Было | Предложено | Статус\n')
        for r in records:
            values = [r['key'], r['before'], r['after'], STATUS_RU[r['status']]]
            out.write(' | '.join(str(v).replace('|', '\\|') for v in values) + '\n')
        out.write('\n«Партия» в поставках поросят и птицы сохранена: это партия товара, не игровая сессия.\n')
        out.write('«Чёрная касса» не отсутствует в дизайне: это раздел поздней теневой линии, скрытый до её открытия. Предложено более прямое название; доступность не меняется.\n')
        out.write('Подпись «Время» требует календарного значения вместо сырого номера шага. Сообщение о потерянном севе — только после октября. Эти привязки подтверждает босс.\n')
    print(json.dumps({'rows': len(records), 'existing': len(REPLACEMENTS), 'new': len(NEW),
                      'shared_writes': 0, 'own_story_writes': 0}, ensure_ascii=False))


if __name__ == '__main__':
    main()

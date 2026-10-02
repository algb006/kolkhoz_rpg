#!/usr/bin/env python3
"""Prepare only the promoted avatar's corrected portrait thought as draft rev3."""

import sqlite3

from office_intro_lines import ROOT, SOURCE, corpus

KEY = 'scene.office_intro.portrait.promoted'
OLD_TEXT = 'В обкоме висел другой портрет. Здесь всё не так... Куда же я попал?'
TEXT = 'Генсека не узнаю. Уж его-то портрет я знаю наизусть... Куда же я попал?'
MEANING = ('Председатель не узнаёт лицо генсека, чей портрет хорошо помнит по '
           'аппаратной работе; это вызывает сомнение, куда привела его дорога.')
INTENT = ('Передать недоумение человека аппарата и уверенность в собственной '
          'памяти, не противопоставлять учреждения и не объяснять переход.')
KEEP = ('Правка по замечанию человека: boss-rpg-office-portrait-promoted-logic-error-'
        '2026-10-02 [1]; кандидат показан в [3]. У генсека одно лицо независимо '
        'от учреждения. Сохранить личный опыт Выдвиженца, вопрос о собственном '
        'положении, независимость от порядка кликов; без имён, портала и новых '
        'фактов. Остальные семь портретных мыслей, бумаги и часы не менять. '
        'Принятый исходник rev2 не заменять; rev3 требует отдельного утверждения '
        'и совпадающего импорта до TTS тем же голосом Charon.')


def apply_revision(con):
    """One-row transaction; no approvals or voice changes are inferred."""
    current = con.execute('SELECT text,rev,source_ref,meaning,intent,keep FROM line '
                          'WHERE key=?', (KEY,)).fetchone()
    if current == (TEXT, 3, SOURCE, MEANING, INTENT, KEEP):
        return 0
    if current is None or current[:3] != (OLD_TEXT, 2, SOURCE):
        raise ValueError('Unexpected portrait source; do not overwrite: ' + KEY)
    before = con.execute('SELECT * FROM line WHERE key<>? ORDER BY key', (KEY,)).fetchall()
    takes = con.execute('SELECT * FROM voice_take ORDER BY key').fetchall()
    con.execute('UPDATE line SET text=?,meaning=?,intent=?,keep=?,approved_rev=NULL '
                'WHERE key=?', (TEXT, MEANING, INTENT, KEEP, KEY))
    actual = con.execute('SELECT text,rev,approved_rev FROM line WHERE key=?', (KEY,)).fetchone()
    if actual != (TEXT, 3, None):
        raise ValueError('Expected an unapproved revision 3')
    if before != con.execute('SELECT * FROM line WHERE key<>? ORDER BY key', (KEY,)).fetchall():
        raise ValueError('Another line changed')
    if takes != con.execute('SELECT * FROM voice_take ORDER BY key').fetchall():
        raise ValueError('Historical voice takes changed')
    if con.execute('PRAGMA foreign_key_check').fetchall():
        raise ValueError('Story foreign-key violation')
    return 1


def main():
    if corpus()['portrait', 'promoted'] != TEXT:
        raise ValueError('Markdown/source disagreement')
    with sqlite3.connect((ROOT / 'db/story.db').resolve().as_uri() + '?mode=rw', uri=True) as con:
        con.execute('PRAGMA foreign_keys=ON')
        changed = apply_revision(con)
    print(f'Выдвиженец, портрет: подготовлена rev3; изменённых строк {changed}; API 0')


if __name__ == '__main__':
    main()

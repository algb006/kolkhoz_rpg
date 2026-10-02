#!/usr/bin/env python3
"""Apply the eight human-selected portrait alternatives as revision 2."""

import sqlite3

from office_intro_lines import AVATARS, ROOT, SOURCE, corpus

PREFIX = 'scene.office_intro.portrait.'


def main():
    texts = corpus()
    con = sqlite3.connect((ROOT / 'db/story.db').resolve().as_uri() + '?mode=rw', uri=True)
    con.execute('PRAGMA foreign_keys=ON')
    try:
        with con:
            before = con.execute('SELECT * FROM line WHERE key NOT LIKE ? ORDER BY key',
                                 (PREFIX + '%',)).fetchall()
            for avatar in AVATARS:
                key = PREFIX + avatar
                text = texts['portrait', avatar]
                current = con.execute('SELECT text,rev,source_ref FROM line WHERE key=?',
                                      (key,)).fetchone()
                if current is None or current[1] not in (1, 2) or current[2] != SOURCE:
                    raise RuntimeError('Unexpected portrait source: ' + key)
                if current[1] == 2:
                    if current[0] != text:
                        raise RuntimeError('Refusing to overwrite a different revision: ' + key)
                    approved = con.execute('SELECT approved_rev FROM line WHERE key=?', (key,)).fetchone()[0]
                    if approved != 2:
                        raise RuntimeError('Existing revision needs an explicit approval audit: ' + key)
                    continue
                meaning = 'Незнакомый государственный портрет заставляет председателя заподозрить, что дорога привела его не в привычную страну; причины перехода ему неизвестны.'
                intent = 'Выразить личное недоумение языком и манерой выбранного аватара, не начать расследование.'
                keep = 'Вариант А выбран человеком 2 октября 2026: тред портрета [4], подтверждение карты [15]. Сохранить пол, манеру, вопрос о собственном положении; без слова «портал», новых имён и объяснения тумана. Порядок кликов свободный, приказ старого мира не меняется.'
                con.execute('UPDATE line SET text=?,meaning=?,intent=?,keep=? WHERE key=?',
                            (text, meaning, intent, keep, key))
                rev = con.execute('SELECT rev FROM line WHERE key=?', (key,)).fetchone()[0]
                if rev != 2:
                    raise RuntimeError('Portrait revision did not become 2: ' + key)
                con.execute('UPDATE line SET approved_rev=? WHERE key=?', (rev, key))
            after = con.execute('SELECT * FROM line WHERE key NOT LIKE ? ORDER BY key',
                                (PREFIX + '%',)).fetchall()
            if before != after:
                raise RuntimeError('Rows outside the eight portrait replacements changed')
            if con.execute('PRAGMA foreign_key_check').fetchall():
                raise RuntimeError('Story database foreign-key violation')
    finally:
        con.close()
    print('8 портретных вариантов А: rev=approved_rev=2; другие строки и звук не менялись')


if __name__ == '__main__':
    main()

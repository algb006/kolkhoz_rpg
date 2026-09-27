#!/usr/bin/env python3
"""Перенос рабочей версии мыслей кабинета в свою сюжетную базу, без TTS.

Повторный запуск проверяет совпадение; существующие строки не перезаписывает.
"""

from pathlib import Path
import re
import sqlite3


ROOT = Path(__file__).resolve().parent.parent
SOURCE = "manual/texts/office-intro-full-corpus.md"
SCENE = "scene.start.office"
AVATARS = (
    "villager", "worker", "student", "ex_chairman", "promoted",
    "old_fighter", "dealer", "acting",
)
ITEMS = (
    "notebooks", "charts", "papers", "door", "wall_map", "posters",
    "journal", "pocketbook", "newspaper", "personal_item", "portrait",
    "calendar", "clock", "stove", "lamp", "window", "drawer",
)
LABELS = {
    "enter": "Первый взгляд на новый кабинет",
    "affairs_notebook": "Автоматическое открытие тетради «Дела»",
    "notebooks": "Тетради людей и работ", "charts": "Графики: план и сдача",
    "papers": "Папка с бумагами", "door": "Дверь кабинета",
    "wall_map": "Карта хозяйства", "posters": "Плакаты",
    "journal": "Журнал", "pocketbook": "Записная книжка",
    "newspaper": "Районная газета", "personal_item": "Личная вещь аватара",
    "portrait": "Незнакомый портрет", "calendar": "Календарь",
    "clock": "Ходики", "stove": "Печь", "lamp": "Лампа",
    "window": "Мутное окно", "drawer": "Запертый ящик стола",
}


def corpus():
    """Строго распознать три вида таблиц, не превращая примеры ключей в строки."""
    result = {}
    avatar = None
    section = ""
    for raw in (ROOT / SOURCE).read_text(encoding="utf-8").splitlines():
        if raw.startswith("## "):
            section = raw
            match = re.search(r"— `([a-z_]+)`$", raw)
            avatar = match.group(1) if match and match.group(1) in AVATARS else None
        if section == "## Первая мысль" and raw.startswith("> "):
            for selected in AVATARS:
                result[("enter", selected)] = raw[2:].strip()
        if not raw.startswith("| `"):
            continue
        cells = [cell.strip() for cell in raw.strip("|").split("|")]
        if len(cells) == 3 and "Автоматически открылись" in section:
            selected = cells[0].strip("`")
            if selected not in AVATARS:
                raise ValueError(f"Неизвестный аватар: {selected}")
            assert cells[1] == f"`office_intro.affairs_notebook.{selected}`"
            result[("affairs_notebook", selected)] = cells[2]
        elif avatar and len(cells) == 2:
            item = cells[0].strip("`")
            if item not in ITEMS:
                raise ValueError(f"Неизвестный предмет: {item}")
            if (item, avatar) in result:
                raise ValueError(f"Дубль: {item}.{avatar}")
            result[(item, avatar)] = cells[1]
    expected = {(item, selected) for item in ("enter", "affairs_notebook", *ITEMS)
                for selected in AVATARS}
    if set(result) != expected or len(result) != 152:
        raise ValueError(f"Неполный корпус: {len(result)}; отсутствуют {expected-set(result)}")
    return result


def main():
    texts = corpus()
    with sqlite3.connect(ROOT / "db/story.db") as con:
        con.execute("PRAGMA foreign_keys=ON")
        existing = con.execute(
            "SELECT key,text,approved_rev FROM line WHERE scene_key=?", (SCENE,)
        ).fetchall()
        expected = {f"scene.office_intro.{item}.{avatar}": text
                    for (item, avatar), text in texts.items()}
        if existing:
            if {key: text for key, text, _ in existing} != expected:
                raise ValueError("Существующий корпус отличается; автоматическая перезапись запрещена")
            if any(approved is not None for _, _, approved in existing):
                raise ValueError("Есть approved_rev: рабочий пакет должен оставаться черновиком")
            print("152 строки уже есть и дословно совпадают; изменений нет")
            return
        con.execute(
            "INSERT INTO scene_script(scene_key,source_ref,status,note,sort) VALUES(?,?,?,?,?)",
            (SCENE, SOURCE, "draft", "Рабочая версия: человек посмотрел, сначала показ в кабинете. "
             "Ход 22 от 27 сентября 2026 запрещает TTS, включая пробы.", 11),
        )
        con.execute(
            "INSERT INTO cast_slot(scene_key,key,title,binding_kind,gender_binding,age_binding,"
            "social_status,relation_note,address_rule,note,sort) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (SCENE, "chairman", "Выбранный председатель", "chairman", "chairman_avatar",
             "Возраст задан выбранным аватаром.", "Статус и опыт заданы выбранным аватаром.",
             "Мысль вслух; собеседника нет.", "Нового адресата нет; вступительное «давай» — слова человека.",
             "Семь мужских вариантов и женский acting; чужой вариант не подставлять.", 10),
        )
        for ai, avatar in enumerate(AVATARS):
            for ii, item in enumerate(("enter", *ITEMS, "affairs_notebook")):
                text = texts[item, avatar]
                context = (
                    f"Первое знакомство с кабинетом; выбран avatar.key={avatar}. {LABELS[item]}. "
                    "Председатель сидит, время на паузе. Рабочий текст для показа, без TTS."
                )
                if item == "affairs_notebook":
                    context += " Тетрадь открывается сама с кнопками; дополнительного клика нет."
                meaning = f"Реакция выбранного председателя: {text}"
                intent = "Передать взгляд и характер аватара через конкретную вещь, без нового задания."
                keep = (
                    "Сохранить буквальный смысл и голос аватара; не добавлять объяснение портала, "
                    "видимый мир за мутным стеклом или знание содержимого запертого ящика. "
                    "Независимость от порядка кликов; не объявлять квест выполненным."
                )
                con.execute(
                    "INSERT INTO line(key,scene_key,namespace,kind,speaker_slot,variant_key,"
                    "grammatical_gender,condition_ref,text,context,meaning,intent,keep,source_ref,"
                    "approved_rev,sort) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (f"scene.office_intro.{item}.{avatar}", SCENE, "scene", "narration", "chairman",
                     f"office_intro.{item}", "female" if avatar == "acting" else "male",
                     f"Выбран avatar.key={avatar}; опора office_intro.{item}.", text, context,
                     meaning, intent, keep, SOURCE, None, (ai + 1) * 100 + ii),
                )
        assert not con.execute("PRAGMA foreign_key_check").fetchall()
        actual = dict(con.execute("SELECT full_key,text FROM string_source WHERE scene_key=?", (SCENE,)))
        assert actual == expected
        assert con.execute("SELECT count(*) FROM line WHERE scene_key=? AND approved_rev IS NULL", (SCENE,)).fetchone()[0] == 152
    print("Внесено 152 строки: scene / office_intro.*, approved_rev=NULL; TTS не запускался")


if __name__ == "__main__":
    main()

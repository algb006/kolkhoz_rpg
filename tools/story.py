#!/usr/bin/env python3
"""Управление сюжетной базой RPG-слоя.

    tools/story.py init            собрать db/story.db из schema.sql + data/*.sql
    tools/story.py save            выгрузить базу обратно в db/data/*.sql
    tools/story.py check           проверить внутренние и внешние ссылки
    tools/story.py export          создать человекочитаемый дамп в db/export/
    tools/story.py render          обновить сводные блоки story:* в документах
    tools/story.py sql "SELECT …"  выполнить запрос; design доступна как design
    tools/story.py tables          показать число строк в таблицах и представлениях

Двоичный файл — рабочая форма, а schema.sql и data/*.sql — сливаемая копия в git.
Инструмент использует только стандартную библиотеку Python.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
import sqlite3
import sys


ROOT = Path(__file__).resolve().parent.parent
DB_DIR = ROOT / "db"
DB_PATH = DB_DIR / "story.db"
SCHEMA = DB_DIR / "schema.sql"
DATA_DIR = DB_DIR / "data"
EXPORT_DIR = DB_DIR / "export"
DESIGN_DB = ROOT.parent / "db" / "design.db"
PLACEHOLDER_RE = re.compile(r"\{([a-z][a-z0-9_]*)\}")


def rel(path: Path | str) -> str:
    try:
        return str(Path(path).resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def die(message: str) -> None:
    print(f"story.py: {message}", file=sys.stderr)
    raise SystemExit(1)


def attach_design_readonly(con: sqlite3.Connection) -> None:
    """Подключить чужую базу так, чтобы даже SQL-команда не могла её изменить."""
    uri = DESIGN_DB.resolve().as_uri() + "?mode=ro"
    con.execute("ATTACH DATABASE ? AS design", (uri,))


def connect(*, design: bool = False) -> sqlite3.Connection:
    if not DB_PATH.exists():
        die(f"нет базы {rel(DB_PATH)} — сначала python3 tools/story.py init")
    con = sqlite3.connect(DB_PATH, uri=True)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    if design:
        if not DESIGN_DB.exists():
            die(f"нет внешней базы {DESIGN_DB}")
        attach_design_readonly(con)
    return con


def real_tables(con: sqlite3.Connection) -> list[str]:
    return [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master"
        " WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )]


def views(con: sqlite3.Connection) -> list[str]:
    return [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name"
    )]


def columns(con: sqlite3.Connection, table: str) -> list[str]:
    return [r[1] for r in con.execute(f'PRAGMA table_info("{table}")')]


def order_clause(con: sqlite3.Connection, table: str) -> str:
    info = con.execute(f'PRAGMA table_info("{table}")').fetchall()
    primary = [r[1] for r in sorted(info, key=lambda r: r[5]) if r[5]]
    if primary:
        return ", ".join(f'"{name}"' for name in primary)
    names = {r[1] for r in info}
    if "sort" in names:
        return '"sort"'
    return "rowid"


def sqlquote(value: object) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, bytes):
        return "X'" + value.hex() + "'"
    return "'" + str(value).replace("'", "''") + "'"


def write_if_changed(path: Path, text: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temp, path)
    print(f"  записан {rel(path)}")
    return True


def md_escape(value: object) -> str:
    if value is None:
        return "—"
    text = str(value).replace("\n", "<br>")
    return text.replace("|", "\\|")


def md_table(headers: list[str], rows: list[tuple[object, ...]]) -> str:
    out = ["| " + " | ".join(md_escape(h) for h in headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(md_escape(v) for v in row) + " |" for row in rows]
    return "\n".join(out)


def local_source_path(source_ref: str) -> Path:
    raw = source_ref.split("#", 1)[0]
    if raw.startswith("rpg/"):
        raw = raw[4:]
    return ROOT / raw


# ---------------------------------------------------------------------------
# init / save
# ---------------------------------------------------------------------------


def cmd_init(argv: list[str]) -> int:
    if argv:
        die("init не принимает аргументов")
    if not SCHEMA.exists():
        die(f"нет схемы {rel(SCHEMA)}")

    DB_DIR.mkdir(parents=True, exist_ok=True)
    temp = DB_PATH.with_name(DB_PATH.name + ".tmp")
    if temp.exists():
        temp.unlink()

    con = sqlite3.connect(temp)
    con.row_factory = sqlite3.Row
    try:
        con.executescript(SCHEMA.read_text(encoding="utf-8"))
        con.execute("PRAGMA foreign_keys = OFF")
        loaded = 0
        if DATA_DIR.exists():
            for path in sorted(DATA_DIR.glob("*.sql")):
                con.executescript(path.read_text(encoding="utf-8"))
                loaded += 1
        con.commit()
        broken = con.execute("PRAGMA foreign_key_check").fetchall()
        if broken:
            for row in broken:
                print(f"  БИТАЯ ССЫЛКА: {row[0]} rowid={row[1]} → {row[2]}",
                      file=sys.stderr)
            raise RuntimeError(f"{len(broken)} битых внешних ключей")
        rows = sum(con.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]
                   for table in real_tables(con))
    except Exception:
        con.close()
        if temp.exists():
            temp.unlink()
        raise
    con.close()
    os.replace(temp, DB_PATH)
    print(f"{rel(DB_PATH)}: собрана из схемы и {loaded} файлов данных, {rows} строк")
    return 0


def cmd_save(argv: list[str]) -> int:
    if argv:
        die("save не принимает аргументов")
    con = connect()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    kept: set[str] = set()

    for table in real_tables(con):
        cols = columns(con, table)
        rows = con.execute(
            f'SELECT * FROM "{table}" ORDER BY {order_clause(con, table)}'
        ).fetchall()
        if not rows:
            continue
        name = f"{table}.sql"
        kept.add(name)
        collist = ", ".join(f'"{col}"' for col in cols)
        lines = [
            f"-- {table}: {len(rows)} строк. Файл создаётся tools/story.py save —",
            "-- правится база, не этот дамп. Порядок строк детерминирован.",
            f'DELETE FROM "{table}";',
        ]
        for row in rows:
            values = ", ".join(sqlquote(row[col]) for col in cols)
            lines.append(f'INSERT INTO "{table}" ({collist}) VALUES ({values});')
        write_if_changed(DATA_DIR / name, "\n".join(lines) + "\n")

    for path in sorted(DATA_DIR.glob("*.sql")):
        if path.name not in kept:
            path.unlink()
            print(f"  убран пустой {rel(path)}")
    con.close()
    print(f"{rel(DATA_DIR)}: {len(kept)} таблиц выгружено")
    return 0


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------


def cmd_check(argv: list[str]) -> int:
    if argv:
        die("check не принимает аргументов")
    con = connect()
    hard = 0
    soft = 0

    def bad(message: str) -> None:
        nonlocal hard
        hard += 1
        print(f"  ОШИБКА  {message}")

    def warn(message: str) -> None:
        nonlocal soft
        soft += 1
        print(f"  ВОПРОС  {message}")

    print("SQLite:")
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        bad(f"integrity_check: {integrity}")
    for row in con.execute("PRAGMA foreign_key_check"):
        bad(f"{row[0]} rowid={row[1]} ссылается в никуда на {row[2]}")

    print("Источники:")
    for table, key_col in (("character", "key"), ("arc", "key"),
                           ("story_branch", "key"), ("scene_script", "scene_key"),
                           ("line", "key")):
        for row in con.execute(f'SELECT "{key_col}", source_ref FROM "{table}"'):
            if not local_source_path(row["source_ref"]).is_file():
                bad(f"{table}.{row[key_col]}: нет файла {row['source_ref']}")

    if not DESIGN_DB.exists():
        bad(f"нет внешней базы дизайна {DESIGN_DB}")
    else:
        print("Связь с design.db:")
        attach_design_readonly(con)
        for row in con.execute(
            "SELECT s.scene_key FROM scene_script s"
            " WHERE NOT EXISTS (SELECT 1 FROM design.scene d WHERE d.key=s.scene_key)"
        ):
            bad(f"scene_script.{row['scene_key']}: сцены нет в design.db")
        for row in con.execute(
            "SELECT b.key, b.entry_quest_key FROM story_branch b"
            " WHERE b.entry_quest_key IS NOT NULL"
            "   AND NOT EXISTS (SELECT 1 FROM design.quest q"
            "                   WHERE q.key=b.entry_quest_key)"
        ):
            bad(f"story_branch.{row['key']}: квеста {row['entry_quest_key']} нет в design.db")
        for row in con.execute(
            "SELECT a.key, a.era_from, a.era_to FROM arc a"
            " WHERE (a.era_from IS NOT NULL AND NOT EXISTS"
            "       (SELECT 1 FROM design.era e WHERE e.key=a.era_from))"
            "    OR (a.era_to IS NOT NULL AND NOT EXISTS"
            "       (SELECT 1 FROM design.era e WHERE e.key=a.era_to))"
        ):
            bad(f"arc.{row['key']}: эпоха не существует ({row['era_from']}…{row['era_to']})")
        for row in con.execute(
            "SELECT g.scene_key, g.key FROM choice_group g"
            " WHERE NOT EXISTS (SELECT 1 FROM design.scene d"
            "                   WHERE d.key=g.scene_key AND d.kind='dialogue')"
        ):
            bad(f"{row['scene_key']}.{row['key']}: выбор есть не в dialogue-сцене design.db")

    era_order = {"era_1": 1, "era_2": 2, "era_3": 3}
    for row in con.execute("SELECT key, era_from, era_to FROM arc"):
        if (row["era_from"] and row["era_to"] and
                era_order[row["era_from"]] > era_order[row["era_to"]]):
            bad(f"arc.{row['key']}: конечная эпоха раньше начальной")

    for row in con.execute(
        "SELECT b.key, b.arc_key, p.arc_key AS parent_arc"
        "  FROM story_branch b JOIN story_branch p ON p.key=b.parent_key"
        " WHERE b.arc_key<>p.arc_key"
    ):
        bad(f"story_branch.{row['key']}: родитель принадлежит другой арке")
    parents = {row["key"]: row["parent_key"]
               for row in con.execute("SELECT key, parent_key FROM story_branch")}
    cyclic: set[str] = set()
    for start in parents:
        seen: set[str] = set()
        current: str | None = start
        while current is not None and current in parents:
            if current in seen:
                cyclic.add(start)
                break
            seen.add(current)
            current = parents[current]
    for key in sorted(cyclic):
        bad(f"story_branch.{key}: цикл родителей")

    for row in con.execute(
        "SELECT s.scene_key, s.arc_key, b.arc_key AS branch_arc"
        "  FROM scene_script s JOIN story_branch b ON b.key=s.story_branch_key"
        " WHERE s.arc_key IS NULL OR s.arc_key<>b.arc_key"
    ):
        bad(f"scene_script.{row['scene_key']}: ветвь и арка не совпадают")

    print("Состав сцен:")
    for row in con.execute(
        "SELECT c.scene_key, c.key, c.gender_binding, p.gender, p.kind"
        "  FROM cast_slot c LEFT JOIN character p ON p.key=c.character_key"
        " WHERE c.binding_kind='fixed_character'"
    ):
        expected = "fixed_male" if row["gender"] == "male" else "fixed_female"
        if row["kind"] != "fixed_person":
            bad(f"{row['scene_key']}.{row['key']}: fixed_character связан не с fixed_person")
        if row["gender_binding"] != expected:
            bad(f"{row['scene_key']}.{row['key']}: пол слота {row['gender_binding']},"
                f" персонажа — {row['gender']}")
    for row in con.execute(
        "SELECT scene_key, key, binding_kind, role_ref FROM cast_slot"
        " WHERE binding_kind='role_holder' AND role_ref IS NULL"
    ):
        bad(f"{row['scene_key']}.{row['key']}: сменяемая роль без role_ref")

    print("Реплики:")
    for row in con.execute(
        "SELECT l.key, l.scene_key, l.kind, l.relationship, l.previous_key,"
        "       l.sort, p.scene_key AS previous_scene, p.sort AS previous_sort"
        "  FROM line l LEFT JOIN line p ON p.key=l.previous_key"
    ):
        if row["previous_key"] is not None and row["previous_scene"] != row["scene_key"]:
            bad(f"{row['key']}: соседняя реплика из другой сцены")
        if row["previous_key"] is not None and row["previous_sort"] >= row["sort"]:
            bad(f"{row['key']}: previous_key не предшествует реплике по sort")
        if (row["kind"] in ("dialogue", "choice") and
                not (row["relationship"] or "").strip()):
            bad(f"{row['key']}: не описаны отношения говорящего и адресата")

    for row in con.execute(
        "SELECT g.scene_key, g.key, count(l.key) AS n"
        "  FROM choice_group g LEFT JOIN line l"
        "    ON l.scene_key=g.scene_key AND l.choice_group_key=g.key"
        "   AND l.deprecated=0"
        " GROUP BY g.scene_key, g.key"
    ):
        if not 2 <= row["n"] <= 4:
            bad(f"{row['scene_key']}.{row['key']}: вариантов {row['n']}, требуется 2–4")

    for row in con.execute(
        "SELECT l.key, l.scene_key, l.variant_key, l.grammatical_gender,"
        "       c.gender_binding"
        "  FROM line l LEFT JOIN cast_slot c"
        "    ON c.scene_key=l.scene_key AND c.key=l.speaker_slot"
        " WHERE l.grammatical_gender <> 'neutral' AND l.deprecated=0"
    ):
        if row["gender_binding"] == "fixed_male" and row["grammatical_gender"] != "male":
            bad(f"{row['key']}: женская форма у фиксированного мужчины")
        elif row["gender_binding"] == "fixed_female" and row["grammatical_gender"] != "female":
            bad(f"{row['key']}: мужская форма у фиксированной женщины")
        elif row["gender_binding"] in ("runtime_resident", "chairman_avatar"):
            if not row["variant_key"]:
                bad(f"{row['key']}: родовая форма случайного говорящего без variant_key")

    for row in con.execute(
        "SELECT scene_key, speaker_slot, variant_key,"
        "       group_concat(DISTINCT grammatical_gender) AS forms"
        "  FROM line WHERE variant_key IS NOT NULL AND deprecated=0"
        " GROUP BY scene_key, speaker_slot, variant_key"
    ):
        forms = set(row["forms"].split(","))
        if forms & {"male", "female"} and not {"male", "female"} <= forms:
            bad(f"{row['scene_key']}.{row['variant_key']}: неполная пара пола ({row['forms']})")

    for row in con.execute(
        "SELECT key, rev, approved_rev, context, meaning, intent, keep FROM line"
        " WHERE approved_rev=rev AND deprecated=0"
    ):
        for field in ("context", "meaning", "intent", "keep"):
            if not row[field].strip():
                bad(f"{row['key']}: утверждена без поля {field}")

    for row in con.execute(
        "SELECT s.scene_key FROM scene_script s"
        " WHERE s.status='approved' AND EXISTS"
        "       (SELECT 1 FROM line l WHERE l.scene_key=s.scene_key"
        "        AND l.deprecated=0 AND"
        "        (l.approved_rev IS NULL OR l.approved_rev<l.rev))"
    ):
        bad(f"scene_script.{row['scene_key']}: сцена утверждена, но в ней есть черновики")

    print("Подстановки:")
    declared: dict[str, set[str]] = {}
    for row in con.execute("SELECT line_key, name FROM line_placeholder"):
        declared.setdefault(row["line_key"], set()).add(row["name"])
    for row in con.execute("SELECT key, text FROM line"):
        used = set(PLACEHOLDER_RE.findall(row["text"]))
        known = declared.get(row["key"], set())
        for name in sorted(used - known):
            bad(f"{row['key']}: подстановка {{{name}}} не объявлена")
        for name in sorted(known - used):
            bad(f"{row['key']}: объявлена {{{name}}}, но в тексте её нет")

    for row in con.execute(
        "SELECT s.scene_key FROM scene_script s"
        " WHERE s.status <> 'retired'"
        "   AND NOT EXISTS (SELECT 1 FROM line l"
        "                   WHERE l.scene_key=s.scene_key AND l.deprecated=0)"
    ):
        warn(f"{row['scene_key']}: заведена без реплик")

    print()
    if hard:
        print(f"ОШИБОК: {hard}, вопросов к автору: {soft}")
    else:
        print(f"Ошибок нет. Вопросов к автору: {soft}")
    con.close()
    return 1 if hard else 0


# ---------------------------------------------------------------------------
# export / render
# ---------------------------------------------------------------------------


def cmd_export(argv: list[str]) -> int:
    if argv:
        die("export не принимает аргументов")
    con = connect()
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    wanted: set[str] = {"README.md"}
    index = [
        "# Дамп сюжетной базы",
        "",
        "> Создаётся `python3 tools/story.py export`; руками не правится и в git не лежит.",
        "> Первоисточник — `db/story.db`, воспроизводимая копия — `schema.sql` и `data/*.sql`.",
        "",
        "| Таблица или представление | Строк |",
        "|---|---|",
    ]

    for name in real_tables(con) + views(con):
        rows = con.execute(f'SELECT * FROM "{name}"').fetchall()
        headers = [d[0] for d in con.execute(f'SELECT * FROM "{name}" LIMIT 0').description]
        kind = "представление" if name in views(con) else "таблица"
        body = [f"# `{name}` — {kind}", "", f"Строк: **{len(rows)}**.", ""]
        body.append(md_table(headers, [tuple(row) for row in rows]) if rows else "_Пусто._")
        body.append("")
        write_if_changed(EXPORT_DIR / f"{name}.md", "\n".join(body))
        wanted.add(f"{name}.md")
        index.append(f"| [`{name}`]({name}.md) | {len(rows)} |")

    write_if_changed(EXPORT_DIR / "README.md", "\n".join(index) + "\n")
    for path in EXPORT_DIR.glob("*.md"):
        if path.name not in wanted:
            path.unlink()
            print(f"  убран сирота {rel(path)}")
    con.close()
    print(f"{rel(EXPORT_DIR)}: {len(wanted)} файлов")
    return 0


OPEN_MARKER = re.compile(r"^<!--\s*story:(\w+)\s*-->\s*$")
CLOSE_MARKER = re.compile(r"^<!--\s*/story\s*-->\s*$")


def summary_coverage(con: sqlite3.Connection) -> str:
    rows = [(f"`{r['scene_key']}`", r["lines"], r["drafts"], r["approved"])
            for r in con.execute("SELECT * FROM scene_coverage")]
    return md_table(["Сцена", "Реплик", "Черновиков", "Утверждено"], rows)


def summary_characters(con: sqlite3.Connection) -> str:
    rows = [(f"`{r['key']}`", r["display_name"] or r["title"], r["kind"],
             r["gender"], r["age_profile"], r["social_status"], r["status"])
            for r in con.execute("SELECT * FROM character ORDER BY sort, key")]
    return md_table(["Ключ", "Кто", "Вид", "Пол", "Возраст", "Статус в мире",
                     "Редакция"], rows)


def summary_arcs(con: sqlite3.Connection) -> str:
    rows = [(f"`{r['key']}`", r["title"], r["era_from"] or "—", r["era_to"] or "—",
             r["role_focus"], r["status"])
            for r in con.execute("SELECT * FROM arc ORDER BY sort, key")]
    if not rows:
        return "_Арки ещё не перенесены из Markdown._"
    return md_table(["Ключ", "Арка", "От", "До", "Ролевой фокус", "Редакция"], rows)


SUMMARIES = {
    "coverage": summary_coverage,
    "characters": summary_characters,
    "arcs": summary_arcs,
}


def cmd_render(argv: list[str]) -> int:
    if argv:
        die("render не принимает аргументов")
    con = connect()
    candidates = [DB_DIR / "README.md"]
    candidates += sorted((ROOT / "manual").rglob("*.md"))
    touched = 0
    blocks = 0
    unknown: list[tuple[Path, str]] = []

    for path in candidates:
        text = path.read_text(encoding="utf-8")
        if "<!-- story:" not in text:
            continue
        lines = text.split("\n")
        out: list[str] = []
        index = 0
        fenced = False
        while index < len(lines):
            if lines[index].lstrip().startswith("```"):
                fenced = not fenced
            match = None if fenced else OPEN_MARKER.match(lines[index])
            if not match:
                out.append(lines[index])
                index += 1
                continue
            kind = match.group(1)
            end = index + 1
            while end < len(lines) and not CLOSE_MARKER.match(lines[end]):
                if OPEN_MARKER.match(lines[end]):
                    die(f"{rel(path)}: блок story:{kind} не закрыт перед строкой {end + 1}")
                end += 1
            if end >= len(lines):
                die(f"{rel(path)}: блок story:{kind} не закрыт")
            out.append(lines[index])
            if kind not in SUMMARIES:
                unknown.append((path, kind))
                out.extend(lines[index + 1:end])
            else:
                out.extend(SUMMARIES[kind](con).split("\n"))
                blocks += 1
            out.append(lines[end])
            index = end + 1
        new = "\n".join(out)
        if new != text:
            write_if_changed(path, new)
            touched += 1

    for path, kind in unknown:
        print(f"  НЕИЗВЕСТНАЯ СВОДКА  {rel(path)}: story:{kind}")
    con.close()
    print(f"вписано блоков: {blocks}, изменено документов: {touched}")
    return 1 if unknown else 0


# ---------------------------------------------------------------------------
# inspection
# ---------------------------------------------------------------------------


def cmd_sql(argv: list[str]) -> int:
    if len(argv) != 1:
        die('нужен один запрос: python3 tools/story.py sql "SELECT …"')
    con = connect(design=DESIGN_DB.exists())
    try:
        cur = con.execute(argv[0])
    except sqlite3.Error as exc:
        con.close()
        die(str(exc))
    if cur.description is None:
        con.commit()
        print(f"строк затронуто: {cur.rowcount}")
    else:
        headers = [d[0] for d in cur.description]
        print(md_table(headers, [tuple(row) for row in cur.fetchall()]))
    con.close()
    return 0


def cmd_tables(argv: list[str]) -> int:
    if argv:
        die("tables не принимает аргументов")
    con = connect()
    rows = [(name, con.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0])
            for name in real_tables(con)]
    rows += [(f"{name} (представление)",
              con.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0])
             for name in views(con)]
    print(md_table(["Таблица", "Строк"], rows))
    con.close()
    return 0


COMMANDS = {
    "init": cmd_init,
    "save": cmd_save,
    "check": cmd_check,
    "export": cmd_export,
    "render": cmd_render,
    "sql": cmd_sql,
    "tables": cmd_tables,
}


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in COMMANDS:
        names = " | ".join(COMMANDS)
        print(f"использование: python3 tools/story.py <{names}>", file=sys.stderr)
        return 2
    return COMMANDS[argv[0]](argv[1:])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

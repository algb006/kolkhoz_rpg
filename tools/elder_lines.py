#!/usr/bin/env python3
"""Load authored Ryabinin scene lines into the RPG-owned story database.

This writes only rpg/db/story.db. Boss-owned design/strings databases are read
by story.py during later validation and are never modified here.
"""

from pathlib import Path
import sqlite3


ROOT = Path(__file__).resolve().parent.parent
SOURCE = "manual/characters/former-elder.md"
NEW = "manual/texts/elder-explains-clarity.md"
SCENES = (
    "scene.elder.first_meeting",
    "scene.elder.warnings",
    "scene.elder.affected_resident_question",
    "scene.elder.own_name",
    "scene.elder.restore_talk",
    "scene.elder.last_advice",
)


def semantic_context(scene, kind, condition):
    situation = {
        "scene.elder.first_meeting": "Председатель уже снял резервное поле и решает, как размечать село.",
        "scene.elder.warnings": "Рябинин замечает исправимую недоработку до потери; он говорит лишь после знакомства.",
        "scene.elder.affected_resident_question": "Житель уже поселился в построенном жилье на принятом контуре Рябинина.",
        "scene.elder.own_name": "Председатель сослался на Рябинина перед жителем и переложил на него ответственность за своё решение.",
        "scene.elder.restore_talk": "Председатель сам нашёл Рябинина на работе после испорченных отношений.",
        "scene.elder.last_advice": "В хозяйстве работают агроном, зоотехник и счетовод; роль старого советчика окончена.",
    }[scene]
    if condition:
        situation += f" Вариант допустим только при факте: {condition}"
    purpose = (
        "Дать игроку настоящую альтернативу без скрытого штрафа."
        if kind == "choice" else
        "Предупредить о видимом и ещё исправимом риске."
        if scene == "scene.elder.warnings" else
        "Показать размен места, не присвоив решение председателя."
        if scene == "scene.elder.first_meeting" else
        "Назвать ответственность каждого участника без насмешки и наказания за совет."
        if scene in {"scene.elder.own_name", "scene.elder.restore_talk",
                     "scene.elder.affected_resident_question"} else
        "Передать право более точного совета работающим специалистам."
    )
    return situation, purpose


def add_line(con, scene, suffix, speaker, text, sort, *, kind="dialogue",
             group=None, condition=None, source=SOURCE, addressee=None,
             variant=None, meaning=None, intent=None, keep=None):
    key = f"{scene}.{suffix}"
    situation, purpose = semantic_context(scene, kind, condition)
    con.execute(
        "INSERT INTO line(key,scene_key,namespace,kind,speaker_slot,addressee_slot,"
        "relationship,choice_group_key,variant_key,condition_ref,text,context,"
        "meaning,intent,keep,source_ref,sort) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (key, scene, "scene", kind, speaker, addressee,
         "Председатель и Рябинин: рабочее уважительное «вы», совет не приказ."
         if speaker in {"elder", "chairman"} else
         "Житель спрашивает о собственном жилье без знания тайных решений.",
         group, variant, condition, text,
         "Фактическое место работы Рябинина; одежда и инструмент берутся из партии."
         if "first_meeting" in scene else
         "Сцена произносится только по зарегистрированному поводу и фактам партии.",
         meaning or situation,
         intent or purpose,
         keep or "Сохранить уважительное «вы», смысл и отсутствие приказа; не добавлять новых условий.",
         source, sort),
    )
    return key


def setup(con):
    con.execute(
        "INSERT INTO character(key,kind,title,display_name,gender,age_profile,"
        "social_status,address_rule,voice,source_ref,status,sort)"
        " VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
        ("fedot_ryabinin", "fixed_person", "Федот Кузьмич Рябинин",
         "Федот Кузьмич Рябинин", "male", "Пожилой; точный возраст не назначен.",
         "Бывший староста, ныне рядовой работник колхоза.",
         "С председателем на «вы»; «старостой» его не называют.",
         "Место и срок прежде вывода; коротко, спокойно, без загадок и приказов.",
         SOURCE, "review", 20),
    )
    for i, scene in enumerate(SCENES):
        con.execute(
            "INSERT INTO scene_script(scene_key,source_ref,status,note,sort)"
            " VALUES(?,?,?,?,?)",
            (scene, SOURCE, "review",
             "Авторские строки; регистрация и триггеры принадлежат design.db."
             if scene != "scene.elder.warnings" else
             "Новые предупреждения ждут раздельных фактических поводов от boss/core;"
             " общим флагом их не показывать.", 1200 + i),
        )
        con.execute(
            "INSERT INTO cast_slot(scene_key,key,title,binding_kind,gender_binding,"
            "age_binding,social_status,relation_note,address_rule,sort)"
            " VALUES(?,?,?,?,?,?,?,?,?,?)",
            (scene, "chairman", "Председатель", "chairman", "chairman_avatar",
             "Возраст выбранного аватара.", "Председатель колхоза.",
             "Имеет власть, но не перекладывает решение на советчика.",
             "К Рябинину уважительное «вы», без уменьшительных имен.", 1),
        )
        if scene != "scene.elder.affected_resident_question":
            con.execute(
                "INSERT INTO cast_slot(scene_key,key,title,binding_kind,character_key,"
                "gender_binding,age_binding,social_status,relation_note,address_rule,sort)"
                " VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (scene, "elder", "Федот Кузьмич Рябинин", "fixed_character",
                 "fedot_ryabinin", "fixed_male", "Пожилой; точный возраст не назначен.",
                 "Рядовой работник, прежде староста.",
                 "Советует, не распоряжается; не приходит в кабинет.",
                 "К председателю уважительное «вы».", 2),
            )
    for scene in ("scene.elder.first_meeting", "scene.elder.affected_resident_question",
                  "scene.elder.restore_talk"):
        con.execute(
            "INSERT INTO choice_group(scene_key,key,title,sort) VALUES(?,?,?,?)",
            (scene, "answer", "Ответ председателя", 1),
        )
    scene = "scene.elder.affected_resident_question"
    con.execute(
        "INSERT INTO cast_slot(scene_key,key,title,binding_kind,gender_binding,"
        "age_binding,social_status,relation_note,address_rule,sort)"
        " VALUES(?,?,?,?,?,?,?,?,?,?)",
        (scene, "resident", "Поселившийся житель", "procedural_resident",
         "runtime_resident", "Возраст из партии.", "Член заселившейся семьи.",
         "Спрашивает о месте собственного жилья, не владеет скрытыми фактами.",
         "Без предположения о поле и родстве.", 3),
    )


def first_meeting(con):
    s = "scene.elder.first_meeting"
    a = lambda key, speaker, text, sort, **kw: add_line(con, s, key, speaker, text, sort, **kw)
    a("opening.chairman", "chairman", "Федот Кузьмич?", 10)
    a("opening.elder", "elder", "Кузьмич — верно. Староста — уже нет. Вы по разметке пришли?", 20)
    a("field.chairman", "chairman", "Поле снято. Теперь надо решить, где что ставить.", 30)
    a("offer.elder", "elder", "Решить — вам. Я могу показать, где поставил бы сам, и почему. Не подойдёт место — передвиньте.", 40)
    a("answer.see", "chairman", "Покажите весь порядок.", 50, kind="choice", group="answer")
    a("answer.own", "chairman", "Размечу по-своему.", 51, kind="choice", group="answer")
    a("reply.see", "elder", "Покажу по одному месту. Так видно, где мой совет кончается и ваше решение начинается.", 60, condition="Выбран ответ answer.see.")
    a("reply.own", "elder", "На то и председатель. Если передумаете — я на работе, не в конторе.", 61, condition="Выбран ответ answer.own.")
    a("offer.student", "elder", "На бумаге село начинается с середины листа. Здесь оно начинается с дороги. Давайте от неё и пойдём.", 70, condition="Аватар student; председатель начинает с общей схемы.", variant="offer_by_avatar")
    a("offer.villager", "elder", "Дороги вы знаете. Я покажу только, где прежний порядок уже не годится.", 71, condition="Аватар villager.", variant="offer_by_avatar")
    a("whistle.elder", "elder", "Свисток далеко слышно. Кого зовёте — не слышно вовсе. За руками можно свистнуть. За разговором лучше подойти.", 80, condition="Председатель воспользовался свистком и затем сам пришёл к Рябинину.")
    advice = (
        ("housing", "Шесть бараков я прижал к отводу от старой дороги. Дом в поле просторнее только пока к нему не повезли первую доску."),
        ("well", "Колодец — между дворами. Крайним всё равно ходить дальше, зато крайних не будет с одной стороны."),
        ("store", "За едой ходят по расписанию желудка. Склад поэтому ближе. В правление — когда есть дело; оно ещё шаг потерпит."),
        ("farmyard", "Хозяйственный двор рядом со складом. Не для красоты — чтобы верёвка, лопата и пустой мешок не путешествовали через всё село по отдельности."),
        ("collective_yard", "Колхозный двор хочется поставить у домов. Утром оттуда лошадь пойдёт не домой, а в поле. Я ставлю между жильём и пашней: человеку чуть дальше, тяглу весь сезон короче."),
        ("livestock_yard", "Скотный двор далеко — не по моей любви к дороге. Поставите ближе, село станет компактнее и будет круглый год это нюхать. Я выбираю дорогу. Вы можете выбрать запах."),
        ("manure", "Навозную кучу туда же. Разнести источник и его запах по двум местам — значит получить две дальние дороги вместо одной."),
        ("access", "Колышки без дороги простоят. Стройка — нет. Сначала оставьте повозке путь, потом ставьте на нём людей с брёвнами."),
    )
    for i, (key, text) in enumerate(advice):
        a(f"layout.{key}", "elder", text, 100 + i,
          condition=f"Согласие посмотреть предложенную разметку; показан контур {key}; фактическое место подходит строке.")
    a("outcome.most", "elder", "Теперь это ваши колышки. Моими они были, пока лежали на схеме.", 200, condition="Принята большая часть предложенной разметки.")
    a("outcome.moved", "elder", "Так и надо. Совет, который нельзя подвинуть, уже стал приказом.", 201, condition="Многое передвинуто.")
    a("outcome.rejected", "elder", "Своими колышками легче отвечать. Порядок вижу — мешать не стану.", 202, condition="Предложение целиком отвергнуто, собственная разметка завершена.")


def warnings(con):
    s = "scene.elder.warnings"
    a = lambda key, text, sort, **kw: add_line(con, s, key, "elder", text, sort, **kw)
    a("work_due", "Срок поджимает: {work_name}. А {place_name} ещё пустует. Дальше погода будет решать вместо вас.", 10,
      condition="Видимая работа ещё не началась перед её сроком; подстановки заполнены из партии.")
    con.execute("INSERT INTO line_placeholder(line_key,name,kind,meaning) VALUES(?,?,?,?)",
                (f"{s}.work_due", "work_name", "text", "Название работы или культуры в именительном падеже."))
    con.execute("INSERT INTO line_placeholder(line_key,name,kind,meaning) VALUES(?,?,?,?)",
                (f"{s}.work_due", "place_name", "text", "Место работы в именительном падеже: поле, луг, площадка."))
    a("hay_before_snow", "Трава на корню — не зимний запас. Скосите до снега: сено и в кучах сохранится.", 20,
      condition="Нескошенная доля луга за месяц до первого устойчивого снега по климату; порог доли — STUB core.")
    a("no_access", "Стены тут поместятся. Теперь покажите, откуда к ним придёт первая повозка.", 30,
      condition="Размеченная стройка без подъезда, исправление ещё не начато.")
    new_lines = (
        ("sowing_window", "Срок сева подходит, а поле пустое. Проверьте наряд и семена: поздний сев даст меньше урожая."),
        ("next_seed", "Для будущего сева запаса не хватает. Посмотрите семенной фонд и поля на будущий год: что сеять, ещё можно поправить."),
        ("late_harvest", "Урожай созрел, а убрать ещё не успели. До конца уборки мало времени; посмотрите, хватает ли людей и подвод."),
        ("zyab", "Стерню сейчас пашут под весенний сев. Это зябь: весной останется забороновать поле и сеять."),
    )
    for i, (key, text) in enumerate(new_lines):
        a(key, text, 40 + i, source=NEW,
          condition=f"Только отдельный фактический повод warning.{key}; общий флаг недостаточен.")


def resident_and_name(con):
    s = "scene.elder.affected_resident_question"
    a = lambda key, speaker, text, sort, **kw: add_line(con, s, key, speaker, text, sort, **kw)
    a("opening.resident", "resident", "Теперь мы тут живём. Почему жильё поставили именно здесь?", 10)
    a("answer.own", "chairman", "Это моё решение. Спрашивайте с меня.", 20, kind="choice", group="answer")
    a("answer.road", "chairman", "Здесь дорога рядом. Дальше строить дороже.", 21, kind="choice", group="answer")
    a("answer.cite_elder", "chairman", "Федот Кузьмич это место показал.", 22, kind="choice", group="answer")

    s = "scene.elder.own_name"
    a = lambda key, speaker, text, sort: add_line(con, s, key, speaker, text, sort)
    a("opening.elder", "elder", "Совет я давал вам. Теперь моё имя ходит по дворам и отвечает без меня. Так больше не пойдёт.", 10)
    a("question.chairman", "chairman", "Что вы хотите услышать?", 20)
    a("answer.elder", "elder", "Не от меня зависит. Хотите снова спрашивать — сначала сами скажите, чьё было решение.", 30)

    s = "scene.elder.restore_talk"
    a = lambda key, speaker, text, sort, **kw: add_line(con, s, key, speaker, text, sort, **kw)
    a("answer.own", "chairman", "Вместо ответа прозвучало ваше имя. Решение было моё.", 10, kind="choice", group="answer")
    a("answer.deflect", "chairman", "Людям нужен был ответ.", 11, kind="choice", group="answer")
    a("reply.own", "elder", "Теперь верно сказано. Когда понадобится — спросите.", 20, condition="Выбран answer.own; обычные отношения не закрывают разговор.")
    a("reply.deflect", "elder", "Вот и отвечайте своим именем. Моё оставьте мне.", 21, condition="Выбран answer.deflect.")

    s = "scene.elder.last_advice"
    add_line(con, s, "handoff", "elder",
             "Что знал — говорил. Теперь у вас есть кого спрашивать точнее. Значит, не зря расчерчивали.", 10,
             condition="В хозяйстве одновременно работают агроном, зоотехник и счетовод.")


def main():
    with sqlite3.connect(ROOT / "db/story.db") as con:
        con.execute("PRAGMA foreign_keys=ON")
        existing = con.execute("SELECT count(*) FROM scene_script WHERE scene_key LIKE 'scene.elder.%'").fetchone()[0]
        if existing:
            count = con.execute("SELECT count(*) FROM line WHERE scene_key LIKE 'scene.elder.%'").fetchone()[0]
            if existing != len(SCENES) or count != 41:
                raise SystemExit("Корпус Рябинина отличается: автоматическая перезапись запрещена")
            key = "scene.elder.warnings.sowing_window"
            old = "Срок сева подходит, а на поле ещё не вышли. Проверьте наряд и семена, пока опоздание не обошлось урожаем."
            new = "Срок сева подходит, а поле пустое. Проверьте наряд и семена: поздний сев даст меньше урожая."
            current = con.execute("SELECT text FROM line WHERE key=?", (key,)).fetchone()
            if current is None or current[0] not in (old, new):
                raise SystemExit("Предупреждение о севе отредактировано вручную; не перезаписываю")
            if current[0] == old:
                con.execute("UPDATE line SET text=? WHERE key=?", (new, key))
            for key, scene, kind, condition in con.execute(
                "SELECT key,scene_key,kind,condition_ref FROM line WHERE scene_key LIKE 'scene.elder.%'"):
                meaning, intent = semantic_context(scene, kind, condition)
                con.execute("UPDATE line SET meaning=?,intent=? WHERE key=?", (meaning, intent, key))
            print("41 строка Рябинина на месте; обновлены только поля для переводчика")
            return
        setup(con)
        first_meeting(con)
        warnings(con)
        resident_and_name(con)
        broken = con.execute("PRAGMA foreign_key_check").fetchall()
        if broken:
            raise ValueError(f"Битые внешние ключи: {broken}")
        total = con.execute("SELECT count(*) FROM line WHERE scene_key LIKE 'scene.elder.%'").fetchone()[0]
    print(f"Шесть сцен Рябинина, {total} строк; условия новых предупреждений — черновик")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Load authored elder scene lines into the RPG-owned story database.

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
WARNING_FACTS = {
    "sowing_window": "fact:elder_warn_sowing_window",
    "next_seed": "fact:elder_warn_next_seed",
    "late_harvest": "fact:elder_warn_late_harvest",
    "hay_before_snow": "fact:elder_warn_hay_before_snow",
    "zyab": "fact:elder_warn_zyab_started",
}
WARNING_MEANINGS = {
    "fact:elder_warn_sowing_window": "Окно сева назначенной культуры близко к концу, а работу на поле ещё не начали; поздний сев снизит урожай.",
    "fact:elder_warn_next_seed": "Разложены поля следующего года, но посевного запаса на эту раскладку не хватает; её ещё можно изменить.",
    "fact:elder_warn_late_harvest": "Созревшая культура остаётся в поле перед концом уборки; люди и подводы ещё могут успеть.",
    "fact:elder_warn_hay_before_snow": "На лугу осталась нескошенная трава за месяц до устойчивого снега; уже скошенные кучи сена остаются запасом.",
    "fact:elder_warn_zyab_started": "Осенью после уборки свободные руки действительно пашут стерню под яровые будущего года; игрок не включает зябь кнопкой.",
}


def semantic_context(scene, kind, condition):
    situation = {
        "scene.elder.first_meeting": "Председатель уже снял резервное поле и решает, как размечать село.",
        "scene.elder.warnings": "староста замечает исправимую недоработку до потери; он говорит лишь после знакомства.",
        "scene.elder.affected_resident_question": "Житель уже поселился в построенном жилье на принятом контуре старосты.",
        "scene.elder.own_name": "Председатель сослался на старосту перед жителем и переложил на него ответственность за своё решение.",
        "scene.elder.restore_talk": "Председатель сам нашёл старосту на работе после испорченных отношений.",
        "scene.elder.last_advice": "В хозяйстве работают агроном, зоотехник и счетовод; роль старого советчика окончена.",
    }[scene]
    if scene == "scene.elder.warnings" and condition in WARNING_MEANINGS:
        situation = WARNING_MEANINGS[condition]
    elif condition:
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
         "Председатель и староста: рабочее уважительное «вы», совет не приказ."
         if speaker in {"elder", "chairman"} else
         "Житель спрашивает о собственном жилье без знания тайных решений.",
         group, variant, condition, text,
         "Фактическое место работы старосты; одежда и инструмент берутся из партии."
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
        ("elder", "fixed_person", "Бывший староста",
         "{person_address}", "male", "Пожилой; точный возраст не назначен.",
         "Бывший староста, ныне рядовой работник колхоза.",
         "С председателем на «вы»; в тексте — староста, имя в карточке берётся из партии.",
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
             "Пять отдельных фактов приняты boss 29 сентября 2026;"
             " численные пороги и исполняемые сигналы — у core.", 1200 + i),
        )
        con.execute(
            "INSERT INTO cast_slot(scene_key,key,title,binding_kind,gender_binding,"
            "age_binding,social_status,relation_note,address_rule,sort)"
            " VALUES(?,?,?,?,?,?,?,?,?,?)",
            (scene, "chairman", "Председатель", "chairman", "chairman_avatar",
             "Возраст выбранного аватара.", "Председатель колхоза.",
             "Имеет власть, но не перекладывает решение на советчика.",
             "К старосте уважительное «вы», без уменьшительных имен.", 1),
        )
        if scene != "scene.elder.affected_resident_question":
            con.execute(
                "INSERT INTO cast_slot(scene_key,key,title,binding_kind,character_key,"
                "gender_binding,age_binding,social_status,relation_note,address_rule,sort)"
                " VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (scene, "elder", "Бывший староста", "fixed_character",
                 "elder", "fixed_male", "Пожилой; точный возраст не назначен.",
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
    a("opening.chairman", "chairman", "Можно теперь о разметке?", 10)
    a("opening.elder", "elder", "Можно. Поле под застройку уже убрали?", 20)
    a("field.chairman", "chairman", "Поле снято. Теперь надо решить, где что ставить.", 30)
    a("offer.elder", "elder", "Решить — вам. Я могу показать, где поставил бы сам, и почему. Не подойдёт место — передвиньте.", 40)
    coat_branch(con)
    a("answer.see", "chairman", "Покажите весь порядок.", 50, kind="choice", group="answer")
    a("answer.own", "chairman", "Размечу по-своему.", 51, kind="choice", group="answer")
    a("reply.see", "elder", "Покажу по одному месту. Так видно, где мой совет кончается и ваше решение начинается.", 60, condition="Выбран ответ answer.see.")
    a("reply.own", "elder", "На то и председатель. Если передумаете — я на работе, не в конторе.", 61, condition="Выбран ответ answer.own.")
    a("offer.student", "elder", "На бумаге село начинается с середины листа. Здесь оно начинается с дороги. Давайте от неё и пойдём.", 70, condition="Аватар student; председатель начинает с общей схемы.", variant="offer_by_avatar")
    a("offer.villager", "elder", "Дороги вы знаете. Я покажу только, где прежний порядок уже не годится.", 71, condition="Аватар villager.", variant="offer_by_avatar")
    a("whistle.elder", "elder", "Свисток далеко слышно. Кого зовёте — не слышно вовсе. За руками можно свистнуть. За разговором лучше подойти.", 80, condition="Председатель воспользовался свистком и затем сам пришёл к старосте.")
    advice = (
        ("housing", "Шесть бараков я прижал к отводу от старой дороги. Дом в поле просторнее только пока к нему не повезли первую доску."),
        ("well", "Колодец — между дворами. Крайним всё равно ходить дальше, зато крайних не будет с одной стороны."),
        ("store", "За едой ходят по расписанию желудка. Склад поэтому ближе. В правление — когда есть дело; оно ещё шаг потерпит."),
        ("farmyard", "Хозяйственный двор рядом со складом. Не для красоты — чтобы верёвка, лопата и пустой мешок не путешествовали через всё село по отдельности."),
        ("collective_yard", "Конный двор хочется поставить у домов. Утром оттуда лошадь пойдёт не домой, а в поле. Я ставлю между жильём и пашней: человеку чуть дальше, тяглу весь сезон короче."),
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


def coat_branch(con):
    s = "scene.elder.first_meeting"
    questions = (
        ("villager", "Я у церкви ваш сюртук приметил. Это тот самый, графский? С детства его не видел."),
        ("worker", "На вас у церкви сюртук был — не рабочая вещь. Откуда он?"),
        ("student", "Можно спросить? Откуда у вас старинный сюртук, в котором вы меня встретили?"),
        ("ex_chairman", "У церкви я приметил ваш сюртук. Как он к вам попал?"),
        ("promoted", "О сюртуке, в котором вы встречали меня у церкви: откуда эта вещь?"),
        ("old_fighter", "У церкви вы при параде стояли. Откуда сюртук?"),
        ("dealer", "Ваш сюртук у церкви — вещь примечательная. Как он вам достался, позвольте узнать?"),
        ("acting", "В день приезда вы были в сюртуке. Он у вас давно?"),
    )
    for avatar, text in questions:
        add_line(con, s, f"coat.question.{avatar}", "chairman", text, 42,
                 condition=f"Выбран avatar.key={avatar}; тема о сюртуке в первой встрече.",
                 variant="coat_question_by_avatar",
                 meaning="Председатель помнит старосту в графском сюртуке у церкви,"
                         " но сейчас спрашивает о происхождении вещи, а не оценивает человека.",
                 intent="Открыть короткую историю усадьбы голосом выбранного аватара.",
                 keep="Вежливая дистанция и характер аватара; деревенский уже знает об усадьбе."
                      " Не делать сюртук шуткой.")
    add_line(con, s, "coat.reply.work_clothes", "elder",
             "Тот, у церкви? В революцию усадьбу разбирали всем селом. Я вынес сюртук из пустого дома. У иных в селе и теперь графские вещи в сундуках лежат. К вашему приезду надел.",
             43, condition="На старосте в этот момент рабочая одежда, сюртук не надет.",
             variant="coat_reply_by_outfit",
             meaning="Сюртук взят из опустевшей усадьбы четырнадцать лет назад,"
                     " сохранён в сундуке и надет ради встречи нового председателя.",
             intent="Без гордости и стыда сообщить факт села; связать пролог с одеждой в сундуках.",
             keep="«Тот» относится к сюртуку в прологе. Не показывать грабёж и не придумывать"
                  " судьбу графской семьи.")
    add_line(con, s, "coat.reply.coat_worn", "elder",
             "Этот? В революцию усадьбу разбирали всем селом. Я вынес сюртук из пустого дома. У иных в селе и теперь графские вещи в сундуках лежат.",
             43, condition="На старосте в этот момент графский сюртук.",
             variant="coat_reply_by_outfit",
             meaning="Сюртук взят из опустевшей усадьбы четырнадцать лет назад;"
                     " часть прежней одежды хранится у других семей.",
             intent="Без гордости и стыда сообщить факт села, не насмехаясь над нарядом.",
             keep="«Этот» относится к сюртуку, который сейчас на старосте."
                  " Не показывать грабёж и не придумывать судьбу графской семьи.")


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
      condition=WARNING_FACTS["hay_before_snow"])
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
          condition=WARNING_FACTS[key])


def resident_and_name(con):
    s = "scene.elder.affected_resident_question"
    a = lambda key, speaker, text, sort, **kw: add_line(con, s, key, speaker, text, sort, **kw)
    a("opening.resident", "resident", "Теперь мы тут живём. Почему жильё поставили именно здесь?", 10)
    a("answer.own", "chairman", "Это моё решение. Спрашивайте с меня.", 20, kind="choice", group="answer")
    a("answer.road", "chairman", "Здесь дорога рядом. Дальше строить дороже.", 21, kind="choice", group="answer")
    a("answer.cite_elder", "chairman", "Это место показал бывший староста.", 22, kind="choice", group="answer")

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
             condition="fact:three_specialists_working")


def main():
    with sqlite3.connect(ROOT / "db/story.db") as con:
        con.execute("PRAGMA foreign_keys=ON")
        existing = con.execute("SELECT count(*) FROM scene_script WHERE scene_key LIKE 'scene.elder.%'").fetchone()[0]
        if existing:
            count = con.execute("SELECT count(*) FROM line WHERE scene_key LIKE 'scene.elder.%'").fetchone()[0]
            if existing != len(SCENES) or count not in (41, 51):
                raise SystemExit("Elder corpus differs; automatic overwrite is forbidden")
            if count == 41:
                coat_branch(con)
            coat_key = "scene.elder.first_meeting.coat.question.villager"
            coat_old = "Это ж графский сюртук был у вас у церкви? Я его с детства не видел."
            coat_new = "Я у церкви ваш сюртук приметил. Это тот самый, графский? С детства его не видел."
            coat_current = con.execute("SELECT text FROM line WHERE key=?", (coat_key,)).fetchone()
            if coat_current is None or coat_current[0] not in (coat_old, coat_new):
                raise SystemExit("Villager coat question was edited manually; refusing overwrite")
            if coat_current[0] == coat_old:
                con.execute("UPDATE line SET text=? WHERE key=?", (coat_new, coat_key))
            key = "scene.elder.warnings.sowing_window"
            old = "Срок сева подходит, а на поле ещё не вышли. Проверьте наряд и семена, пока опоздание не обошлось урожаем."
            new = "Срок сева подходит, а поле пустое. Проверьте наряд и семена: поздний сев даст меньше урожая."
            current = con.execute("SELECT text FROM line WHERE key=?", (key,)).fetchone()
            if current is None or current[0] not in (old, new):
                raise SystemExit("Sowing warning was edited manually; refusing overwrite")
            if current[0] == old:
                con.execute("UPDATE line SET text=? WHERE key=?", (new, key))
            old_conditions = {
                "sowing_window": "Только отдельный фактический повод warning.sowing_window; общий флаг недостаточен.",
                "next_seed": "Только отдельный фактический повод warning.next_seed; общий флаг недостаточен.",
                "late_harvest": "Только отдельный фактический повод warning.late_harvest; общий флаг недостаточен.",
                "hay_before_snow": "Нескошенная доля луга за месяц до первого устойчивого снега по климату; порог доли — STUB core.",
                "zyab": "Только отдельный фактический повод warning.zyab; общий флаг недостаточен.",
            }
            for suffix, fact in WARNING_FACTS.items():
                line_key = f"scene.elder.warnings.{suffix}"
                row = con.execute("SELECT condition_ref FROM line WHERE key=?", (line_key,)).fetchone()
                if row is None or row[0] not in (old_conditions[suffix], fact):
                    raise SystemExit(f"Condition for {line_key} was edited manually; refusing overwrite")
                if row[0] != fact:
                    con.execute("UPDATE line SET condition_ref=? WHERE key=?", (fact, line_key))
            last_key = "scene.elder.last_advice.handoff"
            last_old = "В хозяйстве одновременно работают агроном, зоотехник и счетовод."
            last_new = "fact:three_specialists_working"
            last_row = con.execute("SELECT condition_ref FROM line WHERE key=?", (last_key,)).fetchone()
            if last_row is None or last_row[0] not in (last_old, last_new):
                raise SystemExit("Last-advice condition was edited manually; refusing overwrite")
            if last_row[0] != last_new:
                con.execute("UPDATE line SET condition_ref=? WHERE key=?", (last_new, last_key))
            con.execute("UPDATE scene_script SET note=? WHERE scene_key='scene.elder.warnings'",
                        ("Пять отдельных фактов приняты boss 29 сентября 2026;"
                         " численные пороги и исполняемые сигналы — у core.",))
            for key, scene, kind, condition in con.execute(
                "SELECT key,scene_key,kind,condition_ref FROM line"
                " WHERE scene_key LIKE 'scene.elder.%' AND key NOT LIKE 'scene.elder.first_meeting.coat.%'"):
                meaning, intent = semantic_context(scene, kind, condition)
                con.execute("UPDATE line SET meaning=?,intent=? WHERE key=?", (meaning, intent, key))
            print("51 elder lines present; coat branch and translation metadata updated")
            return
        setup(con)
        first_meeting(con)
        warnings(con)
        resident_and_name(con)
        broken = con.execute("PRAGMA foreign_key_check").fetchall()
        if broken:
            raise ValueError(f"Broken foreign keys: {broken}")
        total = con.execute("SELECT count(*) FROM line WHERE scene_key LIKE 'scene.elder.%'").fetchone()[0]
    print(f"Six elder scenes, {total} lines; new warning conditions remain draft")


if __name__ == "__main__":
    main()

-- Редакция подсказок: boss-rpg-quest-navigation-review-2026-09-26, ход 3.
-- Только собственная сюжетная база. Триггер повышает rev; утверждение не выдаётся.
PRAGMA foreign_keys = ON;
BEGIN IMMEDIATE;
CREATE TEMP TABLE navigation_guard (matched INTEGER NOT NULL CHECK (matched = 5));
INSERT INTO navigation_guard SELECT count(*) FROM line WHERE
    (key = 'dialogue.school_fears.teacher.accepted'
     AND text = 'Начните с её слов. Всё остальное село уже охотно добавило.') OR
    (key = 'dialogue.school_fears.witch.borrowed_name'
     AND text = 'Моё имя там есть, моих слов нет. Без моего имени взрослые бы не поверили. Спросите старшего, который всем показывает, куда облако полетит.') OR
    (key = 'dialogue.school_fears.witch.early_home'
     AND text = 'Я сказала про старые деревья. А вот кто это слышал: {rumor_adult}. Крыша выросла позже. Спросите, зачем она понадобилась.') OR
    (key = 'scene.night_hunt.distiller_report.opening.meeting'
     AND text = 'Позавчера, уже затемно, у одного двора двое встретились. Один пришёл с пустыми руками, ушёл — уже не с пустыми. Я туда не полез. Моё дело склад удержать.') OR
    (key = 'scene.night_hunt.distiller_report.reply.take'
     AND text = 'Двор покажу засветло. Как стемнеет — дальше без меня.');

UPDATE line SET
    text = 'Это {addressee}. Начните с её слов. Всё остальное село уже охотно добавило.',
    meaning = 'Учитель называет закреплённую носительницу роли колдуньи, не её текущую позицию.'
WHERE key = 'dialogue.school_fears.teacher.accepted';
UPDATE line SET
    text = 'Моё имя там есть, моих слов нет. Вот кто рассказывает про облако: {addressee}. Спросите, откуда взялось предупреждение.',
    meaning = 'Колдунья называет закреплённого школьника, известного ей пересказом; его признание ещё не получено.'
WHERE key = 'dialogue.school_fears.witch.borrowed_name';
UPDATE line SET
    text = 'Я сказала про старые деревья. А вот кто это слышал: {addressee}. Крыша выросла позже. Спросите, зачем она понадобилась.',
    meaning = 'Колдунья называет сохранённого взрослого источника слуха, а не случайного прохожего.'
WHERE key = 'dialogue.school_fears.witch.early_home';
UPDATE line SET
    text = 'Позавчера, уже затемно, {place} двое встретились. Один пришёл с пустыми руками, ушёл — уже не с пустыми. Я туда не полез. Моё дело склад удержать.',
    meaning = 'Работник передаёт известное ему место наблюдения у ворот определённого двора, не имя тайного самогонщика.'
WHERE key = 'scene.night_hunt.distiller_report.opening.meeting';
UPDATE line SET
    text = 'Место я назвал. Засветло дорогу запомните. Как стемнеет — дальше без меня.',
    meaning = 'Место уже названо в свидетельстве; работник советует запомнить дорогу засветло, не обещает несуществующее сопровождение.',
    keep = 'Сохранить вечер после темноты до отбоя, личный приход председателя и границу участия работника. Не добавлять метку или сопровождение.'
WHERE key = 'scene.night_hunt.distiller_report.reply.take';

UPDATE line_placeholder SET name = 'addressee',
    meaning = 'Полное имя сохранённого взрослого источника слуха, именительный падеж.',
    note = 'Бывшее rumor_adult; та же роль. Не склонять и не перевыбирать жителя.'
WHERE line_key = 'dialogue.school_fears.witch.early_home' AND name = 'rumor_adult';
INSERT INTO line_placeholder (line_key, name, kind, meaning, note) VALUES
('dialogue.school_fears.teacher.accepted', 'addressee', 'name',
 'Полное имя сохранённой носительницы роли колдуньи, именительный падеж.',
 'Из school_fears.cast.witch_id. Не текущий собеседник и не координаты.'),
('dialogue.school_fears.witch.borrowed_name', 'addressee', 'name',
 'Полное имя сохранённого старшего школьника, именительный падеж.',
 'Из school_fears.cast.older_id. Пол из карточки; настоящее признание впереди.'),
('scene.night_hunt.distiller_report.opening.meeting', 'place', 'text',
 'Человеческое описание фактического места наблюдавшейся передачи у ворот, с предлогом.',
 'Источник и проверка — ядро/хост. Не раскрывать имя нарушителя или ненаблюдавшийся новый двор.');
INSERT INTO line (key, scene_key, namespace, kind, speaker_slot, addressee_slot,
                  relationship, grammatical_gender, condition_ref, previous_key,
                  text, context, meaning, intent, keep, source_ref, sort)
VALUES ('scene.night_hunt.distiller_leak_return.opening.new_place',
        'scene.night_hunt.distiller_leak_return', 'scene', 'dialogue',
        'storekeeper', 'chairman', 'Работник склада сообщает известное место новой передачи.',
        'neutral', 'После повторной утечки; работнику известно новое наблюдение передачи.',
        'scene.night_hunt.distiller_leak_return.opening.through_yard',
        'Вчера передача была уже {place}. Там и посмотрите вечером.',
        'Дополнение дневного доклада перед новой вечерней засадой, не вывод из одной недостачи.',
        'Названо новое место известной свидетелю передачи; старый двор не считается верным автоматически.',
        'Дать маршрут следующего поиска без раскрытия тайной роли.',
        'Показывать только при действительно известном работнику наблюдении. Повторная утечка сама адреса не раскрывает.',
        'manual/texts/night-hunt-scenes.md#склад-остался-проходным--повторная-утечка', 20);
INSERT INTO line_placeholder (line_key, name, kind, meaning, note) VALUES
('scene.night_hunt.distiller_leak_return.opening.new_place', 'place', 'text',
 'Человеческое описание нового места фактически наблюдавшейся передачи, с предлогом.',
 'Не старый двор и не место из тайной роли. Сценарий ждёт известного свидетелю наблюдения.');
COMMIT;

-- choice_group: 11 строк. Файл создаётся tools/story.py save —
-- правится база, не этот дамп. Порядок строк детерминирован.
DELETE FROM "choice_group";
INSERT INTO "choice_group" ("scene_key", "key", "title", "condition_ref", "note", "sort") VALUES ('scene.count_lodge.offer', 'decision', 'Что делать со слухом о погребе', NULL, 'Три ответа: уточнить, поехать или отложить. Уточнение возвращает к выбору.', 10);
INSERT INTO "choice_group" ("scene_key", "key", "title", "condition_ref", "note", "sort") VALUES ('scene.district.failure_explanation', 'answer', 'Назвать причину провала', NULL, 'Пять условных причин; host показывает 2–4 по фактам проваленного года и считает выбранную метку.', 20);
INSERT INTO "choice_group" ("scene_key", "key", "title", "condition_ref", "note", "sort") VALUES ('scene.elder.affected_resident_question', 'answer', 'Ответ председателя', NULL, NULL, 1);
INSERT INTO "choice_group" ("scene_key", "key", "title", "condition_ref", "note", "sort") VALUES ('scene.elder.first_meeting', 'answer', 'Ответ председателя', NULL, NULL, 1);
INSERT INTO "choice_group" ("scene_key", "key", "title", "condition_ref", "note", "sort") VALUES ('scene.elder.restore_talk', 'answer', 'Ответ председателя', NULL, NULL, 1);
INSERT INTO "choice_group" ("scene_key", "key", "title", "condition_ref", "note", "sort") VALUES ('scene.family.before_distribution', 'answer', 'Ответ до выдачи', NULL, 'Четыре авторских решения; общее правило и премия доступны лишь при своих фактах. Уговора и случайной неудачи нет.', 10);
INSERT INTO "choice_group" ("scene_key", "key", "title", "condition_ref", "note", "sort") VALUES ('scene.night_hunt.distiller_report', 'answer', 'Ответ работнику склада', NULL, 'Два варианта: проверить двор вечером либо пока отказаться от засады.', 10);
INSERT INTO "choice_group" ("scene_key", "key", "title", "condition_ref", "note", "sort") VALUES ('scene.school_fears.brave_society', 'main', 'Решение председателя', NULL, 'Варианты и исходы описаны в авторском источнике.', 10);
INSERT INTO "choice_group" ("scene_key", "key", "title", "condition_ref", "note", "sort") VALUES ('scene.school_fears.source_answer', 'main', 'Решение председателя', NULL, 'Варианты и исходы описаны в авторском источнике.', 10);
INSERT INTO "choice_group" ("scene_key", "key", "title", "condition_ref", "note", "sort") VALUES ('scene.school_fears.teacher_opening', 'main', 'Решение председателя', NULL, 'Варианты и исходы описаны в авторском источнике.', 10);
INSERT INTO "choice_group" ("scene_key", "key", "title", "condition_ref", "note", "sort") VALUES ('scene.school_fears.witch_account', 'main', 'Решение председателя', NULL, 'Варианты и исходы описаны в авторском источнике.', 10);

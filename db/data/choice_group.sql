-- choice_group: 2 строк. Файл создаётся tools/story.py save —
-- правится база, не этот дамп. Порядок строк детерминирован.
DELETE FROM "choice_group";
INSERT INTO "choice_group" ("scene_key", "key", "title", "condition_ref", "note", "sort") VALUES ('scene.district.failure_explanation', 'answer', 'Назвать причину провала', NULL, 'Пять условных причин; host показывает 2–4 по фактам проваленного года и считает выбранную метку.', 20);
INSERT INTO "choice_group" ("scene_key", "key", "title", "condition_ref", "note", "sort") VALUES ('scene.family.before_distribution', 'answer', 'Ответ до выдачи', NULL, 'Четыре авторских решения; общее правило и премия доступны лишь при своих фактах. Уговора и случайной неудачи нет.', 10);

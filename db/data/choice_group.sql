-- choice_group: 1 строк. Файл создаётся tools/story.py save —
-- правится база, не этот дамп. Порядок строк детерминирован.
DELETE FROM "choice_group";
INSERT INTO "choice_group" ("scene_key", "key", "title", "condition_ref", "note", "sort") VALUES ('scene.family.before_distribution', 'answer', 'Ответ до выдачи', NULL, 'Четыре авторских решения; общее правило и премия доступны лишь при своих фактах. Уговора и случайной неудачи нет.', 10);

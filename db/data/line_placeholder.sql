-- line_placeholder: 1 строк. Файл создаётся tools/story.py save —
-- правится база, не этот дамп. Порядок строк детерминирован.
DELETE FROM "line_placeholder";
INSERT INTO "line_placeholder" ("line_key", "name", "kind", "meaning", "note") VALUES ('scene.family.before_distribution.answer.premium', 'real_deed', 'text', 'Фактически совершённый семьёй поступок, за который положена ещё не выданная премия.', 'Подставлять словосочетание в форме после предлога «за»: например «помощь на уборке», а не голое название события.');

-- Own story.db only. Guarded one-shot migration, five openings rev1 -> rev2.
-- The existing line_source_changed trigger increments each rev once.
PRAGMA foreign_keys = ON;
BEGIN IMMEDIATE;
CREATE TEMP TABLE rpg_failed_positions_guard (ok INTEGER CHECK (ok = 1));
CREATE TEMP TABLE rpg_failed_positions_values (
    key TEXT PRIMARY KEY,
    old_text TEXT NOT NULL,
    new_text TEXT NOT NULL
);
INSERT INTO rpg_failed_positions_values VALUES
('scene.district.failure_explanation.opening.korenev',
 'План за {failed_year} год не выполнен. Что вы скажете району?',
 'План за {failed_year} год не выполнен: {failed_positions}. Что вы скажете району?'),
('scene.district.failure_explanation.opening.stozharov',
 'План за {failed_year} год не сошёлся. Что произошло на месте?',
 'План за {failed_year} год не сошёлся: {failed_positions}. Что произошло на месте?'),
('scene.district.failure_explanation.opening.karasev',
 'В сводке за {failed_year} год недостача. Мне ведь придётся что-то написать. Что именно?',
 'В сводке за {failed_year} год план не выполнен: {failed_positions}. Мне ведь придётся что-то написать. Что именно?'),
('scene.district.failure_explanation.opening.zhernova',
 'План за {failed_year} год не выполнен. Я вижу цифры. Теперь назовите причину.',
 'План за {failed_year} год не выполнен: {failed_positions}. Я вижу цифры. Теперь назовите причину.'),
('scene.district.failure_explanation.opening.polushkina',
 'В отчёте за {failed_year} год план не выполнен. В бланке есть строка для причины. Что туда вписать?',
 'В отчёте за {failed_year} год план не выполнен: {failed_positions}. В бланке есть строка для причины. Что туда вписать?');
INSERT INTO rpg_failed_positions_guard
SELECT CASE WHEN COUNT(*) = 5 THEN 1 ELSE 0 END
FROM line l JOIN rpg_failed_positions_values v ON v.key = l.key
WHERE l.text = v.old_text AND l.rev = 1 AND l.approved_rev IS NULL
  AND l.deprecated = 0;
INSERT INTO rpg_failed_positions_guard
SELECT CASE WHEN COUNT(*) = 0 THEN 1 ELSE 0 END
FROM line_placeholder WHERE name = 'failed_positions'
 AND line_key IN (SELECT key FROM rpg_failed_positions_values);
UPDATE line
SET text = (SELECT v.new_text FROM rpg_failed_positions_values v WHERE v.key = line.key),
    keep = keep || ' {failed_positions}: ready localized list of positions below plan_met_share from the CLOSED failed-year ledger, with fulfilled percentages, not deficit percentages. Same saved year as {failed_year}; never current stock or aggregate completion. No final punctuation in the supplied list.'
WHERE key IN (SELECT key FROM rpg_failed_positions_values);
INSERT INTO line_placeholder (line_key, name, kind, meaning, note)
SELECT key, 'failed_positions', 'text',
       'Ready localized list of failed plan positions and their fulfilled percentages in the closed failed year.',
       'Host supplies only positions below plan_met_share from the same closed-year ledger as failed_year; joins fragments with feed.list_separator; no terminal punctuation. Not the current year, stock shortage, overall completion or deficit share. Works unchanged with one or multiple positions.'
FROM rpg_failed_positions_values;
INSERT INTO rpg_failed_positions_guard
SELECT CASE WHEN COUNT(*) = 5 THEN 1 ELSE 0 END
FROM string_source s JOIN rpg_failed_positions_values v ON v.key = s.full_key
WHERE s.text = v.new_text AND s.rev = 2 AND s.approved_rev IS NULL;
INSERT INTO rpg_failed_positions_guard
SELECT CASE WHEN COUNT(*) = 5 THEN 1 ELSE 0 END
FROM line_placeholder WHERE name = 'failed_positions' AND kind = 'text'
 AND line_key IN (SELECT key FROM rpg_failed_positions_values);
DROP TABLE rpg_failed_positions_values;
DROP TABLE rpg_failed_positions_guard;
COMMIT;
